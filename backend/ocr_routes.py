import uuid
import json
import logging
import os
import threading
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, cast

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from starlette.requests import Request

try:
    from .deps import (
        ACCESS_COOKIE,
        REFRESH_COOKIE,
        get_current_user,
        supabase_client,
        supabase_client_with_session,
    )
except ImportError:
    from deps import (
        ACCESS_COOKIE,
        REFRESH_COOKIE,
        get_current_user,
        supabase_client,
        supabase_client_with_session,
    )

from label_lens.preprocessing.pipeline import PackageImagePreprocessor
from label_lens.ocr.ocr_pipeline import OCRProcessor
from label_lens.ocr.llm_extractor import extract_fields_with_llm
from label_lens.ocr.ai_fix_suggestions import generate_ai_fix_suggestions
from label_lens.ocr.product_id import generate_product_id

from label_lens.rule_engine_mapper import map_to_rule_engine
from label_lens.rule_engine.engine import run_compliance_check

from label_lens.report_generator import generate_report


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ocr")

_JOBS: Dict[str, Dict[str, Any]] = {}


@router.get("/runtime")
async def get_runtime_status(user=Depends(get_current_user)):
    try:
        from .deps import _load_runtime_config
    except ImportError:
        from deps import _load_runtime_config

    _load_runtime_config()

    try:
        import groq

        groq_available = True
    except ImportError:
        groq_available = False

    return {
        "backend_revision": "llm-required-v1",
        "groq_client_available": groq_available,
        "llm_configuration_present": bool(os.environ.get("GROQ_API_KEY")),
    }


_TEXT_EXTRACTION_FIELDS = (
    "brand",
    "product_name",
    "generic_name",
    "net_quantity",
    "mrp",
    "manufacturer_address",
    "packer",
    "importer",
    "consumer_care",
    "mfg_date",
    "best_before",
    "use_by",
    "country_of_origin",
)


def _has_usable_llm_fields(view_data: Dict[str, Any]) -> bool:
    method = view_data.get("extraction_method")

    if method == "rules":
        return False

    ocr_lines = view_data.get("ocr_lines")
    fields = view_data.get("fields")

    if not isinstance(ocr_lines, list) or not isinstance(fields, dict):
        return False

    if not any(
        isinstance(line, dict)
        and str(line.get("text", "")).strip()
        for line in ocr_lines
    ):
        return False

    return any(
        fields.get(field) not in (None, "")
        for field in _TEXT_EXTRACTION_FIELDS
    )


def _require_usable_ocr(final: Dict[str, Any]) -> None:
    views = final.get("views")

    if not isinstance(views, dict):
        raise RuntimeError(
            "OCR returned no view results. "
            "No compliance score was generated."
        )

    for view_data in views.values():
        if not isinstance(view_data, dict):
            continue

        ocr_lines = view_data.get("ocr_lines")

        if isinstance(ocr_lines, list) and any(
            isinstance(line, dict)
            and str(line.get("text", "")).strip()
            for line in ocr_lines
        ):
            return

    raise RuntimeError(
        "OCR could not read text from the uploaded images. "
        "No compliance score was generated."
    )


