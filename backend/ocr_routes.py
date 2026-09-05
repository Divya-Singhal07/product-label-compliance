import uuid
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from fastapi.responses import JSONResponse

# Shared auth dependency – supports running both as package and standalone
try:
    from .deps import get_current_user, supabase_client
except ImportError:
    from deps import get_current_user, supabase_client

# Import OCR pipeline components (no changes to label_lens code)
from label_lens.preprocessing.pipeline import PackageImagePreprocessor
from label_lens.ocr.ocr_pipeline import OCRProcessor
from label_lens.ocr.llm_extractor import extract_fields_with_llm
from label_lens.ocr.product_id import generate_product_id

# Rule Engine – mapper converts OCR fields → canonical format, engine runs compliance
from label_lens.rule_engine_mapper import map_to_rule_engine
from label_lens.rule_engine.engine import run_compliance_check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ocr")

# Simple in‑memory job store – tracks active processing jobs
_JOBS: Dict[str, Dict[str, Any]] = {}


@router.get("/runtime")
async def get_runtime_status(user=Depends(get_current_user)):
    """Expose safe diagnostics for the active OCR service instance.

    This deliberately returns only feature flags. It never returns environment
    values, tokens, OCR text, uploaded-file paths, or user data.
    """
    try:
        from .deps import _load_runtime_config
    except ImportError:
        from deps import _load_runtime_config

    _load_runtime_config()
    try:
        import groq  # noqa: F401
        groq_available = True
    except ImportError:
        groq_available = False

    return {
        "backend_revision": "llm-required-v1",
        "groq_client_available": groq_available,
        "llm_configuration_present": bool(os.environ.get("GROQ_API_KEY")),
    }

_TEXT_EXTRACTION_FIELDS = (
    "brand", "product_name", "generic_name", "net_quantity", "mrp",
    "manufacturer_address", "packer", "importer", "consumer_care",
    "mfg_date", "best_before", "use_by", "country_of_origin",
)


def _has_usable_llm_fields(view_data: Dict[str, Any]) -> bool:
    """Return whether a view contains usable LLM-derived label fields.

    Rules-based (regex) extraction must never count as success. A single
    non-mandatory field like brand/product_name filled by the regex extractor
    previously caused the guard to skip retry and ship a fake 17/100 score.
    """
    # Reject deterministic fallback — only real LLM (or llm_retry) counts.
    method = view_data.get("extraction_method")
    if method == "rules":
        return False

    ocr_lines = view_data.get("ocr_lines")
    fields = view_data.get("fields")
    if not isinstance(ocr_lines, list) or not isinstance(fields, dict):
        return False
    if not any(isinstance(line, dict) and str(line.get("text", "")).strip() for line in ocr_lines):
        return False

    return any(fields.get(field) not in (None, "") for field in _TEXT_EXTRACTION_FIELDS)


def _require_usable_ocr(final: Dict[str, Any]) -> None:
    """Reject a job when OCR produced no text for every supplied image.

    Previously, view errors and empty OCR responses were merged into the
    default field schema and sent to the rule engine. The resulting score was
    a misleading 17/100 rather than an OCR failure.
    """
    views = final.get("views")
    if not isinstance(views, dict):
        raise RuntimeError("OCR returned no view results. No compliance score was generated.")

    for view_data in views.values():
        if not isinstance(view_data, dict):
            continue
        ocr_lines = view_data.get("ocr_lines")
        if isinstance(ocr_lines, list) and any(
            isinstance(line, dict) and str(line.get("text", "")).strip()
            for line in ocr_lines
        ):
            return

    raise RuntimeError(
        "OCR could not read text from the uploaded images. No compliance score was generated."
    )


