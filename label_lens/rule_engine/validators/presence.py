from typing import List

from ..models import ExtractedFields, Violation, Severity


# Legal references for mandatory packaged-commodity declarations.
# References are based on Rule 6(1) of the Legal Metrology
# (Packaged Commodities) Rules, 2011.

LEGAL_METADATA = {
    "manufacturer": {
        "legal_reference": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(a)",
        "explanation": (
            "The package must declare the name and address of the "
            "manufacturer and, where applicable, the packer or importer."
        ),
    },
    "generic_name": {
        "legal_reference": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(b)",
        "explanation": (
            "The package must state the common or generic name of the commodity "
            "so that the nature of the product is clearly identifiable."
        ),
    },
    "net_quantity": {
        "legal_reference": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(c)",
        "explanation": (
            "The package must declare the net quantity of the commodity "
            "in the prescribed unit of weight, measure or number."
        ),
    },
    "mrp": {
        "legal_reference": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(e)",
        "explanation": (
            "The package must declare the maximum retail price in the "
            "prescribed manner, including applicable tax requirements."
        ),
    },
    "consumer_care": {
        "legal_reference": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(f)",
        "explanation": (
            "The package must provide the prescribed details for consumers "
            "to contact the manufacturer, packer or importer regarding complaints."
        ),
    },
    "country_of_origin": {
        "legal_reference": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(aa)",
        "explanation": (
            "For imported products, the package must declare the country "
            "of origin, manufacture or assembly."
        ),
    },
}


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
    required = {}

    for field, conf in BASE_MANDATORY.items():
        metadata = LEGAL_METADATA.get(field, {})
        required[field] = {
            **conf,
            **metadata,
        }

    # ---------------------------------------------------------
    # 2. Apply product/category-specific mandatory rules
    # ---------------------------------------------------------
    if product_rules and "mandatory" in product_rules:
        for field, conf in product_rules["mandatory"].items():
            metadata = LEGAL_METADATA.get(field, {})
            required[field] = {
                "severity": Severity(
                    conf.get("severity", "high")
                ),
                "label": conf.get("label", field),
                **metadata,
                **{
                    key: conf[key]
                    for key in ("legal_reference", "explanation")
                    if key in conf
                },
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
                        legal_reference=conf.get("legal_reference"),
                        explanation=conf.get("explanation"),
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
                        legal_reference=conf.get("legal_reference"),
                        explanation=conf.get("explanation"),
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
                    legal_reference=conf.get("legal_reference"),
                    explanation=conf.get("explanation"),
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
                    legal_reference=conf.get("legal_reference"),
                    explanation=conf.get("explanation"),
                )
            )

    return violations