def _require_llm_extraction(
    ocr: OCRProcessor,
    final: Dict[str, Any],
) -> List[str]:

    views = final.get("views")

    if not isinstance(views, dict):
        return []

    recovered_views: List[str] = []
    any_usable = False

    for view_name, view_data in views.items():

        if not isinstance(view_data, dict):
            continue

        if _has_usable_llm_fields(view_data):
            any_usable = True
            continue

        raw_lines = view_data.get("ocr_lines")

        has_text = (
            isinstance(raw_lines, list)
            and any(
                isinstance(line, dict)
                and str(line.get("text", "")).strip()
                for line in raw_lines
            )
        )

        if not has_text:
            continue

        ocr_lines = cast(List[Dict[str, Any]], raw_lines)

        try:
            fields = extract_fields_with_llm(ocr_lines)

        except Exception as exc:
            logger.warning(
                "LLM extraction retry failed for view %s: %s",
                view_name,
                exc,
            )
            continue

        retry_view = {
            "ocr_lines": ocr_lines,
            "fields": fields,
        }

        if _has_usable_llm_fields(retry_view):

            view_data["fields"] = ocr._normalize_fields(fields)
            view_data["extraction_method"] = "llm_retry"

            recovered_views.append(view_name)
            any_usable = True

    if not any_usable:

        for view_data in views.values():

            if (
                isinstance(view_data, dict)
                and _has_usable_llm_fields(view_data)
            ):
                any_usable = True
                break

    if not any_usable:
        raise RuntimeError(
            "LLM extraction returned no usable label fields on any view. "
            "No compliance score was generated."
        )

    if recovered_views:

        merged_result = ocr._merge_fields(views)

        final["merged_fields"] = merged_result["fields"]
        final["field_confidence"] = merged_result["field_confidence"]

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

    try:

        _JOBS[job_id]["status"] = "processing"

        logger.info(
            "OCR job %s: preprocessing %s image(s)",
            job_id,
            len(image_paths),
        )

        pre = PackageImagePreprocessor(
            debug=False,
            save_intermediate=False,
            max_workers=1,
            enable_deskew=False,
            enable_perspective=False,
            enable_glare_reduction=False,
            max_side=1600,
        )

        batch = pre.process_batch(
            image_paths,
            view_names=view_names,
            product_id=product_id,
        )

        logger.info(
            "OCR job %s: running OCR + field extraction",
            job_id,
        )

        ocr = OCRProcessor(
            preferred_candidates=[
                "enhanced",
            ]
        )

        front_name = (
            view_names[0]
            if view_names
            else "front"
        )

        final = ocr.process_product(
            batch,
            front_view_name=front_name,
        )

        _require_usable_ocr(final)

        retried_views = _require_llm_extraction(
            ocr,
            final,
        )

        merged_fields = dict(final["merged_fields"])

        # Pass OCR-derived confidence into the rule engine.
        ocr_confidence = dict(
            final.get("field_confidence", {}) or {}
        )

        # The OCR pipeline calls this field manufacturer_address,
        # while the rule engine uses manufacturer.
        if (
            "manufacturer" not in ocr_confidence
            and "manufacturer_address" in ocr_confidence
        ):
            ocr_confidence["manufacturer"] = ocr_confidence[
                "manufacturer_address"
            ]

        merged_fields["ocr_confidence"] = ocr_confidence

        # Preserve complete OCR evidence for the rule engine.
        merged_fields["raw_text"] = final.get("raw_text", "")

        logger.info(
            "OCR job %s extracted merged fields: %s",
            job_id,
            merged_fields,
        )

        # ---------------------------------------------------------
        # RULE ENGINE
        # ---------------------------------------------------------

        try:

            rule_input = map_to_rule_engine(
                merged_fields
            )

            compliance_result: Dict[str, Any] = (
                run_compliance_check(rule_input)
            )

            logger.info(
                "OCR job %s compliance check complete. Score: %s",
                job_id,
                compliance_result.get("score"),
            )

        except Exception as re_exc:

            logger.exception(
                "Rule Engine failed for job %s",
                job_id,
            )

            raise RuntimeError(
                "Rule engine failed; no compliance score was generated: "
                f"{re_exc}"
            ) from re_exc

        # ---------------------------------------------------------
        # COMPLIANCE RESULT
        # ---------------------------------------------------------

        comp_dict = (
            compliance_result
            if isinstance(compliance_result, dict)
            else None
        )

        # ---------------------------------------------------------
        # AI FIX SUGGESTIONS
        # ---------------------------------------------------------

        ai_fix_suggestions = []

        if comp_dict is not None:

            violations = comp_dict.get(
                "violations",
                [],
            )

            logger.info(
                "AI Fix: found %d violation(s) for job %s",
                len(violations),
                job_id,
            )

            try:

                ai_fix_suggestions = (
                    generate_ai_fix_suggestions(
                        violations=violations,
                        product_fields=merged_fields,
                    )
                )

                logger.info(
                    "OCR job %s generated %d AI fix suggestions",
                    job_id,
                    len(ai_fix_suggestions),
                )

            except Exception as ai_exc:

                logger.warning(
                    "AI fix suggestion generation failed "
                    "for job %s: %s",
                    job_id,
                    ai_exc,
                )

        # ---------------------------------------------------------
        # LLM RETRY WARNING
        # ---------------------------------------------------------

        if comp_dict is not None and retried_views:

            warnings = comp_dict.setdefault(
                "warnings",
                [],
            )

            if isinstance(warnings, list):

                warnings.append(
                    "LLM extraction was retried successfully for: "
                    + ", ".join(retried_views)
                    + "."
                )

        # ---------------------------------------------------------
        # STORE JOB RESULT
        # ---------------------------------------------------------

        _JOBS[job_id]["status"] = "completed"

        visual_boxes = {
            view_name: view_data.get("field_boxes", {})
            for view_name, view_data in final.get("views", {}).items()
            if isinstance(view_data, dict)
        }

        _JOBS[job_id]["result"] = {
            "product_id": final["product_id"],
            "product_folder": final["product_folder"],
            "merged_fields": merged_fields,
            "original_merged_fields": dict(merged_fields),
            "visual_boxes": visual_boxes,
            "field_confidence": final.get(
                "field_confidence",
                {},
            ),
            "code_scans": final.get(
                "code_scans",
                {},
            ),
            "ai_fix_suggestions": ai_fix_suggestions,
            "compliance_result": comp_dict,
            "views": final.get(
                "views",
                {},
            ),
            "metadata": {
                "llm_retry_views": retried_views,
            },
        }

        # ---------------------------------------------------------
        # SAVE INSPECTION RECORD
        # ---------------------------------------------------------

        if officer_info:

            try:

                is_comp = (
                    comp_dict.get(
                        "is_compliant",
                        False,
                    )
                    if comp_dict
                    else False
                )

                score = (
                    float(
                        comp_dict.get(
                            "score",
                            0.0,
                        )
                    )
                    if comp_dict
                    else 0.0
                )

                record = {
                    "officer_user_id": officer_info.get(
                        "officer_user_id"
                    ),
                    "officer_id": (
                        officer_info.get("officer_id")
                        or "UNKNOWN"
                    ),
                    "officer_name": (
                        officer_info.get("officer_name")
                        or ""
                    ),
                    "officer_email": (
                        officer_info.get("officer_email")
                        or ""
                    ),
                    "department": (
                        officer_info.get("department")
                        or ""
                    ),
                    "role": (
                        officer_info.get("role")
                        or ""
                    ),
                    "product_id": (
                        final.get("product_id")
                        or product_id
                    ),
                    "view_names": (
                        view_names
                        or []
                    ),
                    "is_compliant": is_comp,
                    "confidence_score": score,
                    "summary": (
                        comp_dict.get(
                            "summary",
                            "",
                        )
                        if comp_dict
                        else ""
                    ),
                    "needs_manual_review": bool(
                        comp_dict.get(
                            "needs_manual_review",
                            False,
                        )
                    )
                    if comp_dict
                    else False,
                    "extracted_fields": (
                        merged_fields
                        or {}
                    ),
                    "violations": (
                        comp_dict.get(
                            "violations",
                            [],
                        )
                        if comp_dict
                        else []
                    ),
                    "missing_fields": (
                        comp_dict.get(
                            "missing_fields",
                            [],
                        )
                        if comp_dict
                        else []
                    ),
                    "warnings": (
                        comp_dict.get(
                            "warnings",
                            [],
                        )
                        if comp_dict
                        else []
                    ),
                }

                supabase_client_with_session(
                    officer_info.get("supabase_access_token"),
                    officer_info.get("supabase_refresh_token"),
                ) \
                    .table("inspection_records") \
                    .insert(record) \
                    .execute()

            except Exception as db_exc:

                logger.warning(
                    "Failed to persist inspection record: %s",
                    db_exc,
                )

    except Exception as exc:

        logger.exception(
            "OCR job %s failed",
            job_id,
        )

        job = _JOBS.get(job_id)

        if job is not None:

            job["status"] = "failed"
            job["error"] = str(exc)


