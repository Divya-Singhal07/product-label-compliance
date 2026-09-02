#!/usr/bin/env python3
"""
Full pipeline:
OpenCV Preprocessing → OCR → Field Extraction → Auto Product ID
→ Save structured JSON for Rule Engine
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from label_lens.preprocessing.pipeline import PackageImagePreprocessor
from label_lens.ocr.ocr_pipeline import OCRProcessor


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Full pipeline: Preprocessing + OCR + Auto Product ID"
    )

    parser.add_argument(
        "--input",
        "-i",
        nargs="+",
        required=True,
        help="front [back] [side] image paths",
    )

    parser.add_argument(
        "--views",
        nargs="+",
        default=None,
        help="Optional view names e.g. front back side",
    )

    parser.add_argument(
        "--product-id",
        default=None,
        help="Optional override of auto-generated product_id",
    )

    args = parser.parse_args()

    setup_logging()

    # ---------------------------------------------------------
    # Validate input images
    # ---------------------------------------------------------
    paths = [Path(p) for p in args.input]

    for p in paths:
        if not p.exists():
            print(
                f"❌ Error: file not found → {p}",
                file=sys.stderr,
            )
            return 1

    # ---------------------------------------------------------
    # 1. OpenCV Preprocessing
    # ---------------------------------------------------------
    print("\n🚀 Starting preprocessing...")

    pre = PackageImagePreprocessor(
        debug=True,
        max_workers=3,
    )

    batch = pre.process_batch(
        paths,
        view_names=args.views,
        product_id=args.product_id,
    )

    print("✅ Preprocessing completed.")

    # ---------------------------------------------------------
    # 2. OCR + Field Extraction + Auto Product ID
    # ---------------------------------------------------------
    print("\n🔎 Starting OCR + Field Extraction...")

    ocr = OCRProcessor()

    front_name = (
        args.views[0]
        if args.views
        else "front"
    )

    final = ocr.process_product(
        batch,
        front_view_name=front_name,
    )

    # ---------------------------------------------------------
    # 3. Display Auto Product ID
    # ---------------------------------------------------------
    print("\n========== AUTO PRODUCT ID ==========")
    print(
        f"Product ID     : {final['product_id']}"
    )
    print(
        f"Product folder : {final['product_folder']}"
    )
    print("=====================================")

    # ---------------------------------------------------------
    # 4. Display Merged Fields
    # ---------------------------------------------------------
    print(
        "\n========== MERGED FIELDS "
        "(Front + Back + Side) =========="
    )

    for k, v in final["merged_fields"].items():
        print(f"{k:25}: {v}")

    # ---------------------------------------------------------
    # 4B. Display Raw OCR Lines
    # ---------------------------------------------------------
    print("\n========== RAW OCR LINES ==========")

    views = final.get("views", {})

    if not views:
        print("⚠️ No per-view OCR data found.")

    for view_name, view_data in views.items():

        print(f"\n--- {view_name.upper()} ---")

        print(
            f"Best candidate: "
            f"{view_data.get('best_candidate')}"
        )

        ocr_lines = view_data.get(
            "ocr_lines",
            [],
        )

        if not ocr_lines:
            print("⚠️ No OCR lines detected.")
            continue

        for line in ocr_lines:

            if isinstance(line, dict):

                text = line.get(
                    "text",
                    line.get(
                        "rec_text",
                        str(line),
                    ),
                )

                score = line.get(
                    "score",
                    line.get(
                        "confidence",
                        None,
                    ),
                )

                if score is not None:
                    print(
                        f"{text} "
                        f"[confidence: {score}]"
                    )
                else:
                    print(text)

            else:
                print(line)

    print("\n====================================\n")

    # ---------------------------------------------------------
    # 5. Save structured JSON for Rule Engine
    # ---------------------------------------------------------

    product_folder = Path(
        final["product_folder"]
    )

    product_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = (
        product_folder
        / "structured_result.json"
    )

    # Save ONLY merged fields because
    # rule_engine_mapper.py expects this structure.
    with open(
        json_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            final["merged_fields"],
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ---------------------------------------------------------
    # 6. Confirm JSON was created
    # ---------------------------------------------------------
    print(
        "========== RULE ENGINE HANDOFF =========="
    )

    print("✅ Structured JSON saved:")
    print(f"   {json_path}")

    print(
        "=========================================="
    )

    print(
        "\n✅ Structured result is ready "
        "for Rule Engine."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
