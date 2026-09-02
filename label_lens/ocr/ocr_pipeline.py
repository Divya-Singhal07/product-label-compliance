"""
OCR + Field Extraction + Auto Product ID pipeline.

Supports:
- Multi-view processing (front / back / side)
- Multiple OCR preprocessing candidates
- LLM extraction
- Rule-based fallback
- Consistent field schema
- Smart multi-view merging
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .field_extractor import extract_fields
from .llm_extractor import extract_fields_with_llm
from .paddle_runner import run_ocr_on_candidates
from .product_id import generate_product_id

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Canonical field schema
# ---------------------------------------------------------------------

FIELD_DEFAULTS: Dict[str, Any] = {
    "brand": None,
    "product_name": None,
    "generic_name": None,
    "net_quantity": None,
    "mrp": None,
    "mrp_inclusive_of_taxes": False,
    "unit_sale_price": None,
    "manufacturer_address": None,
    "packer": None,
    "importer": None,
    "consumer_care": None,
    "mfg_date": None,
    "best_before": None,
    "use_by": None,
    "country_of_origin": None,
    "product_type": "general",
    "specific_product": None,
    "is_food": False,
    "is_cosmetic": False,
    "is_electronic": False,
    "is_imported": False,
    "has_shelf_life": False,
}


class OCRProcessor:

    def __init__(
        self,
        preferred_candidates: Optional[List[str]] = None,
    ):
        self.preferred_candidates = preferred_candidates or [
            "sharpened",
            "enhanced",
            "illumination_corrected",
            "original",
            "denoised",
        ]

    # -----------------------------------------------------------------
    # Normalize extracted fields
    # -----------------------------------------------------------------

    def _normalize_fields(
        self,
        fields: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:

        normalized = dict(FIELD_DEFAULTS)

        if not isinstance(fields, dict):
            return normalized

        # Copy known canonical fields
        for key in normalized:
            if key in fields:
                normalized[key] = fields[key]

        # -------------------------------------------------------------
        # Backward compatibility with old field names
        # -------------------------------------------------------------

        if (
            normalized["mfg_date"] is None
            and fields.get("manufacturing_date")
        ):
            normalized["mfg_date"] = fields["manufacturing_date"]

        if (
            normalized["mfg_date"] is None
            and fields.get("mfg_or_expiry_date")
        ):
            normalized["mfg_date"] = fields["mfg_or_expiry_date"]

        if (
            normalized["use_by"] is None
            and fields.get("expiry_date")
        ):
            normalized["use_by"] = fields["expiry_date"]

        return normalized

    # -----------------------------------------------------------------
    # Process one image/view
    # -----------------------------------------------------------------

    def process_view(
        self,
        preprocessed_result: Dict[str, Any],
        use_llm: bool = True,
    ) -> Dict[str, Any]:

        candidates = preprocessed_result.get("images", {})

        if not candidates:
            raise ValueError(
                "No preprocessed images found in result"
            )

        # -------------------------------------------------------------
        # OCR
        # -------------------------------------------------------------

        ocr_lines, best_candidate = run_ocr_on_candidates(
            candidates,
            preferred_order=self.preferred_candidates,
        )

        # -------------------------------------------------------------
        # Field extraction
        # -------------------------------------------------------------

        if use_llm:
            try:
                fields = extract_fields_with_llm(ocr_lines)
                method = "llm"

            except Exception as e:
                logger.warning(
                    "LLM extraction failed (%s). "
                    "Falling back to deterministic rules.",
                    e,
                )

                fields = extract_fields(ocr_lines)["fields"]
                method = "rules"

        else:
            fields = extract_fields(ocr_lines)["fields"]
            method = "rules"

        fields = self._normalize_fields(fields)

        return {
            "view": preprocessed_result.get(
                "view",
                "unknown",
            ),
            "best_candidate": best_candidate,
            "ocr_lines": ocr_lines,
            "fields": fields,
            "extraction_method": method,
            "num_lines": len(ocr_lines),
            "quality_metrics": preprocessed_result.get(
                "quality_metrics"
            ),
        }

    # -----------------------------------------------------------------
    # Merge multi-view fields
    # -----------------------------------------------------------------

    def _merge_fields(
        self,
        view_outputs: Dict[str, Dict],
    ) -> Dict[str, Any]:

        priority = {
            "brand": [
                "front",
                "side",
                "back",
            ],

            "generic_name": [
                "front",
                "side",
                "back",
            ],

            "product_name": [
                "front",
                "side",
                "back",
            ],

            "net_quantity": [
                "front",
                "side",
                "back",
            ],

            "mrp": [
                "front",
                "back",
                "side",
            ],

            "mrp_inclusive_of_taxes": [
                "front",
                "back",
                "side",
            ],

            "unit_sale_price": [
                "front",
                "back",
                "side",
            ],

            "manufacturer_address": [
                "back",
                "side",
                "front",
            ],

            "packer": [
                "back",
                "side",
                "front",
            ],

            "importer": [
                "back",
                "side",
                "front",
            ],

            "consumer_care": [
                "back",
                "side",
                "front",
            ],

            "mfg_date": [
                "back",
                "side",
                "front",
            ],

            "best_before": [
                "back",
                "side",
                "front",
            ],

            "use_by": [
                "back",
                "side",
                "front",
            ],

            "country_of_origin": [
                "back",
                "side",
                "front",
            ],

            "product_type": [
                "front",
                "back",
                "side",
            ],

            "specific_product": [
                "front",
                "back",
                "side",
            ],

            "is_food": [
                "front",
                "back",
                "side",
            ],

            "is_cosmetic": [
                "front",
                "back",
                "side",
            ],

            "is_electronic": [
                "front",
                "back",
                "side",
            ],

            "is_imported": [
                "front",
                "back",
                "side",
            ],

            "has_shelf_life": [
                "back",
                "side",
                "front",
            ],
        }

        merged = dict(FIELD_DEFAULTS)

        for field, views_order in priority.items():

            for view in views_order:

                if view not in view_outputs:
                    continue

                view_data = view_outputs[view]

                if "fields" not in view_data:
                    continue

                candidate = view_data["fields"].get(field)

                # -----------------------------------------------------
                # IMPORTANT:
                # False and 0 are valid values.
                # Only None / empty string mean "missing".
                # -----------------------------------------------------

                if candidate is not None and candidate != "":
                    merged[field] = candidate
                    break

        return merged

    # -----------------------------------------------------------------
    # Process complete product
    # -----------------------------------------------------------------

    def process_product(
        self,
        batch_result: Dict[str, Any],
        front_view_name: str = "front",
        use_llm: bool = True,
    ) -> Dict[str, Any]:

        results = batch_result.get(
            "results",
            {},
        )

        view_outputs: Dict[str, Dict] = {}

        # -------------------------------------------------------------
        # Process every view
        # -------------------------------------------------------------

        for view_name, pre_res in results.items():

            if "error" in pre_res:
                view_outputs[view_name] = {
                    "error": pre_res["error"]
                }
                continue

            try:
                view_outputs[view_name] = self.process_view(
                    pre_res,
                    use_llm=use_llm,
                )

            except Exception as e:
                logger.exception(
                    "OCR processing failed for view '%s'",
                    view_name,
                )

                view_outputs[view_name] = {
                    "error": str(e)
                }

        # -------------------------------------------------------------
        # Merge fields
        # -------------------------------------------------------------

        merged_fields = self._merge_fields(
            view_outputs
        )

        # -------------------------------------------------------------
        # Auto product ID
        # -------------------------------------------------------------

        product_id = generate_product_id(
            brand=merged_fields.get("brand"),
            product_name=merged_fields.get(
                "product_name"
            ),
            net_quantity=merged_fields.get(
                "net_quantity"
            ),
        )

        # -------------------------------------------------------------
        # Return complete result
        # -------------------------------------------------------------

        return {
            "product_id": product_id,

            "product_folder": batch_result.get(
                "product_folder"
            ),

            "views": view_outputs,

            "merged_fields": merged_fields,

            "front_fields": (
                view_outputs
                .get(front_view_name, {})
                .get("fields", {})
            ),

            "ready_for_rule_engine": True,
        }
