"""
Quick test script for the Rule Engine.
Run from the parent directory:
    python -m rule_engine.test_engine
"""

from rule_engine import RuleEngine, ExtractedFields
from rule_engine.examples.sample_inputs import (
    COMPLIANT_GENERAL,
    NON_COMPLIANT_MRP,
    FOOD_SAMPLE,
    IMPORTED_ELECTRONIC,
    ECOMMERCE_SAMPLE,
)


def print_result(title: str, result):
    print("\n" + "=" * 70)
    print(f"TEST: {title}")
    print("=" * 70)
    print(f"Product Type : {result.product_type}")
    print(f"Compliant    : {result.is_compliant}")
    print(f"Score        : {result.score:.1f}/100")
    print(f"Summary      : {result.summary}")
    print(f"Needs Review : {result.needs_manual_review}")
    if result.missing_fields:
        print(f"Missing      : {result.missing_fields}")
    if result.violations:
        print("\nViolations:")
        for v in result.violations:
            print(f"  [{v.severity.value.upper():6}] {v.rule_id}: {v.message}")
            if v.suggestion:
                print(f"           → {v.suggestion}")
    print()


def main():
    engine = RuleEngine()
    print("Available product types:", engine.get_available_product_types())

    # Test 1
    data = ExtractedFields(**COMPLIANT_GENERAL)
    result = engine.validate(data)
    print_result("Compliant General Package", result)

    # Test 2
    data = ExtractedFields(**NON_COMPLIANT_MRP)
    result = engine.validate(data)
    print_result("Non-Compliant (MRP + Font + Email)", result)

    # Test 3
    data = ExtractedFields(**FOOD_SAMPLE)
    result = engine.validate(data)
    print_result("Food Product", result)

    # Test 4
    data = ExtractedFields(**IMPORTED_ELECTRONIC)
    result = engine.validate(data)
    print_result("Imported Electronic", result)

    # Test 5
    data = ExtractedFields(**ECOMMERCE_SAMPLE)
    result = engine.validate(data)
    print_result("E-commerce Listing", result)


if __name__ == "__main__":
    main()