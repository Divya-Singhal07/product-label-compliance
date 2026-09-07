from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


TEXT_FIELDS = [
    "brand",
    "product_name",
    "generic_name",
    "net_quantity",
    "mrp",
    "unit_sale_price",
    "manufacturer_address",
    "packer",
    "importer",
    "consumer_care",
    "mfg_date",
    "best_before",
    "use_by",
    "country_of_origin",
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _similarity(value: str, ocr_text: str) -> float:
    value_n = _normalize(value)
    text_n = _normalize(ocr_text)

    if not value_n or not text_n:
        return 0.0

    if value_n in text_n:
        return 1.0

    value_words = set(re.findall(r"[a-z0-9]+", value_n))
    text_words = set(re.findall(r"[a-z0-9]+", text_n))

    if not value_words:
        return 0.0

    overlap = len(value_words & text_words) / len(value_words)
    return min(1.0, overlap)


def _polygon_to_bbox(
    polygon: Any,
) -> Optional[List[float]]:
    if polygon is None:
        return None

    try:
        points = []

        for point in polygon:
            if len(point) >= 2:
                points.append(
                    (
                        float(point[0]),
                        float(point[1]),
                    )
                )

        if not points:
            return None

        xs = [point[0] for point in points]
        ys = [point[1] for point in points]

        return [
            round(min(xs), 2),
            round(min(ys), 2),
            round(max(xs), 2),
            round(max(ys), 2),
        ]

    except Exception:
        return None


def _clean_polygon(
    polygon: Any,
) -> Optional[List[List[float]]]:
    if polygon is None:
        return None

    try:
        cleaned = []

        for point in polygon:
            if len(point) >= 2:
                cleaned.append(
                    [
                        round(float(point[0]), 2),
                        round(float(point[1]), 2),
                    ]
                )

        return cleaned if cleaned else None

    except Exception:
        return None


def _get_line_geometry(
    line: Dict[str, Any],
) -> Tuple[
    Optional[List[float]],
    Optional[List[List[float]]],
]:
    polygon = line.get("polygon")

    if polygon is not None:
        return (
            _polygon_to_bbox(polygon),
            _clean_polygon(polygon),
        )

    box = line.get("box")

    if box is not None:
        try:
            values = [float(value) for value in box]

            if len(values) == 4:
                bbox = [
                    round(values[0], 2),
                    round(values[1], 2),
                    round(values[2], 2),
                    round(values[3], 2),
                ]

                polygon = [
                    [bbox[0], bbox[1]],
                    [bbox[2], bbox[1]],
                    [bbox[2], bbox[3]],
                    [bbox[0], bbox[3]],
                ]

                return bbox, polygon

        except Exception:
            pass

    return None, None


def _find_best_line(
    value_text: str,
    ocr_lines: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    candidates = []

    for index, line in enumerate(ocr_lines):
        text = str(line.get("text", "") or "").strip()
        ocr_conf = float(line.get("confidence", 0.0) or 0.0)

        if not text or ocr_conf <= 0:
            continue

        similarity = _similarity(value_text, text)

        if similarity <= 0:
            continue

        candidates.append(
            {
                "index": index,
                "similarity": similarity,
                "ocr_confidence": ocr_conf,
                "line": line,
            }
        )

    if not candidates:
        return None

    # Textual similarity is the primary signal.
    # OCR confidence breaks ties.
    candidates.sort(
        key=lambda item: (
            item["similarity"],
            item["ocr_confidence"],
        ),
        reverse=True,
    )

    return candidates[0]


def build_field_confidence(
    fields: Dict[str, Any],
    ocr_lines: List[Dict[str, Any]],
) -> Dict[str, float]:
    """
    Calculate confidence for every extracted text field using
    the strongest matching PaddleOCR line.
    """

    result: Dict[str, float] = {}

    for field in TEXT_FIELDS:
        value = fields.get(field)

        if value is None or not str(value).strip():
            continue

        value_text = str(value)

        best = _find_best_line(
            value_text,
            ocr_lines,
        )

        if best is None:
            continue

        similarity = best["similarity"]
        ocr_conf = best["ocr_confidence"]

        confidence = ocr_conf * (
            0.7 + 0.3 * similarity
        )

        result[field] = round(
            max(0.0, min(1.0, confidence)),
            3,
        )

    return result


def build_field_boxes(
    fields: Dict[str, Any],
    ocr_lines: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Locate each extracted field on the original OCR image.

    Only the strongest OCR line supporting the extracted field
    receives a visual box.

    This intentionally does NOT create boxes for every OCR line.
    """

    result: Dict[str, Dict[str, Any]] = {}

    for field in TEXT_FIELDS:
        value = fields.get(field)

        if value is None or not str(value).strip():
            continue

        value_text = str(value)

        best = _find_best_line(
            value_text,
            ocr_lines,
        )

        if best is None:
            continue

        line = best["line"]

        bbox, polygon = _get_line_geometry(line)

        if bbox is None and polygon is None:
            continue

        similarity = best["similarity"]
        ocr_conf = best["ocr_confidence"]

        confidence = ocr_conf * (
            0.7 + 0.3 * similarity
        )

        result[field] = {
            "field": field,
            "text": str(line.get("text", "")).strip(),
            "confidence": round(
                max(0.0, min(1.0, confidence)),
                3,
            ),
            "similarity": round(
                max(0.0, min(1.0, similarity)),
                3,
            ),
            "ocr_confidence": round(
                max(0.0, min(1.0, ocr_conf)),
                3,
            ),
            "box": bbox,
            "polygon": polygon,
            "orientation": line.get(
                "orientation",
                "0deg",
            ),
        }

    return result
