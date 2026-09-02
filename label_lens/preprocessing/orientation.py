"""Skew / orientation correction for packaging images."""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np


def _estimate_skew_angle(gray: np.ndarray, max_angle: float = 15.0) -> float:
    """
    Estimate dominant text/line skew using Canny + HoughLines.
    Returns angle in degrees (positive = counter-clockwise).
    Limited to ±max_angle to avoid aggressive rotations on packaging.
    """
    h, w = gray.shape
    # Mild blur helps Hough
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=80,
        minLineLength=max(30, min(h, w) // 12),
        maxLineGap=20,
    )

    if lines is None or len(lines) < 5:
        return 0.0

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 == x1:
            continue
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Normalize to [-90, 90]
        if angle < -90:
            angle += 180
        elif angle > 90:
            angle -= 180
        # Prefer near-horizontal lines (most package text is horizontal)
        if abs(angle) < max_angle:
            angles.append(angle)

    if not angles:
        return 0.0

    # Robust central tendency
    median_angle = float(np.median(angles))
    # Clamp
    return float(np.clip(median_angle, -max_angle, max_angle))


def deskew_image(
    image: np.ndarray,
    max_angle: float = 12.0,
    min_angle_to_correct: float = 0.8,
) -> Tuple[np.ndarray, float]:
    """
    Detect and correct mild skew.

    Returns
    -------
    corrected : np.ndarray
        Deskewed BGR image (or original if angle is negligible).
    angle : float
        Applied rotation angle in degrees.
    """
    if image is None or image.size == 0:
        raise ValueError("Empty image passed to deskew")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
    angle = _estimate_skew_angle(gray, max_angle=max_angle)

    if abs(angle) < min_angle_to_correct:
        return image.copy(), 0.0

    h, w = image.shape[:2]
    center = (w / 2.0, h / 2.0)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Compute new bounding box so we do not crop content
    cos = abs(M[0, 0])
    sin = abs(M[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]

    rotated = cv2.warpAffine(
        image,
        M,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated, angle