def _require_llm_extraction(ocr: OCRProcessor, final: Dict[str, Any]) -> List[str]:
    """Ensure OCR text is assessed by the configured LLM, never fallback rules.

    The OCR package can silently replace an LLM failure with deterministic
    extraction. That leads to a plausible-but-wrong compliance score when the
    rules extractor finds only a few declarations. The API retries the LLM
    once, then fails the job instead of treating incomplete fallback fields as
    a compliance result.
    """
    views = final.get("views")
    if not isinstance(views, dict):
        return []

    recovered_views: List[str] = []
    for view_name, view_data in views.items():
        if not isinstance(view_data, dict):
            continue

        ocr_lines = view_data.get("ocr_lines")
        has_text = isinstance(ocr_lines, list) and any(
            isinstance(line, dict) and str(line.get("text", "")).strip()
            for line in ocr_lines
        )
        if not has_text or _has_usable_llm_fields(view_data):
            continue

        try:
            fields = extract_fields_with_llm(ocr_lines)
        except Exception as exc:
            logger.warning("LLM extraction retry failed for view %s: %s", view_name, exc)
            raise RuntimeError(
                "LLM extraction is unavailable. No compliance score was generated."
            ) from exc

        retry_view = {"ocr_lines": ocr_lines, "fields": fields}
        if not _has_usable_llm_fields(retry_view):
            raise RuntimeError(
                "LLM extraction returned no usable label fields. No compliance score was generated."
            )

        view_data["fields"] = ocr._normalize_fields(fields)
        view_data["extraction_method"] = "llm_retry"
        recovered_views.append(view_name)

    if recovered_views:
        # Reuse the pipeline's existing multi-view priority rules rather than
        # redefining OCR merge behavior in the API layer.
        final["merged_fields"] = ocr._merge_fields(views)
        merged = final["merged_fields"]
        final["product_id"] = generate_product_id(
            brand=merged.get("brand"),
            product_name=merged.get("product_name"),
            net_quantity=merged.get("net_quantity"),
        )

    return recovered_views

