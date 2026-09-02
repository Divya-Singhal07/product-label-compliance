from typing import List

from ..models import ExtractedFields, Violation, Severity


# Base mandatory fields for most retail packages
BASE_MANDATORY = {
    "manufacturer": {
        "severity": Severity.HIGH,
        "label": "Name & Address of Manufacturer/Packer/Importer",
    },
    "generic_name": {
        "severity": Severity.HIGH,
        "label": "Common / Generic Name of Commodity",
    },
    "net_quantity": {
        "severity": Severity.HIGH,
        "label": "Net Quantity",
    },
    "mrp": {
        "severity": Severity.HIGH,
        "label": "Maximum Retail Price (MRP)",
    },
    "consumer_care": {
        "severity": Severity.HIGH,
        "label": "Consumer Care Details",
    },
}


# Only truly universal conditional requirements belong here.
# Category/product-specific requirements should come from YAML.
CONDITIONAL_FIELDS = {
    "country_of_origin": {
        "when": lambda d: d.is_imported,
        "severity": Severity.HIGH,
        "label": "Country of Origin",
    },
}


def check_mandatory_fields(
    data: ExtractedFields,
    product_rules: dict = None
) -> List[Violation]:
    """
    Check whether all mandatory declarations are present.

    Base mandatory fields are always checked.

    Product/category YAML rules can:
    - add mandatory fields
    - override severity/labels
    - exempt fields

    Conditional fields are checked only when their condition is satisfied.
    """

    violations = []

    # ---------------------------------------------------------
    # 1. Start with base mandatory fields
    # ---------------------------------------------------------
    required = dict(BASE_MANDATORY)

    # ---------------------------------------------------------
    # 2. Apply product/category-specific mandatory rules
    # ---------------------------------------------------------
    if product_rules and "mandatory" in product_rules:
        for field, conf in product_rules["mandatory"].items():
            required[field] = {
                "severity": Severity(
                    conf.get("severity", "high")
                ),
                "label": conf.get("label", field),
            }

    # ---------------------------------------------------------
    # 3. Remove exempted fields
    # ---------------------------------------------------------
    if product_rules and "exempted" in product_rules:
        for field in product_rules["exempted"]:
            required.pop(field, None)

    # ---------------------------------------------------------
    # 4. Check mandatory fields
    # ---------------------------------------------------------
    for field, conf in required.items():
        value = getattr(data, field, None)

        # MRP declaration may be detected even when the numeric
        # value could not be extracted by OCR.
        if field == "mrp" and (
            value is None
            or (isinstance(value, str) and not value.strip())
        ):
            if getattr(data, "mrp_declaration_detected", False):
                violations.append(
                    Violation(
                        rule_id="MRP_VALUE_VERIFICATION",
                        field="mrp",
                        message=(
                            "MRP declaration detected, but the numeric "
                            "MRP value could not be extracted."
                        ),
                        severity=Severity.MEDIUM,
                        suggestion=(
                            "Manually verify the numeric MRP value on "
                            "the product label."
                        ),
                    )
                )
            else:
                violations.append(
                    Violation(
                        rule_id=f"PRESENCE_{field.upper()}",
                        field=field,
                        message=(
                            f"Missing mandatory declaration: "
                            f"{conf['label']}"
                        ),
                        severity=conf["severity"],
                        suggestion=(
                            f"Ensure '{conf['label']}' is clearly printed "
                            f"on the product label."
                        ),
                    )
                )

        # Normal mandatory-field validation.
        elif value is None or (
            isinstance(value, str) and not value.strip()
        ):
            violations.append(
                Violation(
                    rule_id=f"PRESENCE_{field.upper()}",
                    field=field,
                    message=(
                        f"Missing mandatory declaration: "
                        f"{conf['label']}"
                    ),
                    severity=conf["severity"],
                    suggestion=(
                        f"Ensure '{conf['label']}' is clearly printed "
                        f"on the product label."
                    ),
                )
            )

    # ---------------------------------------------------------
    # 5. Check conditional fields
    # ---------------------------------------------------------
    for field, conf in CONDITIONAL_FIELDS.items():

        # Condition is not applicable
        if not conf["when"](data):
            continue

        # Product/category rule can exempt this field
        if (
            product_rules
            and field in product_rules.get("exempted", [])
        ):
            continue

        value = getattr(data, field, None)

        # Field is required but missing
        if value is None or (
            isinstance(value, str) and not value.strip()
        ):
            violations.append(
                Violation(
                    rule_id=f"PRESENCE_{field.upper()}",
                    field=field,
                    message=(
                        f"Missing required declaration: "
                        f"{conf['label']}"
                    ),
                    severity=conf["severity"],
                    suggestion=(
                        "This field is mandatory for the "
                        "given product type or condition."
                    ),
                )
            )

    return violations
