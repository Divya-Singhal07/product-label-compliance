"""Image quality metrics used to drive adaptive preprocessing decisions."""

from __future__ import annotations

from typing import Any, Dict

import cv2
import numpy as np


def analyze_image_quality(image: np.ndarray) -> Dict[str, Any]:
    """
    Compute basic quality metrics on a BGR image.

    Returns a dictionary containing numeric scores and boolean flags
    that later stages use to decide whether a particular enhancement
    should be applied.
    """
    if image is None or image.size == 0:
        raise ValueError("Empty image passed to quality analysis")

    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image

    # Brightness (mean intensity)
    brightness = float(np.mean(gray))

    # Contrast (standard deviation)
    contrast = float(np.std(gray))

    # Blur score – variance of Laplacian (higher = sharper)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    blur_score = float(lap.var())

    # Simple noise estimate: high-frequency residual after mild blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    noise_est = float(np.mean(np.abs(gray.astype(np.float32) - blurred.astype(np.float32))))

    # Decision flags (thresholds are intentionally conservative)
    is_dark = brightness < 70.0
    is_bright = brightness > 200.0
    is_low_contrast = contrast < 35.0
    is_blurry = blur_score < 80.0
    is_noisy = noise_est > 12.0
    is_low_res = min(h, w) < 600

    return {
        "width": w,
        "height": h,
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "blur_score": round(blur_score, 2),
        "noise_estimate": round(noise_est, 2),
        "is_dark": is_dark,
        "is_bright": is_bright,
        "is_low_contrast": is_low_contrast,
        "is_blurry": is_blurry,
        "is_noisy": is_noisy,
        "is_low_res": is_low_res,
    }
