"""
PaddleOCR wrapper with rotation-aware OCR.

Designed for packaged-product labels where some declarations,
MRP stamps, batch numbers, dates, etc. may be printed vertically
or at unusual orientations.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_ocr_engine = None


def get_ocr_engine(lang: str = "en", use_angle_cls: bool = True):
    """
    Create and cache the PaddleOCR engine.

    PP-OCRv6 / PaddleX versions may not expose the same angle-classifier
    arguments, so we keep initialization compatible with the installed
    version and handle additional rotations ourselves.
    """
    global _ocr_engine

    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR

            try:
                _ocr_engine = PaddleOCR(
                    lang=lang,
                    use_doc_orientation_classify=True,
                    use_doc_unwarping=False,
                    use_textline_orientation=True,
                )
            except Exception:
                # Compatibility fallback for installations where the
                # newer orientation parameters are unavailable.
                _ocr_engine = PaddleOCR(lang=lang)

            logger.info("PaddleOCR engine initialized")

        except ImportError as e:
            raise ImportError(
                "PaddleOCR is not installed. Run: "
                "pip install paddlepaddle paddleocr"
            ) from e

    return _ocr_engine


def _run_single_orientation(
    image: np.ndarray,
    engine,
) -> List[Dict[str, Any]]:
    """
    Run PaddleOCR on one image orientation and normalize the result
    into our internal line format.
    """

    result = engine.ocr(image)

    if not result:
        return []

    lines: List[Dict[str, Any]] = []

    first = result[0]

    # ---------------------------------------------------------
    # New PP-OCRv6 / PaddleX OCRResult format
    # ---------------------------------------------------------
    if hasattr(first, "get") or isinstance(first, dict):
        try:
            texts = first.get("rec_texts") or first.get("texts") or []
            scores = first.get("rec_scores") or first.get("scores") or []
            polys = (
                first.get("rec_polys")
                or first.get("dt_polys")
                or first.get("rec_boxes")
                or []
            )

            for i, text in enumerate(texts):
                text = str(text).strip()

                if not text:
                    continue

                conf = float(scores[i]) if i < len(scores) else 0.0
                box = polys[i] if i < len(polys) else None

                if hasattr(box, "tolist"):
                    box = box.tolist()

                lines.append(
                    {
                        "text": text,
                        "confidence": conf,
                        "box": box,
                    }
                )

            return lines

        except Exception as e:
            logger.warning(
                "Failed parsing new OCRResult format: %s",
                e,
            )

    # ---------------------------------------------------------
    # Older PaddleOCR list format
    # ---------------------------------------------------------
    try:
        data = first if isinstance(first, (list, tuple)) else result

        for item in data:
            if item is None:
                continue

            if isinstance(item, (list, tuple)) and len(item) >= 2:
                box = item[0]
                text_info = item[1]

                if (
                    isinstance(text_info, (list, tuple))
                    and len(text_info) >= 2
                ):
                    text, conf = text_info[0], text_info[1]
                else:
                    text, conf = str(text_info), 0.9

                text = str(text).strip()

                if not text:
                    continue

                lines.append(
                    {
                        "text": text,
                        "confidence": float(conf),
                        "box": box,
                    }
                )

    except Exception as e:
        logger.warning(
            "Failed parsing old OCR format: %s",
            e,
        )

    return lines


def _normalize_text(text: str) -> str:
    """
    Normalize text for duplicate detection.
    """
    return re.sub(r"\s+", " ", text.strip().lower())


def _merge_ocr_lines(
    all_lines: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merge OCR results from multiple orientations.

    Duplicate text detected in more than one orientation is kept only
    once, preferring the higher-confidence result.
    """

    best_by_text: Dict[str, Dict[str, Any]] = {}

    for line in all_lines:
        text = str(line.get("text", "")).strip()

        if not text:
            continue

        key = _normalize_text(text)

        if key not in best_by_text:
            best_by_text[key] = line
        else:
            old_conf = float(
                best_by_text[key].get("confidence", 0.0)
            )
            new_conf = float(
                line.get("confidence", 0.0)
            )

            if new_conf > old_conf:
                best_by_text[key] = line

    return list(best_by_text.values())


