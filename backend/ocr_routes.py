import uuid
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from fastapi import APIRouter, Depends, File, UploadFile, Form, BackgroundTasks, HTTPException, status
from fastapi.responses import JSONResponse

# Shared auth dependency – supports running both as package and standalone
try:
    from .deps import get_current_user, supabase_client
except ImportError:
    from deps import get_current_user, supabase_client

# Import OCR pipeline components (no changes to label_lens code)
from label_lens.preprocessing.pipeline import PackageImagePreprocessor
from label_lens.ocr.ocr_pipeline import OCRProcessor

# Rule Engine – mapper converts OCR fields → canonical format, engine runs compliance
from label_lens.rule_engine_mapper import map_to_rule_engine
from label_lens.rule_engine.engine import run_compliance_check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ocr")

# Simple in‑memory job store – tracks active processing jobs
_JOBS: Dict[str, Dict[str, Any]] = {}

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

        # 1️⃣ Preprocess images
        pre = PackageImagePreprocessor(debug=False, max_workers=3)
        batch = pre.process_batch(image_paths, view_names=view_names, product_id=product_id)

        # 2️⃣ OCR + field extraction
        ocr = OCRProcessor()
        front_name = view_names[0] if view_names else "front"
        final = ocr.process_product(batch, front_view_name=front_name)

        merged_fields = final["merged_fields"]
        logger.info("OCR job %s extracted merged fields: %s", job_id, merged_fields)

        for vname, vdata in final.get("views", {}).items():
            if "error" in vdata:
                logger.warning("OCR view %s reported error: %s", vname, vdata["error"])
            elif isinstance(vdata.get("fields"), dict) and "error" in vdata["fields"]:
                logger.warning("OCR view %s field extraction error: %s", vname, vdata["fields"]["error"])

        # 3️⃣ Rule Engine – map OCR fields to canonical format, then check compliance
        try:
            rule_input = map_to_rule_engine(merged_fields)
            compliance_result = run_compliance_check(rule_input)
            comp_score = getattr(compliance_result, "score", None) if compliance_result else None
            logger.info("OCR job %s compliance check complete. Score: %s", job_id, comp_score)
        except Exception as re_exc:
            logger.warning("Rule Engine failed, returning OCR-only result: %s", re_exc)
            compliance_result = None

        # Format compliance result dictionary
        comp_dict = None
        if compliance_result is not None:
            if hasattr(compliance_result, "model_dump"):
                comp_dict = compliance_result.model_dump()
            elif hasattr(compliance_result, "dict"):
                comp_dict = compliance_result.dict()
            elif isinstance(compliance_result, dict):
                comp_dict = compliance_result

        # Store in-memory result for current polling session
        _JOBS[job_id]["status"] = "completed"
        _JOBS[job_id]["result"] = {
            "product_id": final["product_id"],
            "product_folder": final["product_folder"],
            "merged_fields": merged_fields,
            "compliance_result": comp_dict,
            "views": final.get("views", {}),
            "metadata": {},
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
        _JOBS[job_id]["status"] = "failed"
        _JOBS[job_id]["error"] = str(exc)

@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    background: BackgroundTasks,
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

    # Parse view_names – frontend sends a JSON-encoded array as a single form field
    parsed_views: Optional[List[str]] = None
    if view_names:
        try:
            parsed_views = json.loads(view_names)
        except (json.JSONDecodeError, TypeError):
            parsed_views = [view_names]

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
        "metadata": json.loads(metadata) if metadata else {},
    }

    # Queue background processing
    background.add_task(
        _run_ocr_job,
        job_id=job_id,
        image_paths=saved_paths,
        view_names=parsed_views,
        product_id=product_id,
        officer_info=officer_info,
    )

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
    return {"job_id": job_id, "status": job["status"]}

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

