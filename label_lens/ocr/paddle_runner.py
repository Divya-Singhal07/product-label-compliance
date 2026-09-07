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

    original_height, original_width = image.shape[:2]
    print(f">>> Running OCR on image shape: {image.shape}")

    # PaddleOCR has a max-side limit of 4000. Resize explicitly so
    # we know exactly how to map OCR coordinates back to the input image.
    max_side = 4000
    scale = min(1.0, max_side / max(original_height, original_width))

    if scale < 1.0:
        ocr_width = max(1, int(round(original_width * scale)))
        ocr_height = max(1, int(round(original_height * scale)))
        ocr_image = cv2.resize(
            image,
            (ocr_width, ocr_height),
            interpolation=cv2.INTER_AREA,
        )
        print(
            f">>> Pre-resized OCR image: "
            f"{original_width}x{original_height} -> "
            f"{ocr_width}x{ocr_height}"
        )
    else:
        ocr_image = image
        scale = 1.0

    try:
        result = engine.ocr(ocr_image)
    except Exception as e:
        print(f">>> engine.ocr() failed: {e}")
        logger.exception("engine.ocr failed")
        return []

    if not result:
        print(">>> OCR returned empty result")
        return []

    def restore_polygon(polygon):
        if polygon is None:
            return None

        try:
            points = np.asarray(polygon, dtype=np.float32).reshape(-1, 2)

            if scale != 1.0:
                points[:, 0] /= scale
                points[:, 1] /= scale

            points[:, 0] = np.clip(points[:, 0], 0, original_width - 1)
            points[:, 1] = np.clip(points[:, 1], 0, original_height - 1)

            return points.tolist()
        except Exception:
            return polygon

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

                box = restore_polygon(box)

                lines.append({
                    "text": text,
                    "confidence": conf,
                    "box": box,
                    "polygon": box,
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
                    box = restore_polygon(box)

                    lines.append({
                        "text": text,
                        "confidence": float(conf),
                        "box": box,
                        "polygon": box,
                    })

        print(f">>> Parsed {len(lines)} lines (old format)")

    except Exception as e:
        print(f">>> Failed old format parsing: {e}")

    return lines

def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _polygon_to_bbox(polygon: Any) -> Optional[Tuple[float, float, float, float]]:
    if polygon is None:
        return None

    try:
        points = np.asarray(polygon, dtype=np.float32).reshape(-1, 2)
        if len(points) < 2:
            return None

        x_min = float(np.min(points[:, 0]))
        y_min = float(np.min(points[:, 1]))
        x_max = float(np.max(points[:, 0]))
        y_max = float(np.max(points[:, 1]))

        if x_max <= x_min or y_max <= y_min:
            return None

        return x_min, y_min, x_max, y_max
    except Exception:
        return None


def _bbox_iou(
    first: Any,
    second: Any,
) -> float:
    box_a = _polygon_to_bbox(first)
    box_b = _polygon_to_bbox(second)

    if box_a is None or box_b is None:
        return 0.0

    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0

    intersection = (ix2 - ix1) * (iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)

    union = area_a + area_b - intersection

    if union <= 0:
        return 0.0

    return intersection / union


def _merge_ocr_lines(
    all_lines: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []

    for line in all_lines:
        text = str(line.get("text", "")).strip()
        if not text:
            continue

        normalized = _normalize_text(text)
        duplicate_index = None

        for index, existing in enumerate(merged):
            existing_text = _normalize_text(
                str(existing.get("text", ""))
            )

            if normalized != existing_text:
                continue

            if _bbox_iou(
                line.get("polygon") or line.get("box"),
                existing.get("polygon") or existing.get("box"),
            ) >= 0.50:
                duplicate_index = index
                break

        if duplicate_index is None:
            merged.append(line)
            continue

        existing = merged[duplicate_index]

        if float(line.get("confidence", 0.0)) > float(
            existing.get("confidence", 0.0)
        ):
            merged[duplicate_index] = line

    return merged

def _map_rotated_polygon_to_original(
    polygon: Any,
    original_shape: Tuple[int, int, int],
) -> Any:
    """Map a polygon from 90-degree clockwise coordinates back to original."""
    if polygon is None:
        return None

    try:
        height, width = original_shape[:2]
        points = np.asarray(polygon, dtype=np.float32).reshape(-1, 2)

        mapped = []
        for x_rot, y_rot in points:
            x_orig = width - 1 - y_rot
            y_orig = x_rot
            mapped.append([float(x_orig), float(y_orig)])

        return mapped
    except Exception:
        return polygon

def run_ocr_on_image(image: np.ndarray, engine=None) -> List[Dict[str, Any]]:
    if engine is None:
        engine = get_ocr_engine()

    if image is None or image.size == 0:
        return []

    # Use the native image orientation for precise OCR geometry.
    # Rotated OCR can be enabled later as a fallback for genuinely
    # rotated labels, but should not be merged into normal geometry.
    orientations = [
        ("0deg", image),
    ]

    all_lines: List[Dict[str, Any]] = []

    for name, img in orientations:
        try:
            lines = _run_single_orientation(img, engine)
            print(f">>> Orientation {name}: {len(lines)} lines")

            for line in lines:
                line = dict(line)

                if name == "90deg":
                    line["polygon"] = _map_rotated_polygon_to_original(
                        line.get("polygon") or line.get("box"),
                        image.shape,
                    )

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
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:

    if preferred_order is None:
        preferred_order = ["enhanced", "original", "sharpened"]

    engine = get_ocr_engine()

    best_lines: List[Dict[str, Any]] = []
    all_candidate_lines: List[Dict[str, Any]] = []

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

        avg_conf = (
            sum(float(l.get("confidence", 0.0)) for l in lines)
            / max(len(lines), 1)
        )

        score = avg_conf * (1 + 0.1 * len(lines))

        print(
            f">>> Candidate '{name}' → "
            f"{len(lines)} lines, score={score:.3f}"
        )

        # Keep OCR text from every candidate for extraction.
        for line in lines:
            line_copy = dict(line)
            line_copy["ocr_candidate"] = name
            all_candidate_lines.append(line_copy)

        # Keep only the strongest candidate for visual boxes.
        if score > best_score:
            best_score = score
            best_lines = lines
            best_name = name

    # Merge text from all candidates for maximum extraction recall.
    extraction_lines = _merge_ocr_lines(all_candidate_lines)

    print(
        f">>> Extraction OCR: {len(extraction_lines)} unique lines"
    )

    print(
        f">>> Visual OCR: {len(best_lines)} lines "
        f"from candidate '{best_name}'"
    )

    return extraction_lines, best_lines, best_name
