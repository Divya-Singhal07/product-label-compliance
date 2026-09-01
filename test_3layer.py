"""
Test script for the upgraded 3-Layer Rule Engine
"""

from rule_engine import RuleEngine, ExtractedFields


def print_result(title, result):
    print("\n" + "=" * 70)
    print(f"TEST: {title}")
    print("=" * 70)
    print(f"Category (Layer 2) : {result.product_type}")
    print(f"Product  (Layer 3) : {result.specific_product}")
    print(f"Layers Applied     : {result.layers_applied}")
    print(f"Compliant          : {result.is_compliant}")
    print(f"Score              : {result.score:.1f}/100")
    print(f"Summary            : {result.summary}")
    if result.violations:
        print("\nViolations:")
        for v in result.violations:
            layer = f"[{v.layer}]" if v.layer else ""
            print(f"  {layer:12} [{v.severity.value.upper():6}] {v.rule_id}: {v.message}")
    print()


def main():
    engine = RuleEngine()
    print("Available Categories (Layer 2):", engine.get_available_categories())
    print("Available Products   (Layer 3):", engine.get_available_products())

    # Test 1: Normal general package
    data = ExtractedFields(
        manufacturer="ABC Foods, Pune",
        generic_name="Tomato Ketchup",
        net_quantity="500 g",
        mrp="MRP Rs. 95 (Inclusive of all taxes)",
        consumer_care="care@abc.com, 1800-123456",
        product_type="general",
    )
    print_result("General Package (only Layer 1 + 2)", engine.validate(data))

    # Test 2: Toothpaste (Layer 3 activated)
    data = ExtractedFields(
        manufacturer="Colgate Palmolive, Mumbai",
        generic_name="Toothpaste",
        net_quantity="150 g",
        mrp="MRP Rs. 99 (Inclusive of all taxes)",
        consumer_care="care@colgate.com",
        product_type="cosmetics",
        specific_product="toothpaste",
        is_cosmetic=True,
    )
    print_result("Toothpaste (Layer 1 + 2 + 3)", engine.validate(data))

    # Test 3: Packaged Drinking Water
    data = ExtractedFields(
        manufacturer="Bisleri International, Mumbai",
        generic_name="Packaged Drinking Water",
        net_quantity="1 L",
        mrp="MRP Rs. 20 (Inclusive of all taxes)",
        consumer_care="care@bisleri.com, 1800-111-222",
        best_before="Dec 2026",
        product_type="food",
        specific_product="packaged_drinking_water",
        is_food=True,
        has_shelf_life=True,
    )
    print_result("Packaged Drinking Water (Layer 1 + 2 + 3)", engine.validate(data))

    # Test 4: Mobile Phone (Imported)
    data = ExtractedFields(
        manufacturer="Imported by Foxconn India, Chennai",
        generic_name="Smartphone Model X1",
        net_quantity="1 Nos",
        mrp="MRP Rs. 14999 (Inclusive of all taxes)",
        consumer_care="support@phone.com",
        country_of_origin="China",
        product_type="electronic",
        specific_product="mobile_phone",
        is_imported=True,
        is_electronic=True,
    )
    print_result("Mobile Phone - Imported (Layer 1 + 2 + 3)", engine.validate(data))


if __name__ == "__main__":
    main()