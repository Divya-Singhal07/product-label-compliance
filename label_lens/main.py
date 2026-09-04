#!/usr/bin/env python3
"""
Command-line entry point for the packaging image preprocessing pipeline.

Usage
-----
python main.py --input path/to/product.jpg
python main.py --input path/to/product.jpg --no-debug
python main.py --input path/to/product.jpg --enable-perspective
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from label_lens.preprocessing.pipeline import PackageImagePreprocessor


def setup_logging(verbose: bool = True) -> None:
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Adaptive OpenCV preprocessing for product packaging images (before PaddleOCR)"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        type=str,
        help="Path to input product package image (.jpg/.jpeg/.png)",
    )
    parser.add_argument(
        "--debug-root",
        default="debug_outputs",
        help="Root folder for intermediate debug images (default: debug_outputs)",
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Disable saving intermediate images",
    )
    parser.add_argument(
        "--enable-perspective",
        action="store_true",
        help="Attempt perspective correction (conservative, off by default)",
    )
    parser.add_argument(
        "--min-side",
        type=int,
        default=900,
        help="Minimum shorter side after normalisation (default: 900)",
    )
    parser.add_argument(
        "--max-side",
        type=int,
        default=2400,
        help="Maximum longer side after normalisation (default: 2400)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging(verbose=True)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found → {input_path}", file=sys.stderr)
        return 1

    preprocessor = PackageImagePreprocessor(
        debug=not args.no_debug,
        save_intermediate=not args.no_debug,
        debug_root=args.debug_root,
        min_side=args.min_side,
        max_side=args.max_side,
        enable_perspective=args.enable_perspective,
    )

    try:
        result = preprocessor.process(input_path)
    except Exception as exc:
        logging.exception("Preprocessing failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Pretty-print summary
    q = result["quality_metrics"]
    print("\n========== PREPROCESSING SUMMARY ==========")
    print(f"Input               : {input_path}")
    print(f"Resolution          : {q['width']} × {q['height']}")
    print(f"Brightness          : {q['brightness']}")
    print(f"Contrast            : {q['contrast']}")
    print(f"Blur score          : {q['blur_score']}")
    print(f"Noise estimate      : {q['noise_estimate']}")
    print(f"Flags               : dark={q['is_dark']}  low_contrast={q['is_low_contrast']}  "
          f"blurry={q['is_blurry']}  noisy={q['is_noisy']}")
    print(f"Rotation applied    : {result['rotation_angle']}°")
    print(f"Glare detected      : {result['glare_detected']}")
    print(f"Perspective corrected: {result['perspective_corrected']}")
    print(f"Debug folder        : {result['debug_dir']}")
    print("OCR candidate images produced:")
    for name in result["images"]:
        print(f"  • {name}")
    print("===========================================\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
