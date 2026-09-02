"""Optional perspective correction for clearly rectangular labels/packages."""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def correct_perspective(
    image: np.ndarray,
    min_area_ratio: float = 0.25,
    max_area_ratio: float = 0.95,
    epsilon_factor: float = 0.02,
) -> Tuple[np.ndarray, bool]:
    """
    Attempt to find a dominant quadrilateral (package face / label) and
    apply a perspective transform.

    If no confident rectangle is found the original image is returned unchanged.
    This is intentionally conservative because many product photos are not
    clean document-like rectangles.
    """
    if image.ndim != 3:
        raise ValueError("correct_perspective expects a 3-channel BGR image")

    h, w = image.shape[:2]
    img_area = float(h * w)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    best_approx = None
    best_area = 0.0

    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon_factor * peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            ratio = area / img_area
            if min_area_ratio <= ratio <= max_area_ratio and area > best_area:
                best_area = area
                best_approx = approx

    if best_approx is None:
        return image.copy(), False

    pts = best_approx.reshape(4, 2).astype(np.float32)
    rect = _order_points(pts)

    # Destination rectangle – preserve approximate width/height
    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = max(int(widthA), int(widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = max(int(heightA), int(heightB))

    if maxWidth < 50 or maxHeight < 50:
        return image.copy(), False

    dst = np.array(
        [
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1],
        ],
        dtype=np.float32,
    )

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight), flags=cv2.INTER_CUBIC)
    return warped, True