def _run_ocr_job(
    job_id: str,
    image_paths: List[Union[str, Path]],
    view_names: Optional[List[str]],
    product_id: Optional[str],
    officer_info: Optional[Dict[str, Any]] = None,
) -> None:
    """Background task that runs the OCR pipeline and stores the result.
    Mirrors the logic from label_lens/main_ocr.py but returns a dict instead of writing files.
    After OCR, the merged fields are fed through the Rule Engine for compliance checking.
    The final immutable audit record is saved to Supabase inspection_records.
    """
    try:
        _JOBS[job_id]["status"] = "processing"
        logger.info("OCR job %s: preprocessing %s image(s)", job_id, len(image_paths))

        # 1️⃣ Preprocess images
        pre = PackageImagePreprocessor(debug=False, max_workers=3)
        batch = pre.process_batch(image_paths, view_names=view_names, product_id=product_id)

        # 2️⃣ OCR + field extraction
        logger.info("OCR job %s: running OCR + field extraction", job_id)
        ocr = OCRProcessor()
        front_name = view_names[0] if view_names else "front"
        final = ocr.process_product(batch, front_view_name=front_name)
        _require_usable_ocr(final)
        retried_views = _require_llm_extraction(ocr, final)

        merged_fields = final["merged_fields"]
        logger.info("OCR job %s extracted merged fields: %s", job_id, merged_fields)

        for vname, vdata in final.get("views", {}).items():
            if "error" in vdata:
                logger.warning("OCR view %s reported error: %s", vname, vdata["error"])
            elif isinstance(vdata.get("fields"), dict) and "error" in vdata["fields"]:
                logger.warning("OCR view %s field extraction error: %s", vname, vdata["fields"]["error"])

        # 3️⃣ Rule Engine – map OCR fields to canonical format, then check compliance.
        # Do not swallow engine failures: a null compliance_result produces the
        # identical "AWAITING ANALYSIS" UI for every image.
        try:
            rule_input = map_to_rule_engine(merged_fields)
            compliance_result = run_compliance_check(rule_input)
            if isinstance(compliance_result, dict):
                comp_score = compliance_result.get("score")
            else:
                comp_score = getattr(compliance_result, "score", None)
            logger.info("OCR job %s compliance check complete. Score: %s", job_id, comp_score)
        except Exception as re_exc:
            logger.exception("Rule Engine failed for job %s", job_id)
            raise RuntimeError(
                f"Rule engine failed; no compliance score was generated: {re_exc}"
            ) from re_exc

        # Format compliance result dictionary
        comp_dict = None
        if compliance_result is not None:
            if hasattr(compliance_result, "model_dump"):
                comp_dict = compliance_result.model_dump()
            elif hasattr(compliance_result, "dict"):
                comp_dict = compliance_result.dict()
            elif isinstance(compliance_result, dict):
                comp_dict = compliance_result

        if comp_dict is not None and retried_views:
            warnings = comp_dict.setdefault("warnings", [])
            if isinstance(warnings, list):
                warnings.append(
                    "LLM extraction was retried successfully for: "
                    + ", ".join(retried_views)
                    + "."
                )

        # Store in-memory result for current polling session
        _JOBS[job_id]["status"] = "completed"
        _JOBS[job_id]["result"] = {
            "product_id": final["product_id"],
            "product_folder": final["product_folder"],
            "merged_fields": merged_fields,
            "compliance_result": comp_dict,
            "views": final.get("views", {}),
            "metadata": {"llm_retry_views": retried_views},
        }

        # 4️⃣ Persist to Supabase immutable inspection_records audit table
        if officer_info:
            try:
                is_comp = comp_dict.get("is_compliant", False) if comp_dict else False
                score = float(comp_dict.get("score", 0.0)) if comp_dict else 0.0
                summary = comp_dict.get("summary", "") if comp_dict else ""
                needs_review = bool(comp_dict.get("needs_manual_review", False)) if comp_dict else False
                violations = comp_dict.get("violations", []) if comp_dict else []
                missing = comp_dict.get("missing_fields", []) if comp_dict else []
                warnings = comp_dict.get("warnings", []) if comp_dict else []

                record = {
                    "officer_user_id": officer_info.get("officer_user_id"),
                    "officer_id": officer_info.get("officer_id") or "UNKNOWN",
                    "officer_name": officer_info.get("officer_name") or "",
                    "officer_email": officer_info.get("officer_email") or "",
                    "department": officer_info.get("department") or "",
                    "role": officer_info.get("role") or "",
                    "product_id": final.get("product_id") or product_id,
                    "view_names": view_names or [],
                    "is_compliant": is_comp,
                    "confidence_score": score,
                    "summary": summary,
                    "needs_manual_review": needs_review,
                    "extracted_fields": merged_fields or {},
                    "violations": violations,
                    "missing_fields": missing,
                    "warnings": warnings,
                }
                supabase_client().table("inspection_records").insert(record).execute()
                logger.info("Saved immutable inspection record for product %s to Supabase", final["product_id"])
            except Exception as db_exc:
                logger.warning("Failed to persist inspection record to Supabase: %s", db_exc)

    except Exception as exc:
        logger.exception("OCR job %s failed", job_id)
        job = _JOBS.get(job_id)
        if job is not None:
            job["status"] = "failed"
            job["error"] = str(exc)