@router.post(
    "/jobs",
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_job(
    request: Request,
    files: List[UploadFile] = File(...),
    view_names: Optional[str] = Form(None),
    product_id: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    user=Depends(get_current_user),
):

    parsed_views: Optional[List[str]] = None

    if view_names:

        try:

            parsed = json.loads(view_names)

        except (
            json.JSONDecodeError,
            TypeError,
        ) as exc:

            raise HTTPException(
                status_code=400,
                detail="view_names must be a JSON array",
            ) from exc

        if (
            not isinstance(parsed, list)
            or len(parsed) != len(files)
            or not all(
                isinstance(v, str)
                and v in {
                    "front",
                    "back",
                    "side",
                }
                for v in parsed
            )
            or len(set(parsed)) != len(parsed)
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "view_names must contain unique "
                    "front/back/side entries"
                ),
            )

        parsed_views = parsed

    parsed_metadata: Dict[str, Any] = {}

    if metadata:

        try:

            parsed_metadata = json.loads(
                metadata
            )

        except json.JSONDecodeError as exc:

            raise HTTPException(
                status_code=400,
                detail="metadata must be valid JSON",
            ) from exc

    job_id = str(uuid.uuid4())

    upload_dir = (
        Path(__file__).resolve().parent
        / "ocr_uploads"
        / job_id
    )

    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    saved_paths: List[
        Union[str, Path]
    ] = []

    for idx, upload in enumerate(files):

        filename = (
            upload.filename
            or "image.png"
        )

        suffix = (
            Path(filename).suffix
            or ".png"
        )

        dest = (
            upload_dir
            / f"img_{idx}{suffix}"
        )

        content = await upload.read()

        dest.write_bytes(content)

        saved_paths.append(dest)

    now = datetime.now(
        timezone.utc
    ).isoformat()

    supabase_access_token = request.cookies.get(
        ACCESS_COOKIE
    )
    supabase_refresh_token = request.cookies.get(
        REFRESH_COOKIE
    )

    user_metadata = (
        getattr(
            user,
            "user_metadata",
            {},
        )
        or getattr(
            user,
            "raw_user_meta_data",
            {},
        )
        or {}
    )

    officer_info = {
        "supabase_access_token": supabase_access_token,
        "supabase_refresh_token": supabase_refresh_token,
        "officer_user_id": getattr(
            user,
            "id",
            None,
        ),
        "officer_email": getattr(
            user,
            "email",
            None,
        ),
        "officer_id": (
            user_metadata.get(
                "officer_id"
            )
            or getattr(
                user,
                "email",
                "UNKNOWN",
            )
        ),
        "officer_name": (
            user_metadata.get(
                "full_name"
            )
            or ""
        ),
        "department": (
            user_metadata.get(
                "department"
            )
            or ""
        ),
        "role": (
            user_metadata.get(
                "role"
            )
            or ""
        ),
    }

    _JOBS[job_id] = {
        "status": "queued",
        "owner": getattr(
            user,
            "id",
            None,
        ),
        "created_at": now,
        "metadata": parsed_metadata,
    }

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

    return JSONResponse(
        {
            "job_id": job_id,
            "status": "queued",
            "submitted_at": now,
        },
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get(
    "/jobs/{job_id}"
)
async def get_job_status(
    job_id: str,
    user=Depends(get_current_user),
):

    job = _JOBS.get(job_id)

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    if job.get("owner") != getattr(
        user,
        "id",
        None,
    ):

        raise HTTPException(
            status_code=403,
            detail="Not authorized",
        )

    response = {
        "job_id": job_id,
        "status": job["status"],
    }

    if job["status"] == "failed":

        response["error"] = job.get(
            "error",
            "Analysis failed",
        )

    return response


@router.get(
    "/jobs/{job_id}/result"
)
async def get_job_result(
    job_id: str,
    user=Depends(get_current_user),
):

    job = _JOBS.get(job_id)

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    if job.get("owner") != getattr(
        user,
        "id",
        None,
    ):

        raise HTTPException(
            status_code=403,
            detail="Not authorized",
        )

    if job["status"] != "completed":

        raise HTTPException(
            status_code=409,
            detail="Job not completed yet",
        )

    return job["result"]


@router.post(
    "/jobs/{job_id}/recheck"
)
async def recheck_compliance(
    job_id: str,
    payload: dict,
    user=Depends(get_current_user),
):
    """Re-run deterministic compliance using officer-corrected fields."""

    job = _JOBS.get(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    if job.get("owner") != getattr(
        user,
        "id",
        None,
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized",
        )

    if job.get("status") != "completed":
        raise HTTPException(
            status_code=409,
            detail="Job not completed yet",
        )

    result = job.get("result")

    if not isinstance(result, dict):
        raise HTTPException(
            status_code=404,
            detail="No result found",
        )

    corrected_fields = payload.get("fields")

    if not isinstance(corrected_fields, dict):
        raise HTTPException(
            status_code=400,
            detail="fields must be an object",
        )

    current_fields = dict(
        result.get(
            "merged_fields",
            {},
        )
    )

    # Only update known extracted fields.
    allowed_fields = {
        "brand",
        "product_name",
        "generic_name",
        "net_quantity",
        "mrp",
        "mrp_inclusive_of_taxes",
        "unit_sale_price",
        "manufacturer_address",
        "packer",
        "importer",
        "consumer_care",
        "mfg_date",
        "best_before",
        "use_by",
        "country_of_origin",
        "product_type",
        "specific_product",
        "is_food",
        "is_cosmetic",
        "is_electronic",
        "is_imported",
        "has_shelf_life",
    }

    for field, value in corrected_fields.items():
        if field in allowed_fields:
            current_fields[field] = value

    # Re-create the exact Rule Engine input from the corrected values.
    try:
        rule_input = map_to_rule_engine(
            current_fields
        )

        compliance_result = run_compliance_check(
            rule_input
        )

    except Exception as exc:
        logger.exception(
            "Re-check failed for job %s",
            job_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Compliance re-check failed: {exc}",
        ) from exc

    comp_dict = (
        compliance_result
        if isinstance(compliance_result, dict)
        else None
    )

    if comp_dict is None:
        raise HTTPException(
            status_code=500,
            detail="Compliance re-check returned no result",
        )

    # Record that these are officer-corrected values.
    result["merged_fields"] = current_fields
    result["compliance_result"] = comp_dict

    result["manual_corrections"] = {
        field: {
            "original": result.get(
                "original_merged_fields",
                {}
            ).get(field),
            "corrected": current_fields.get(field),
        }
        for field in allowed_fields
        if result.get(
            "original_merged_fields",
            {}
        ).get(field) != current_fields.get(field)
    }

    # Refresh AI fix suggestions using the corrected values.
    try:
        result["ai_fix_suggestions"] = (
            generate_ai_fix_suggestions(
                violations=comp_dict.get(
                    "violations",
                    [],
                ),
                product_fields=current_fields,
            )
        )
    except Exception as exc:
        logger.warning(
            "AI fix suggestion refresh failed after re-check "
            "for job %s: %s",
            job_id,
            exc,
        )

    logger.info(
        "Job %s compliance re-checked. New score: %s",
        job_id,
        comp_dict.get("score"),
    )

    return {
        "merged_fields": current_fields,
        "compliance_result": comp_dict,
        "field_confidence": result.get(
            "field_confidence",
            {},
        ),
        "ai_fix_suggestions": result.get(
            "ai_fix_suggestions",
            [],
        ),
        "manual_corrections": result.get(
            "manual_corrections",
            {},
        ),
    }


@router.get(
    "/jobs/{job_id}/pdf"
)
async def download_compliance_pdf(
    job_id: str,
    user=Depends(get_current_user),
):

    """Generate and download PDF compliance report."""

    job = _JOBS.get(job_id)

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    if job.get("owner") != getattr(
        user,
        "id",
        None,
    ):

        raise HTTPException(
            status_code=403,
            detail="Not authorized",
        )

    if job["status"] != "completed":

        raise HTTPException(
            status_code=409,
            detail="Job not completed yet",
        )

    result = job.get("result")

    if not result:

        raise HTTPException(
            status_code=404,
            detail="No result found",
        )

    compliance = result.get(
        "compliance_result"
    )

    merged_fields = result.get(
        "merged_fields",
        {},
    )

    field_confidence = result.get(
        "field_confidence",
        {},
    )

    ai_fix_suggestions = result.get(
        "ai_fix_suggestions",
        [],
    )

    visual_boxes = result.get(
        "visual_boxes",
        {},
    )

    if not compliance:

        raise HTTPException(
            status_code=400,
            detail="No compliance result available",
        )

    try:

        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf",
        )

        pdf_path = temp_file.name

        temp_file.close()

        generate_report(
            structured=merged_fields,
            compliance=compliance,
            output_path=pdf_path,
            field_confidence=field_confidence,
            ai_fix_suggestions=ai_fix_suggestions,
            visual_boxes=visual_boxes,
            manual_corrections=result.get(
                "manual_corrections",
                {},
            ),
        )

        return FileResponse(
            path=pdf_path,
            filename=(
                f"Compliance_Report_"
                f"{job_id[:8]}.pdf"
            ),
            media_type="application/pdf",
        )

    except Exception as e:

        logger.exception(
            "Failed to generate PDF for job %s",
            job_id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"PDF generation failed: {str(e)}"
            ),
        )


@router.get(
    "/records"
)
async def get_past_records(
    request: Request,
    user=Depends(get_current_user),
):

    try:

        user_metadata = (
            getattr(
                user,
                "user_metadata",
                {},
            )
            or getattr(
                user,
                "raw_user_meta_data",
                {},
            )
            or {}
        )

        officer_id = (
            user_metadata.get(
                "officer_id"
            )
            or getattr(
                user,
                "email",
                None,
            )
        )

        user_id = getattr(
            user,
            "id",
            None,
        )

        query = (
            supabase_client_with_session(
                request.cookies.get(ACCESS_COOKIE),
                request.cookies.get(REFRESH_COOKIE),
            )
            .table(
                "inspection_records"
            )
            .select("*")
            .order(
                "created_at",
                desc=True,
            )
        )

        if user_id:

            query = query.or_(
                f"officer_user_id.eq.{user_id},"
                f"officer_id.eq.{officer_id}"
            )

        response = query.limit(
            50
        ).execute()

        return response.data or []

    except Exception as exc:

        logger.warning(
            "Failed to fetch past records: %s",
            exc,
        )

        return []
