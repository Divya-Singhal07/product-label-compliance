from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import cv2


_QR_WECHAT_DETECTOR = None


def _get_wechat_detector():
    global _QR_WECHAT_DETECTOR

    if _QR_WECHAT_DETECTOR is not None:
        return _QR_WECHAT_DETECTOR

    if not hasattr(cv2, "wechat_qrcode_WeChatQRCode"):
        return None

    try:
        _QR_WECHAT_DETECTOR = cv2.wechat_qrcode_WeChatQRCode(
            "",
            "",
            "",
            "",
        )
    except Exception:
        _QR_WECHAT_DETECTOR = None

    return _QR_WECHAT_DETECTOR


def _unique_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []

    for item in items:
        key = (
            str(item.get("type", "")).strip(),
            str(item.get("data", "")).strip(),
        )

        if not key[1] or key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


def _scan_wechat_qr(image) -> List[Dict[str, Any]]:
    found = []

    detector = _get_wechat_detector()

    if detector is None:
        return found

    try:
        values, points = detector.detectAndDecode(image)

        if values:
            for index, value in enumerate(values):
                value = str(value or "").strip()

                if not value:
                    continue

                polygon = None

                if points is not None and len(points) > index:
                    polygon = points[index].tolist()

                found.append(
                    {
                        "data": value,
                        "type": "QR",
                        "polygon": polygon,
                    }
                )
    except Exception:
        pass

    return found


def _scan_opencv_qr(image) -> List[Dict[str, Any]]:
    found = []
    detector = cv2.QRCodeDetector()

    try:
        value, points, _ = detector.detectAndDecode(image)

        if value:
            found.append(
                {
                    "data": value.strip(),
                    "type": "QR",
                    "polygon": (
                        points.tolist()
                        if points is not None
                        else None
                    ),
                }
            )
    except Exception:
        pass

    return found


def _scan_barcode(image) -> List[Dict[str, Any]]:
    found = []

    if not hasattr(cv2, "barcode"):
        return found

    try:
        detector = cv2.barcode.BarcodeDetector()

        # OpenCV returns:
        # decoded_info, points, straight_code
        decoded_info, points, _ = detector.detectAndDecode(image)

        if not decoded_info:
            return found

        values = (
            list(decoded_info)
            if isinstance(decoded_info, (list, tuple))
            else [decoded_info]
        )

        for index, value in enumerate(values):
            value = str(value or "").strip()

            if not value:
                continue

            polygon = None

            if points is not None:
                try:
                    if len(points) > index:
                        polygon = points[index].tolist()
                except Exception:
                    polygon = None

            found.append(
                {
                    "data": value,
                    "type": "BARCODE",
                    "polygon": polygon,
                }
            )

    except Exception:
        pass

    return found


def _scan_image(image) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fast code scan.

    Pass 1: original image.
    Pass 2: grayscale.
    Pass 3: CLAHE.

    Stops processing variants once both QR/barcode detection has
    produced useful results.
    """

    qr_codes = []
    barcodes = []

    # ---------------------------------------------------------
    # PASS 1: ORIGINAL
    # ---------------------------------------------------------

    qr_codes.extend(_scan_wechat_qr(image))
    qr_codes.extend(_scan_opencv_qr(image))
    barcodes.extend(_scan_barcode(image))

    qr_codes = _unique_items(qr_codes)
    barcodes = _unique_items(barcodes)

    if qr_codes or barcodes:
        return {
            "qr_codes": qr_codes,
            "barcodes": barcodes,
        }

    # ---------------------------------------------------------
    # PASS 2: GRAYSCALE
    # ---------------------------------------------------------

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    qr_codes.extend(_scan_wechat_qr(gray))
    qr_codes.extend(_scan_opencv_qr(gray))
    barcodes.extend(_scan_barcode(gray))

    qr_codes = _unique_items(qr_codes)
    barcodes = _unique_items(barcodes)

    if qr_codes or barcodes:
        return {
            "qr_codes": qr_codes,
            "barcodes": barcodes,
        }

    # ---------------------------------------------------------
    # PASS 3: CLAHE
    # ---------------------------------------------------------

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    enhanced = clahe.apply(gray)

    qr_codes.extend(_scan_wechat_qr(enhanced))
    qr_codes.extend(_scan_opencv_qr(enhanced))
    barcodes.extend(_scan_barcode(enhanced))

    return {
        "qr_codes": _unique_items(qr_codes),
        "barcodes": _unique_items(barcodes),
    }


def scan_codes(image_path: str | Path) -> Dict[str, Any]:
    """
    Detect and decode QR codes and barcodes from a product image.

    Designed for the live backend path:
    - uses the original image first
    - stops early when a code is found
    - reuses the WeChat QR detector
    - avoids expensive multi-scale processing
    """

    path = str(image_path)
    image = cv2.imread(path)

    if image is None:
        raise FileNotFoundError(
            f"Could not read image: {path}"
        )

    scanned = _scan_image(image)

    return {
        "image": path,
        "qr_codes": scanned["qr_codes"],
        "barcodes": scanned["barcodes"],
        "total_codes": (
            len(scanned["qr_codes"])
            + len(scanned["barcodes"])
        ),
    }
