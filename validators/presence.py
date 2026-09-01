from typing import List
from ..models import ExtractedFields, Violation, Severity


# Base mandatory fields for most retail packages
BASE_MANDATORY = {
    "manufacturer": {"severity": Severity.HIGH, "label": "Name & Address of Manufacturer/Packer/Importer"},
    "generic_name": {"severity": Severity.HIGH, "label": "Common / Generic Name of Commodity"},
    "net_quantity": {"severity": Severity.HIGH, "label": "Net Quantity"},
    "mrp": {"severity": Severity.HIGH, "label": "Maximum Retail Price (MRP)"},
    "consumer_care": {"severity": Severity.HIGH, "label": "Consumer Care Details"},
}

# Extra fields that become mandatory under conditions
CONDITIONAL_FIELDS = {
    "country_of_origin": {
        "when": lambda d: d.is_imported,
        "severity": Severity.HIGH,
        "label": "Country of Origin",
    },
    "unit_sale_price": {
        "when": lambda d: not (d.is_multi_piece or d.is_combination or d.is_ecommerce),
        "severity": Severity.MEDIUM,
        "label": "Unit Sale Price",
    },
    "mfg_date": {
        "when": lambda d: not (d.is_food or d.is_cosmetic),
        "severity": Severity.MEDIUM,
        "label": "Month & Year of Manufacture/Packing/Import",
    },
    "best_before": {
        "when": lambda d: d.has_shelf_life or d.is_food,
        "severity": Severity.MEDIUM,
        "label": "Best Before / Use By Date",
    },
}


def check_mandatory_fields(data: ExtractedFields, product_rules: dict = None) -> List[Violation]:
    """
    Check presence of mandatory fields.
    product_rules can override / extend the base list for specific product types.
    """
    violations = []
    missing = []

    # Start with base
    required = dict(BASE_MANDATORY)

    # Apply product-type specific overrides if provided
    if product_rules and "mandatory" in product_rules:
        for field, conf in product_rules["mandatory"].items():
            required[field] = {
                "severity": Severity(conf.get("severity", "high")),
                "label": conf.get("label", field),
            }

    # Remove fields that are exempted for this product type
    if product_rules and "exempted" in product_rules:
        for field in product_rules["exempted"]:
            required.pop(field, None)

    # Check base + overridden required fields
    for field, conf in required.items():
        value = getattr(data, field, None)
        if not value or (isinstance(value, str) and not value.strip()):
            violations.append(
                Violation(
                    rule_id=f"PRESENCE_{field.upper()}",
                    field=field,
                    message=f"Missing mandatory declaration: {conf['label']}",
                    severity=conf["severity"],
                    suggestion=f"Ensure '{conf['label']}' is clearly printed on the principal display panel.",
                )
            )
            missing.append(field)

    # Conditional fields
    for field, conf in CONDITIONAL_FIELDS.items():
        if conf["when"](data):
            # Check if this field is exempted for the product type
            if product_rules and field in product_rules.get("exempted", []):
                continue
            value = getattr(data, field, None)
            if not value or (isinstance(value, str) and not value.strip()):
                violations.append(
                    Violation(
                        rule_id=f"PRESENCE_{field.upper()}",
                        field=field,
                        message=f"Missing required declaration: {conf['label']}",
                        severity=conf["severity"],
                        suggestion=f"This field is mandatory for the given product type / condition.",
                    )
                )
                missing.append(field)

    return violations