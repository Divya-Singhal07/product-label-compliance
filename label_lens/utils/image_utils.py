"""Common image I/O and utility helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image


def ensure_dir(path: Union[str, Path]) -> Path:
    """Create directory (and parents) if it does not exist."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_image(path: Union[str, Path]) -> np.ndarray:
    """
    Load an image as BGR uint8 numpy array.
    Raises FileNotFoundError / ValueError on failure.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    # Prefer OpenCV; fall back to Pillow for exotic formats
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        try:
            pil = Image.open(path).convert("RGB")
            img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        except Exception as exc:
            raise ValueError(f"Cannot read image: {path}") from exc

    if img.ndim != 3 or img.shape[2] != 3:
        raise ValueError(f"Expected 3-channel BGR image, got shape {img.shape}")

    return img


def save_image(path: Union[str, Path], image: np.ndarray, quality: int = 95) -> None:
    """Save BGR or grayscale image. Creates parent dirs if needed."""
    path = Path(path)
    ensure_dir(path.parent)

    if image.ndim == 2:
        cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    else:
        cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, quality])


def resize_keep_aspect(
    image: np.ndarray,
    max_side: Optional[int] = None,
    min_side: Optional[int] = None,
    interpolation: int = cv2.INTER_AREA,
) -> np.ndarray:
    """
    Resize while preserving aspect ratio.
    - If max_side is set and the longer side exceeds it → downscale.
    - If min_side is set and the shorter side is below it → upscale.
    """
    h, w = image.shape[:2]
    scale = 1.0

    if max_side is not None:
        longer = max(h, w)
        if longer > max_side:
            scale = max_side / float(longer)

    if min_side is not None:
        shorter = min(h, w)
        if shorter * scale < min_side:
            scale = min_side / float(shorter)

    if abs(scale - 1.0) < 1e-3:
        return image.copy()

    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return cv2.resize(image, (new_w, new_h), interpolation=interpolation)


def to_rgb(image: np.ndarray) -> np.ndarray:
    """BGR → RGB."""
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def to_bgr(image: np.ndarray) -> np.ndarray:
    """RGB → BGR."""
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
