from typing import List
from ..models import ExtractedFields, Violation, Severity
from ..utils import (
    normalize_text,
    contains_any,
    has_inclusive_of_taxes,
    is_valid_email,
    is_valid_phone,
    parse_quantity_unit,
    extract_number,
)


def check_mrp_format(data: ExtractedFields) -> List[Violation]:
    violations = []
    if not data.mrp:
        return violations

    mrp = data.mrp
    mrp_norm = normalize_text(mrp)

    # 1. Must indicate inclusive of all taxes
    if not has_inclusive_of_taxes(mrp):
        violations.append(
            Violation(
                rule_id="MRP_001",
                field="mrp",
                message="MRP does not clearly state that it is inclusive of all taxes",
                severity=Severity.HIGH,
                suggestion="Use format: 'MRP Rs. XX.XX (Inclusive of all taxes)' or 'MRP ₹XX.XX incl. of all taxes'",
                detected_value=mrp,
            )
        )

    # 2. Should contain currency indicator
    if not contains_any(mrp, ["rs", "₹", "inr", "rupee"]):
        violations.append(
            Violation(
                rule_id="MRP_002",
                field="mrp",
                message="MRP does not contain currency indicator (Rs. / ₹)",
                severity=Severity.MEDIUM,
                suggestion="Prefix price with Rs. or ₹",
                detected_value=mrp,
            )
        )

    # 3. Should contain a numeric price
    if extract_number(mrp) is None:
        violations.append(
            Violation(
                rule_id="MRP_003",
                field="mrp",
                message="Could not detect a valid numeric price in MRP declaration",
                severity=Severity.HIGH,
                detected_value=mrp,
            )
        )

    return violations


def check_quantity_format(data: ExtractedFields) -> List[Violation]:
    violations = []
    if not data.net_quantity:
        return violations

    value, unit = parse_quantity_unit(data.net_quantity)

    if value is None or unit is None:
        violations.append(
            Violation(
                rule_id="QTY_001",
                field="net_quantity",
                message="Net quantity is not in standard format (value + unit)",
                severity=Severity.HIGH,
                suggestion="Use standard units: g, kg, ml, L, m, cm, nos etc. Example: '200 g' or '500 ml'",
                detected_value=data.net_quantity,
            )
        )
    else:
        # Basic sanity
        if value <= 0:
            violations.append(
                Violation(
                    rule_id="QTY_002",
                    field="net_quantity",
                    message="Net quantity value must be positive",
                    severity=Severity.HIGH,
                    detected_value=data.net_quantity,
                )
            )

    return violations


def check_date_format(data: ExtractedFields) -> List[Violation]:
    violations = []
    date_fields = [
        ("mfg_date", "Manufacture / Packing / Import date"),
        ("best_before", "Best Before date"),
        ("use_by", "Use By date"),
    ]

    for field, label in date_fields:
        value = getattr(data, field, None)
        if not value:
            continue

        # Very basic check – presence of month/year like patterns
        import re
        if not re.search(r"(\d{1,2}[-/ ]?[A-Za-z]{3,9}[-/ ]?\d{2,4})|([A-Za-z]{3,9}[-/ ]?\d{2,4})|(\d{1,2}[-/]\d{2,4})", value):
            violations.append(
                Violation(
                    rule_id=f"DATE_{field.upper()}",
                    field=field,
                    message=f"{label} does not appear to be in a readable date format",
                    severity=Severity.MEDIUM,
                    suggestion="Preferred formats: 'Jan 2025', '01/2025', 'January 2025'",
                    detected_value=value,
                )
            )

    return violations


def check_consumer_care(data: ExtractedFields) -> List[Violation]:
    violations = []
    if not data.consumer_care:
        return violations

    care = data.consumer_care
    has_email = is_valid_email(care)
    has_phone = is_valid_phone(care)

    if not has_email:
        violations.append(
            Violation(
                rule_id="CARE_001",
                field="consumer_care",
                message="Consumer care details must include a valid email address",
                severity=Severity.HIGH,
                suggestion="Email is mandatory under the Rules",
                detected_value=care,
            )
        )

    if not has_phone:
        violations.append(
            Violation(
                rule_id="CARE_002",
                field="consumer_care",
                message="Consumer care details should include a contact phone / toll-free number",
                severity=Severity.MEDIUM,
                detected_value=care,
            )
        )

    return violations


def check_unit_sale_price(data: ExtractedFields) -> List[Violation]:
    violations = []

    # Skip if exempted
    if data.is_multi_piece or data.is_combination or data.is_ecommerce:
        return violations

    if not data.unit_sale_price:
        # Presence is already handled in presence checker
        return violations

    usp = normalize_text(data.unit_sale_price)

    # Should contain "per" and a unit
    valid_units = ["per g", "per kg", "per ml", "per l", "per cm", "per m", "per nos", "per number", "per unit", "/g", "/kg", "/ml", "/l"]
    if not any(u in usp for u in valid_units):
        violations.append(
            Violation(
                rule_id="USP_001",
                field="unit_sale_price",
                message="Unit Sale Price does not follow the required format (e.g. Rs. X.XX per g / per kg / per ml)",
                severity=Severity.MEDIUM,
                suggestion="Declare as 'Rs. 0.25 per g' or '₹12.50 per kg' etc. Round to 2 decimal places.",
                detected_value=data.unit_sale_price,
            )
        )

    return violations


def check_country_of_origin(data: ExtractedFields) -> List[Violation]:
    violations = []
    if not data.is_imported:
        return violations

    if not data.country_of_origin or not data.country_of_origin.strip():
        violations.append(
            Violation(
                rule_id="COO_001",
                field="country_of_origin",
                message="Country of Origin is mandatory for imported products",
                severity=Severity.HIGH,
                suggestion="Declare as 'Country of Origin: XXX' or 'Made in XXX'",
            )
        )
    return violations


def check_manufacturer(data: ExtractedFields) -> List[Violation]:
    violations = []
    mfr = data.manufacturer or ""
    if len(mfr.strip()) < 10:
        violations.append(
            Violation(
                rule_id="MFR_001",
                field="manufacturer",
                message="Manufacturer / Packer / Importer name & address appears incomplete",
                severity=Severity.MEDIUM,
                suggestion="Must include name and complete address",
                detected_value=mfr,
            )
        )
    return violations