def _looks_like_important_declaration(text: str) -> bool:
    """
    Identify text that is especially useful for packaged-product
    compliance.

    This gives rotated OCR extra importance for declarations such as:
    MRP, batch, date, expiry, quantity, etc.
    """

    t = text.lower()

    keywords = [
        "mrp",
        "maximum retail",
        "retail price",
        "incl",
        "inclusive",
        "unit sale",
        "batch",
        "mfd",
        "mfg",
        "manufact",
        "expiry",
        "exp",
        "best before",
        "use by",
        "net wt",
        "net weight",
        "quantity",
        "rs",
        "inr",
        "₹",
    ]

    return any(k in t for k in keywords)


def run_ocr_on_image(
    image: np.ndarray,
    engine=None,
) -> List[Dict[str, Any]]:
    """
    Run PaddleOCR on the original image plus rotated versions.

    0°   = normal label orientation
    90°  = catches vertically printed declarations
    270° = catches declarations printed in the opposite direction

    This is particularly useful for:
      - MRP
      - batch numbers
      - MFD / manufacturing date
      - expiry
      - small vertical declarations
    """

    if engine is None:
        engine = get_ocr_engine()

    if image is None or image.size == 0:
        return []

    orientations = [
        ("0deg", image),
        ("90deg", cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)),
        ("270deg", cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)),
    ]

    all_lines: List[Dict[str, Any]] = []

    for orientation_name, rotated_image in orientations:
        try:
            lines = _run_single_orientation(
                rotated_image,
                engine,
            )

            logger.info(
                "OCR orientation '%s' → %d lines",
                orientation_name,
                len(lines),
            )

            for line in lines:
                line = dict(line)
                line["orientation"] = orientation_name
                all_lines.append(line)

        except Exception as e:
            logger.warning(
                "OCR failed for orientation '%s': %s",
                orientation_name,
                e,
            )

    merged = _merge_ocr_lines(all_lines)

    # Put important compliance declarations first.
    merged.sort(
        key=lambda x: (
            _looks_like_important_declaration(
                str(x.get("text", ""))
            ),
            float(x.get("confidence", 0.0)),
        ),
        reverse=True,
    )

    logger.info(
        "Rotation-aware OCR → %d unique lines",
        len(merged),
    )

    return merged


def run_ocr_on_candidates(
    candidates: Dict[str, np.ndarray],
    preferred_order: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Try multiple preprocessed candidates and return the best OCR result.
    """

    if preferred_order is None:
        preferred_order = [
            "sharpened",
            "enhanced",
            "illumination_corrected",
            "original",
            "denoised",
        ]

    engine = get_ocr_engine()

    best_lines: List[Dict[str, Any]] = []
    best_score = -1.0
    best_name = "none"

    for name in preferred_order:
        if name not in candidates:
            continue

        img = candidates[name]

        lines = run_ocr_on_image(
            img,
            engine=engine,
        )

        if not lines:
            continue

        avg_conf = (
            sum(
                float(l.get("confidence", 0.0))
                for l in lines
            )
            / max(len(lines), 1)
        )

        important_count = sum(
            1
            for l in lines
            if _looks_like_important_declaration(
                str(l.get("text", ""))
            )
        )

        # Base score from OCR confidence and number of lines.
        score = avg_conf * (1 + 0.1 * len(lines))

        # Give a moderate bonus when compliance-related declarations
        # are actually detected.
        score += 0.15 * important_count

        logger.info(
            "OCR candidate '%s' → %d lines, "
            "avg_conf=%.3f, important=%d, score=%.3f",
            name,
            len(lines),
            avg_conf,
            important_count,
            score,
        )

        if score > best_score:
            best_score = score
            best_lines = lines
            best_name = name

    return best_lines, best_name
