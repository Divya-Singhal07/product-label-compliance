"""
OCR + Field Extraction + Auto Product ID pipeline
Balanced version (Speed + Reliability)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .field_extractor import extract_fields
from .field_confidence import build_field_confidence, build_field_boxes
from .llm_extractor import extract_fields_with_llm
from .paddle_runner import run_ocr_on_candidates
from .code_scanner import scan_codes
from .product_id import generate_product_id

logger = logging.getLogger(__name__)


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

    def __init__(self, preferred_candidates: Optional[List[str]] = None):
        # Balanced: 3 candidates
        self.preferred_candidates = preferred_candidates or [
            "enhanced",
            "original",
            "sharpened",
        ]

    def _normalize_fields(self, fields: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        normalized = dict(FIELD_DEFAULTS)

        if not isinstance(fields, dict):
            return normalized

        for key in normalized:
            if key in fields:
                normalized[key] = fields[key]

        if normalized["mfg_date"] is None and fields.get("manufacturing_date"):
            normalized["mfg_date"] = fields["manufacturing_date"]

        if normalized["mfg_date"] is None and fields.get("mfg_or_expiry_date"):
            normalized["mfg_date"] = fields["mfg_or_expiry_date"]

        if normalized["use_by"] is None and fields.get("expiry_date"):
            normalized["use_by"] = fields["expiry_date"]

        return normalized

    @staticmethod
    def _map_field_boxes_to_original(
        field_boxes: Dict[str, Dict[str, Any]],
        preprocessed_result: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Map OCR coordinates from the processed image back to the
        original uploaded image coordinates.
        """

        original = preprocessed_result.get("original_dimensions", {})
        processed = preprocessed_result.get("processed_dimensions", {})

        original_width = float(original.get("width", 0) or 0)
        original_height = float(original.get("height", 0) or 0)
        processed_width = float(processed.get("width", 0) or 0)
        processed_height = float(processed.get("height", 0) or 0)

        if (
            original_width <= 0
            or original_height <= 0
            or processed_width <= 0
            or processed_height <= 0
        ):
            return field_boxes

        scale_x = original_width / processed_width
        scale_y = original_height / processed_height

        mapped: Dict[str, Dict[str, Any]] = {}

        for field, data in field_boxes.items():
            item = dict(data)

            polygon = item.get("polygon")
            if polygon:
                mapped_polygon = []

                for point in polygon:
                    if len(point) < 2:
                        continue

                    x = max(
                        0.0,
                        min(
                            original_width,
                            float(point[0]) * scale_x,
                        ),
                    )
                    y = max(
                        0.0,
                        min(
                            original_height,
                            float(point[1]) * scale_y,
                        ),
                    )

                    mapped_polygon.append(
                        [
                            round(x, 2),
                            round(y, 2),
                        ]
                    )

                item["polygon"] = mapped_polygon

                if mapped_polygon:
                    xs = [point[0] for point in mapped_polygon]
                    ys = [point[1] for point in mapped_polygon]

                    item["box"] = [
                        round(min(xs), 2),
                        round(min(ys), 2),
                        round(max(xs), 2),
                        round(max(ys), 2),
                    ]

            elif item.get("box"):
                box = item["box"]

                if len(box) == 4:
                    x1 = max(
                        0.0,
                        min(original_width, float(box[0]) * scale_x),
                    )
                    y1 = max(
                        0.0,
                        min(original_height, float(box[1]) * scale_y),
                    )
                    x2 = max(
                        0.0,
                        min(original_width, float(box[2]) * scale_x),
                    )
                    y2 = max(
                        0.0,
                        min(original_height, float(box[3]) * scale_y),
                    )

                    item["box"] = [
                        round(x1, 2),
                        round(y1, 2),
                        round(x2, 2),
                        round(y2, 2),
                    ]

            mapped[field] = item

        return mapped

    def process_view(self, preprocessed_result: Dict[str, Any], use_llm: bool = True) -> Dict[str, Any]:
        candidates = preprocessed_result.get("images", {})

        if not candidates:
            raise ValueError("No preprocessed images found in result")

        # Scan the original uploaded image for QR codes and barcodes.
        code_scan = {
            "image": preprocessed_result.get("source_path"),
            "qr_codes": [],
            "barcodes": [],
            "total_codes": 0,
        }

        source_path = preprocessed_result.get("source_path")

        if source_path:
            try:
                code_scan = scan_codes(source_path)
            except Exception as e:
                logger.warning(
                    "Code scanning failed for view '%s': %s",
                    preprocessed_result.get("view", "unknown"),
                    e,
                )

        # Code verification is intentionally conservative:
        # decoding a code is not the same as proving the external
        # information behind it is authentic.
        #
        # Barcode: corroborate decoded value against OCR text.
        # QR: successfully decoded, but external supplier verification
        # is not claimed yet.
        for qr in code_scan.get("qr_codes", []):
            qr["verification"] = {
                "status": "DECODED",
                "message": "QR payload decoded successfully; external source not verified.",
            }

        ocr_lines, visual_ocr_lines, best_candidate = run_ocr_on_candidates(
            candidates,
            preferred_order=self.preferred_candidates,
        )

        if use_llm:
            try:
                fields = extract_fields_with_llm(ocr_lines)
                method = "llm"
            except Exception as e:
                logger.warning("LLM extraction failed (%s). Falling back to rules.", e)
                fields = extract_fields(ocr_lines)["fields"]
                method = "rules"
        else:
            fields = extract_fields(ocr_lines)["fields"]
            method = "rules"

        fields = self._normalize_fields(fields)
        ocr_text_normalized = " ".join(
            str(line.get("text", "") or "").strip()
            for line in ocr_lines
        ).lower()

        for barcode in code_scan.get("barcodes", []):
            barcode_value = str(
                barcode.get("data", "") or ""
            ).strip()

            if barcode_value and barcode_value.lower() in ocr_text_normalized:
                barcode["verification"] = {
                    "status": "LABEL_MATCH",
                    "message": "Decoded barcode also appears in OCR text.",
                }
            else:
                barcode["verification"] = {
                    "status": "NO_OCR_MATCH",
                    "message": "Barcode decoded, but its value was not found in OCR text.",
                }

        field_confidence = build_field_confidence(fields, ocr_lines)
        field_boxes = build_field_boxes(fields, visual_ocr_lines)
        field_boxes = self._map_field_boxes_to_original(
            field_boxes,
            preprocessed_result,
        )

        return {
            "view": preprocessed_result.get("view", "unknown"),
            "best_candidate": best_candidate,
            "ocr_lines": ocr_lines,
            "fields": fields,
            "field_confidence": field_confidence,
            "field_boxes": field_boxes,
            "code_scan": code_scan,
            "extraction_method": method,
            "num_lines": len(ocr_lines),
            "quality_metrics": preprocessed_result.get("quality_metrics"),
        }

    def _merge_fields(self, view_outputs: Dict[str, Dict]) -> Dict[str, Any]:
        priority = {
            "brand": ["front", "side", "back"],
            "generic_name": ["front", "side", "back"],
            "product_name": ["front", "side", "back"],
            "net_quantity": ["front", "side", "back"],
            "mrp": ["front", "back", "side"],
            "mrp_inclusive_of_taxes": ["front", "back", "side"],
            "unit_sale_price": ["front", "back", "side"],
            "manufacturer_address": ["back", "side", "front"],
            "packer": ["back", "side", "front"],
            "importer": ["back", "side", "front"],
            "consumer_care": ["back", "side", "front"],
            "mfg_date": ["back", "side", "front"],
            "best_before": ["back", "side", "front"],
            "use_by": ["back", "side", "front"],
            "country_of_origin": ["back", "side", "front"],
            "product_type": ["front", "back", "side"],
            "specific_product": ["front", "back", "side"],
            "is_food": ["front", "back", "side"],
            "is_cosmetic": ["front", "back", "side"],
            "is_electronic": ["front", "back", "side"],
            "is_imported": ["front", "back", "side"],
            "has_shelf_life": ["back", "side", "front"],
        }

        merged = dict(FIELD_DEFAULTS)
        field_confidence: Dict[str, float] = {}

        for field, views_order in priority.items():
            for view in views_order:
                if view not in view_outputs:
                    continue

                view_data = view_outputs[view]

                if "fields" not in view_data:
                    continue

                candidate = view_data["fields"].get(field)

                if candidate is not None and candidate != "":
                    merged[field] = candidate

                    confidence = view_data.get(
                        "field_confidence",
                        {},
                    ).get(field)

                    if confidence is not None:
                        field_confidence[field] = confidence

                    break

        return {
            "fields": merged,
            "field_confidence": field_confidence,
        }

    def process_product(
        self,
        batch_result: Dict[str, Any],
        front_view_name: str = "front",
        use_llm: bool = True,
    ) -> Dict[str, Any]:

        results = batch_result.get("results", {})
        view_outputs: Dict[str, Dict] = {}

        for view_name, pre_res in results.items():
            if "error" in pre_res:
                view_outputs[view_name] = {"error": pre_res["error"]}
                continue
            try:
                view_outputs[view_name] = self.process_view(pre_res, use_llm=use_llm)
            except Exception as e:
                logger.exception("OCR processing failed for view '%s'", view_name)
                view_outputs[view_name] = {"error": str(e)}

        merged_result = self._merge_fields(view_outputs)

        merged_fields = merged_result["fields"]
        field_confidence = merged_result["field_confidence"]

        # Preserve the OCR evidence from all product views so downstream
        # rule validation can distinguish missing declarations from
        # information that is only referenced elsewhere (for example QR codes).
        raw_text_parts = []

        for view_name, view_data in view_outputs.items():
            for line in view_data.get("ocr_lines", []):
                line_text = str(line.get("text", "") or "").strip()
                if line_text:
                    raw_text_parts.append(
                        f"[{view_name}] {line_text}"
                    )

        raw_text = "\n".join(raw_text_parts)

        # Aggregate QR/barcode results across all product views.
        code_scans = {}

        for view_name, view_data in view_outputs.items():
            code_scans[view_name] = view_data.get(
                "code_scan",
                {
                    "image": None,
                    "qr_codes": [],
                    "barcodes": [],
                    "total_codes": 0,
                },
            )

        product_id = generate_product_id(
            brand=merged_fields.get("brand"),
            product_name=merged_fields.get("product_name"),
            net_quantity=merged_fields.get("net_quantity"),
        )

        return {
            "product_id": product_id,
            "product_folder": batch_result.get("product_folder"),
            "views": view_outputs,
            "merged_fields": merged_fields,
            "field_confidence": field_confidence,
            "raw_text": raw_text,
            "code_scans": code_scans,
            "front_fields": view_outputs.get(front_view_name, {}).get("fields", {}),
            "ready_for_rule_engine": True,
        }
