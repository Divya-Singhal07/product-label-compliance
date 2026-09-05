"""
PaddleOCR wrapper – Compatible with new PaddleOCR versions
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_ocr_engine = None


def get_ocr_engine(lang: str = "en"):
    global _ocr_engine

    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            print(">>> Initializing PaddleOCR...")

            # Try different initialization styles for compatibility
            try:
                # Newest style (no show_log, no use_angle_cls in some versions)
                _ocr_engine = PaddleOCR(lang=lang)
            except Exception as e1:
                print(f">>> First init style failed: {e1}")
                try:
                    _ocr_engine = PaddleOCR(use_angle_cls=True, lang=lang)
                except Exception as e2:
                    print(f">>> Second init style failed: {e2}")
                    _ocr_engine = PaddleOCR()

            print(">>> PaddleOCR initialized successfully")
            logger.info("PaddleOCR engine initialized successfully")

        except Exception as e:
            print(f">>> FAILED to initialize PaddleOCR: {e}")
            logger.exception("Failed to initialize PaddleOCR")
            raise

    return _ocr_engine


def _run_single_orientation(image: np.ndarray, engine) -> List[Dict[str, Any]]:
    if image is None or image.size == 0:
        print(">>> Empty image received")
        return []

    print(f">>> Running OCR on image shape: {image.shape}")

    try:
        result = engine.ocr(image)
    except Exception as e:
        print(f">>> engine.ocr() failed: {e}")
        logger.exception("engine.ocr failed")
        return []

    if not result:
        print(">>> OCR returned empty result")
        return []

    lines: List[Dict[str, Any]] = []
    first = result[0]

    # ------ New format (PP-OCRv6 / PaddleX) ------
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
                lines.append({
                    "text": text,
                    "confidence": conf,
                    "box": box,
                })
            print(f">>> Parsed {len(lines)} lines (new format)")
            return lines
        except Exception as e:
            print(f">>> Failed new format parsing: {e}")

    # ------ Old format ------
    try:
        data = first if isinstance(first, (list, tuple)) else result
        for item in data:
            if item is None:
                continue
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                box = item[0]
                text_info = item[1]
                if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                    text, conf = text_info[0], text_info[1]
                else:
                    text, conf = str(text_info), 0.9
                text = str(text).strip()
                if text:
                    lines.append({
                        "text": text,
                        "confidence": float(conf),
                        "box": box,
                    })
        print(f">>> Parsed {len(lines)} lines (old format)")
    except Exception as e:
        print(f">>> Failed old format parsing: {e}")

    return lines


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _merge_ocr_lines(all_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best_by_text: Dict[str, Dict[str, Any]] = {}
    for line in all_lines:
        text = str(line.get("text", "")).strip()
        if not text:
            continue
        key = _normalize_text(text)
        if key not in best_by_text or float(line.get("confidence", 0)) > float(
            best_by_text[key].get("confidence", 0)
        ):
            best_by_text[key] = line
    return list(best_by_text.values())


def run_ocr_on_image(image: np.ndarray, engine=None) -> List[Dict[str, Any]]:
    if engine is None:
        engine = get_ocr_engine()

    if image is None or image.size == 0:
        return []

    orientations = [
        ("0deg", image),
        ("90deg", cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)),
    ]

    all_lines: List[Dict[str, Any]] = []

    for name, img in orientations:
        try:
            lines = _run_single_orientation(img, engine)
            print(f">>> Orientation {name}: {len(lines)} lines")
            for line in lines:
                line = dict(line)
                line["orientation"] = name
                all_lines.append(line)
        except Exception as e:
            print(f">>> Orientation {name} failed: {e}")

    merged = _merge_ocr_lines(all_lines)
    print(f">>> Total unique lines after merge: {len(merged)}")
    return merged


def run_ocr_on_candidates(
    candidates: Dict[str, np.ndarray],
    preferred_order: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], str]:

    if preferred_order is None:
        preferred_order = ["enhanced", "original", "sharpened"]

    engine = get_ocr_engine()

    best_lines: List[Dict[str, Any]] = []
    best_score = -1.0
    best_name = "none"

    print(f">>> Available candidates: {list(candidates.keys())}")

    for name in preferred_order:
        if name not in candidates:
            print(f">>> Candidate '{name}' not found")
            continue

        img = candidates[name]
        print(f">>> Trying candidate: {name}")

        lines = run_ocr_on_image(img, engine=engine)

        if not lines:
            print(f">>> Candidate '{name}' returned 0 lines")
            continue

        avg_conf = sum(float(l.get("confidence", 0.0)) for l in lines) / max(len(lines), 1)
        score = avg_conf * (1 + 0.1 * len(lines))

        print(f">>> Candidate '{name}' → {len(lines)} lines, score={score:.3f}")

        if score > best_score:
            best_score = score
            best_lines = lines
            best_name = name

    print(f">>> Best candidate: {best_name} with {len(best_lines)} lines")
    return best_lines, best_name