@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    files: List[UploadFile] = File(...),
    view_names: Optional[str] = Form(None),
    product_id: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    user = Depends(get_current_user),
):
    """Create a new OCR job.
    - `files` : one or more images (front, back, side …)
    - `view_names` : JSON-encoded list matching the order of `files`
    - `product_id` : optional override for the auto‑generated product ID
    - `metadata` : optional free‑form JSON saved with the job
    Returns a UUID job identifier.
    """
    parsed_views: Optional[List[str]] = None
    if view_names:
        try:
            parsed = json.loads(view_names)
        except (json.JSONDecodeError, TypeError) as exc:
            raise HTTPException(status_code=400, detail="view_names must be a JSON array") from exc
        if (
            not isinstance(parsed, list)
            or len(parsed) != len(files)
            or not all(isinstance(view, str) and view in {"front", "back", "side"} for view in parsed)
            or len(set(parsed)) != len(parsed)
        ):
            raise HTTPException(
                status_code=400,
                detail="view_names must contain unique front, back, or side entries matching the uploaded files",
            )
        parsed_views = parsed

    parsed_metadata: Dict[str, Any] = {}
    if metadata:
        try:
            parsed_metadata = json.loads(metadata)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="metadata must be valid JSON") from exc
        if not isinstance(parsed_metadata, dict):
            raise HTTPException(status_code=400, detail="metadata must be a JSON object")

    job_id = str(uuid.uuid4())
    upload_dir = Path(__file__).resolve().parent / "ocr_uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: List[Union[str, Path]] = []
    for idx, upload in enumerate(files):
        filename = upload.filename or "image.png"
        suffix = Path(filename).suffix or ".png"
        dest = upload_dir / f"img_{idx}{suffix}"
        content = await upload.read()
        dest.write_bytes(content)
        saved_paths.append(dest)

    now = datetime.now(timezone.utc).isoformat()

    # Extract officer metadata from user
    user_metadata = getattr(user, "user_metadata", {}) or getattr(user, "raw_user_meta_data", {}) or {}
    officer_info = {
        "officer_user_id": getattr(user, "id", None),
        "officer_email": getattr(user, "email", None),
        "officer_id": user_metadata.get("officer_id") or getattr(user, "email", "UNKNOWN"),
        "officer_name": user_metadata.get("full_name") or "",
        "department": user_metadata.get("department") or "",
        "role": user_metadata.get("role") or "",
    }

    # Initialise the job entry
    _JOBS[job_id] = {
        "status": "queued",
        "owner": getattr(user, "id", None),
        "created_at": now,
        "metadata": parsed_metadata,
    }

    # Run OCR in a daemon thread so long Paddle/Groq work cannot stall the
    # request worker the way FastAPI BackgroundTasks sometimes does.
    worker = threading.Thread(
        target=_run_ocr_job,
        kwargs={
            "job_id": job_id,
            "image_paths": saved_paths,
            "view_names": parsed_views,
            "product_id": product_id,
            "officer_info": officer_info,
        },
        daemon=True,
        name=f"ocr-{job_id[:8]}",
    )
    worker.start()
    logger.info("OCR job %s queued (%s file(s))", job_id, len(saved_paths))

    return JSONResponse(
        {
            "job_id": job_id,
            "status": "queued",
            "submitted_at": now,
        },
        status_code=status.HTTP_202_ACCEPTED,
    )

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, user = Depends(get_current_user)):
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("owner") != getattr(user, "id", None):
        raise HTTPException(status_code=403, detail="Not authorized")
    response = {"job_id": job_id, "status": job["status"]}
    if job["status"] == "failed":
        response["error"] = job.get("error", "Analysis failed")
    return response

@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str, user = Depends(get_current_user)):
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("owner") != getattr(user, "id", None):
        raise HTTPException(status_code=403, detail="Not authorized")
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not completed yet")
    return job["result"]

@router.get("/records")
async def get_past_records(user = Depends(get_current_user)):
    """Fetch past immutable inspection records for the authenticated officer."""
    try:
        user_metadata = getattr(user, "user_metadata", {}) or getattr(user, "raw_user_meta_data", {}) or {}
        officer_id = user_metadata.get("officer_id") or getattr(user, "email", None)
        user_id = getattr(user, "id", None)
        query = supabase_client().table("inspection_records").select("*").order("created_at", desc=True)
        if user_id:
            query = query.or_(f"officer_user_id.eq.{user_id},officer_id.eq.{officer_id}")
        response = query.limit(50).execute()
        return response.data or []
    except Exception as exc:
        logger.warning("Failed to fetch past records: %s", exc)
        return []
