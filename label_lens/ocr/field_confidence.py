from __future__ import annotations

import re
from typing import Any, Dict, List


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


def build_field_confidence(
    fields: Dict[str, Any],
    ocr_lines: List[Dict[str, Any]],
) -> Dict[str, float]:
    """
    Calculate confidence for every extracted text field using the
    actual PaddleOCR confidence of the OCR lines supporting that field.

    Output values are normalized to 0.0 - 1.0.
    """

    result: Dict[str, float] = {}

    for field in TEXT_FIELDS:
        value = fields.get(field)

        if value is None or not str(value).strip():
            continue

        value_text = str(value)

        candidates = []

        for line in ocr_lines:
            text = str(line.get("text", "") or "")
            ocr_conf = float(line.get("confidence", 0.0) or 0.0)

            if not text or ocr_conf <= 0:
                continue

            similarity = _similarity(value_text, text)

            if similarity > 0:
                candidates.append((similarity, ocr_conf))

        if not candidates:
            continue

        # Prefer the strongest textual match.
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)

        similarity, ocr_conf = candidates[0]

        # Small penalty when only part of a field was found in one OCR line.
        confidence = ocr_conf * (0.7 + 0.3 * similarity)

        result[field] = round(max(0.0, min(1.0, confidence)), 3)

    return result
