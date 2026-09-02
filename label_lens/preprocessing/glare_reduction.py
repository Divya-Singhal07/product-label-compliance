"""Conservative specular glare detection and reduction."""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np


def detect_glare(
    image: np.ndarray,
    v_thresh: int = 245,
    s_thresh: int = 40,
    min_area_ratio: float = 0.001,
) -> Tuple[np.ndarray, bool]:
    """
    Detect potential specular (glare) regions.

    Specular highlights usually have very high Value and low Saturation in HSV.
    Returns a binary mask and a boolean indicating whether significant glare was found.
    """
    if image.ndim != 3:
        raise ValueError("detect_glare expects a 3-channel BGR image")

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    # Bright and desaturated → likely glare
    mask = cv2.inRange(hsv, (0, 0, v_thresh), (180, s_thresh, 255))

    # Clean small noise
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    area_ratio = float(np.count_nonzero(mask)) / mask.size
    has_glare = area_ratio >= min_area_ratio

    return mask, has_glare


def reduce_glare(
    image: np.ndarray,
    mask: np.ndarray,
    blur_size: int = 21,
) -> np.ndarray:
    """
    Soften detected glare regions by inpainting-like blending with local median.
    Very conservative – only the masked pixels are touched.
    """
    if image.ndim != 3:
        raise ValueError("reduce_glare expects a 3-channel BGR image")

    if mask is None or np.count_nonzero(mask) == 0:
        return image.copy()

    # Local median as a simple inpaint substitute (preserves colour better than pure inpaint)
    median = cv2.medianBlur(image, blur_size if blur_size % 2 == 1 else blur_size + 1)

    result = image.copy()
    result[mask > 0] = median[mask > 0]
    return result
