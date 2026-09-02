#!/usr/bin/env python3
"""
Full Pipeline: Latest OCR+LLM result → Rule Engine → Compliance Report
GitHub-ready version
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from label_lens.rule_engine.engine import run_compliance_check
from label_lens.rule_engine_mapper import map_to_rule_engine


def run_full_pipeline():
    print("\n🚀 Starting Rule Engine on latest OCR + LLM result...")

    debug_dir = Path("debug_outputs")
    if not debug_dir.exists():
        print("❌ debug_outputs folder not found. Please run main_ocr.py first.")
        return

    # Find the latest product folder
    latest_folders = sorted(
        [p for p in debug_dir.glob("product_*") if p.is_dir()],
        key=os.path.getmtime,
        reverse=True
    )

    if not latest_folders:
        print("❌ No recent OCR results found. Please run main_ocr.py first.")
        return

    latest = latest_folders[0]
    print(f"📂 Using latest result from: {latest.name}")

    # Find any JSON file inside it
    json_files = list(latest.rglob("*.json"))
    if not json_files:
        print("❌ No JSON result file found inside the latest folder.")
        return

    result_file = json_files[0]
    print(f"📄 Loading: {result_file.name}")

    with open(result_file, "r", encoding="utf-8") as f:
        llm_fields = json.load(f)

    print("\n✅ LLM Fields:")
    print(json.dumps(llm_fields, indent=2, ensure_ascii=False))

    # Map to Rule Engine format
    data_dict = map_to_rule_engine(llm_fields)

    # Run Rule Engine
    print("\n⚙️  Running Rule Engine...")
    result = run_compliance_check(data_dict)

    # Pretty print
    print("\n" + "="*65)
    print("📋 FINAL COMPLIANCE REPORT")
    print("="*65)
    print(f"Status           : {'✅ COMPLIANT' if result['is_compliant'] else '❌ NON-COMPLIANT'}")
    print(f"Score            : {result['score']:.1f} / 100")
    print(f"Product Type     : {result['product_type']}")
    print(f"Specific Product : {result.get('specific_product')}")
    print(f"Summary          : {result['summary']}")
    print(f"Layers Applied   : {', '.join(result.get('layers_applied', []))}")

    if result.get("violations"):
        print("\n🚨 Violations:")
        for v in result["violations"]:
            sev = v.get("severity", "unknown").upper()
            print(f"  • [{sev:6}] {v.get('field')}: {v.get('message')}")
            if v.get("suggestion"):
                print(f"           → Suggestion: {v['suggestion']}")

    if result.get("needs_manual_review"):
        print("\n⚠️  Needs Manual Review (low OCR confidence)")

    print("="*65)

    # Save result
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    out_path = output_dir / f"{latest.name}_compliance.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Full result saved to: {out_path}")
    return result


if __name__ == "__main__":
    run_full_pipeline()
