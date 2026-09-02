"""Contrast, illumination, denoising, sharpening and mild deblur utilities."""

from __future__ import annotations

from typing import Any, Dict

import cv2
import numpy as np


def enhance_contrast(
    image: np.ndarray,
    clip_limit: float = 2.5,
    tile_grid_size: tuple = (8, 8),
) -> np.ndarray:
    """Stronger but still controlled CLAHE on L channel."""
    if image.ndim != 3:
        raise ValueError("enhance_contrast expects a 3-channel BGR image")

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    l_eq = clahe.apply(l)

    lab_eq = cv2.merge([l_eq, a, b])
    return cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)


def correct_illumination(
    image: np.ndarray,
    kernel_size: int = 61,
) -> np.ndarray:
    """
    Stronger uneven illumination / shadow reduction.
    Uses morphological background estimation + gentle gamma.
    """
    if image.ndim != 3:
        raise ValueError("correct_illumination expects a 3-channel BGR image")

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    k = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))

    background = cv2.morphologyEx(l, cv2.MORPH_OPEN, kernel)
    background = np.maximum(background, 1).astype(np.float32)
    l_f = l.astype(np.float32)

    normalised = (l_f / background) * np.mean(l_f)
    normalised = np.clip(normalised, 0, 255).astype(np.uint8)

    # Gentle gamma correction to lift dark areas
    gamma = 1.15
    table = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in range(256)]).astype("uint8")
    normalised = cv2.LUT(normalised, table)

    lab_corr = cv2.merge([normalised, a, b])
    return cv2.cvtColor(lab_corr, cv2.COLOR_LAB2BGR)


def denoise_image(
    image: np.ndarray,
    quality: Dict[str, Any],
    strength: int = 6,
) -> np.ndarray:
    """Edge-preserving denoising (bilateral). Applied only when noisy."""
    if not quality.get("is_noisy", False):
        return image.copy()

    return cv2.bilateralFilter(
        image, d=9, sigmaColor=strength * 9, sigmaSpace=strength * 9
    )


def sharpen_image(
    image: np.ndarray,
    amount: float = 0.7,
    radius: float = 1.0,
) -> np.ndarray:
    """Unsharp masking with controlled strength."""
    if image.ndim != 3:
        raise ValueError("sharpen_image expects a 3-channel BGR image")

    blurred = cv2.GaussianBlur(image, (0, 0), radius)
    sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def mild_deblur(image: np.ndarray) -> np.ndarray:
    """
    Very mild deblur using a combination of unsharp + slight contrast boost.
    Safe for packaging text (does not create heavy halos).
    """
    sharpened = sharpen_image(image, amount=0.45, radius=1.2)
    return enhance_contrast(sharpened, clip_limit=1.8)
