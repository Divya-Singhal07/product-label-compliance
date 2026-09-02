"""Main adaptive preprocessing pipeline – multi-image support with clean product folder."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import cv2
import numpy as np

from label_lens.utils.image_utils import ensure_dir, load_image, resize_keep_aspect, save_image
from .enhancement import (
    correct_illumination,
    denoise_image,
    enhance_contrast,
    mild_deblur,
    sharpen_image,
)
from .glare_reduction import detect_glare, reduce_glare
from .image_quality import analyze_image_quality
from .orientation import deskew_image
from .perspective import correct_perspective

logger = logging.getLogger(__name__)


class PackageImagePreprocessor:
    def __init__(
        self,
        debug: bool = True,
        save_intermediate: bool = True,
        debug_root: Union[str, Path] = "debug_outputs",
        min_side: int = 900,
        max_side: int = 2400,
        enable_deskew: bool = True,
        max_skew_angle: float = 12.0,
        enable_perspective: bool = False,
        clahe_clip_limit: float = 2.5,
        enable_glare_reduction: bool = True,
        glare_v_thresh: int = 242,
        denoise_strength: int = 6,
        sharpen_amount: float = 0.65,
        max_workers: int = 3,
    ) -> None:
        self.debug = debug
        self.save_intermediate = save_intermediate
        self.debug_root = Path(debug_root)
        self.min_side = min_side
        self.max_side = max_side
        self.enable_deskew = enable_deskew
        self.max_skew_angle = max_skew_angle
        self.enable_perspective = enable_perspective
        self.clahe_clip_limit = clahe_clip_limit
        self.enable_glare_reduction = enable_glare_reduction
        self.glare_v_thresh = glare_v_thresh
        self.denoise_strength = denoise_strength
        self.sharpen_amount = sharpen_amount
        self.max_workers = max_workers
        self._product_dir: Optional[Path] = None

    def process(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """Single image (creates its own product folder)."""
        return self.process_batch([image_path], view_names=["front"])["results"]["front"]

    def process_batch(
        self,
        image_paths: List[Union[str, Path]],
        view_names: Optional[List[str]] = None,
        product_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        paths = [Path(p) for p in image_paths]

        if view_names is None:
            default_names = ["front", "back", "side"]
            view_names = default_names[:len(paths)]
        if len(view_names) != len(paths):
            raise ValueError("Number of view_names must match number of images")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"product_{product_id}_{ts}" if product_id else f"product_{ts}"
        self._product_dir = ensure_dir(self.debug_root / folder_name)
        logger.info("Product folder created → %s", self._product_dir)

        results = {}
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(paths))) as executor:
            future_to_view = {
                executor.submit(self._process_one, path, name): name
                for path, name in zip(paths, view_names)
            }
            for future in as_completed(future_to_view):
                view = future_to_view[future]
                try:
                    results[view] = future.result()
                except Exception as exc:
                    logger.error("Failed on %s: %s", view, exc)
                    results[view] = {"error": str(exc)}

        return {
            "product_folder": str(self._product_dir),
            "product_id": product_id or ts,
            "num_images": len(paths),
            "views": view_names,
            "results": results,
        }

    def _process_one(self, image_path: Path, view_name: str) -> Dict[str, Any]:
        view_dir = ensure_dir(self._product_dir / view_name) if self._product_dir else None

        image = self._load_and_validate(image_path)
        self._save_debug(image, "01_original", view_dir)

        quality = analyze_image_quality(image)
        self._log_quality(quality, view_name)

        perspective_corrected = False
        if self.enable_perspective:
            image, perspective_corrected = correct_perspective(image)
            if perspective_corrected:
                self._save_debug(image, "02_perspective", view_dir)

        rotation_angle = 0.0
        if self.enable_deskew:
            image, rotation_angle = deskew_image(image, max_angle=self.max_skew_angle)
            if abs(rotation_angle) > 0.1:
                self._save_debug(image, "03_deskewed", view_dir)

        image = self._normalize_resolution(image, quality)
        self._save_debug(image, "04_normalized", view_dir)
        quality = analyze_image_quality(image)

        glare_detected = False
        if self.enable_glare_reduction:
            mask, glare_detected = detect_glare(image, v_thresh=self.glare_v_thresh)
            if glare_detected:
                image = reduce_glare(image, mask)
                self._save_debug(mask, "05_glare_mask", view_dir)
                self._save_debug(image, "06_glare_reduced", view_dir)

        base = image.copy()

        candidate_original = base.copy()
        candidate_enhanced = enhance_contrast(base, clip_limit=self.clahe_clip_limit)
        self._save_debug(candidate_enhanced, "07_enhanced", view_dir)

        if quality["is_dark"] or quality["is_low_contrast"] or quality["brightness"] < 110:
            candidate_illum = correct_illumination(base)
            self._save_debug(candidate_illum, "08_illumination", view_dir)
        else:
            candidate_illum = base.copy()

        candidate_denoised = denoise_image(base, quality, strength=self.denoise_strength)
        if quality.get("is_noisy", False):
            self._save_debug(candidate_denoised, "09_denoised", view_dir)

        if quality["is_blurry"] or quality["blur_score"] < 300:
            candidate_sharpened = mild_deblur(candidate_enhanced)
            self._save_debug(candidate_sharpened, "10_deblurred", view_dir)
        else:
            candidate_sharpened = sharpen_image(candidate_enhanced, amount=self.sharpen_amount)
            self._save_debug(candidate_sharpened, "10_sharpened", view_dir)

        result = {
            "view": view_name,
            "source_path": str(image_path),
            "quality_metrics": quality,
            "rotation_angle": round(rotation_angle, 3),
            "glare_detected": glare_detected,
            "perspective_corrected": perspective_corrected,
            "images": {
                "original": candidate_original,
                "enhanced": candidate_enhanced,
                "illumination_corrected": candidate_illum,
                "denoised": candidate_denoised,
                "sharpened": candidate_sharpened,
            },
        }

        if view_dir is not None:
            for name, img in result["images"].items():
                save_image(view_dir / f"final_{name}.jpg", img)

        return result

    def _load_and_validate(self, path: Path) -> np.ndarray:
        img = load_image(path)
        h, w = img.shape[:2]
        if min(h, w) < 80:
            raise ValueError(f"Image too small ({w}x{h})")
        return img

    def _normalize_resolution(self, image: np.ndarray, quality: Dict[str, Any]) -> np.ndarray:
        inter = cv2.INTER_CUBIC if quality.get("is_low_res", False) else cv2.INTER_AREA
        return resize_keep_aspect(
            image,
            max_side=self.max_side,
            min_side=self.min_side if quality.get("is_low_res", False) else None,
            interpolation=inter,
        )

    def _save_debug(self, image: np.ndarray, name: str, view_dir: Optional[Path]) -> None:
        if view_dir is None:
            return
        save_image(view_dir / f"{name}.jpg", image)

    def _log_quality(self, q: Dict[str, Any], view: str) -> None:
        logger.info(
            "[%s] %dx%d | brightness=%.1f | contrast=%.1f | blur=%.1f",
            view, q["width"], q["height"], q["brightness"], q["contrast"], q["blur_score"]
        )
