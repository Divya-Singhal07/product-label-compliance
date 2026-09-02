"""
Maps OCR/LLM extracted fields -> Rule Engine format.

This file acts as the compatibility layer between:
    OCR + LLM extraction
and:
    Rule Engine

The mapper keeps field names consistent and prevents incorrect
assumptions such as treating MFG date as Best Before.
"""

from typing import Dict, Any


CANONICAL_FIELDS = [
    "brand",
    "product_name",
    "generic_name",
    "net_quantity",
    "mrp",
    "mrp_inclusive_of_taxes",
    "unit_sale_price",
    "manufacturer_address",
    "packer",
    "importer",
    "consumer_care",
    "mfg_date",
    "best_before",
    "use_by",
    "country_of_origin",
    "product_type",
    "specific_product",
    "is_food",
    "is_cosmetic",
    "is_electronic",
    "is_imported",
    "has_shelf_life",
]


def _value(data: Dict[str, Any], *keys):
    """
    Return the first meaningful value among multiple possible keys.

    Supports backward compatibility with older extractor field names.
    """
    for key in keys:
        value = data.get(key)

        if value is not None and value != "":
            return value

    return None


def _to_bool(value: Any, default: bool = False) -> bool:
    """
    Safely convert common boolean representations to bool.
    """
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        value = value.strip().lower()

        if value in {"true", "yes", "1", "y"}:
            return True

        if value in {"false", "no", "0", "n"}:
            return False

    return bool(value)


def map_to_rule_engine(llm_fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert OCR/LLM extracted fields into the schema expected by RuleEngine.

    Important:
    - Does NOT invent missing declarations.
    - Does NOT treat MFG date as Best Before.
    - Preserves separate MFG / Best Before / Use By fields.
    - Uses LLM classification when available.
    - Keeps backward compatibility with older field names.
    """

    if not isinstance(llm_fields, dict):
        raise TypeError("llm_fields must be a dictionary")

    # ---------------------------------------------------------
    # Basic product information
    # ---------------------------------------------------------

    brand = _value(
        llm_fields,
        "brand",
    )

    product_name = _value(
        llm_fields,
        "product_name",
    )

    generic_name = _value(
        llm_fields,
        "generic_name",
    )

    net_quantity = _value(
        llm_fields,
        "net_quantity",
    )

    # ---------------------------------------------------------
    # Price information
    # ---------------------------------------------------------

    mrp = _value(
        llm_fields,
        "mrp",
    )

    mrp_inclusive_of_taxes = _to_bool(
        _value(
            llm_fields,
            "mrp_inclusive_of_taxes",
        ),
        default=False,
    )

    unit_sale_price = _value(
        llm_fields,
        "unit_sale_price",
    )

    # ---------------------------------------------------------
    # Manufacturer / importer / consumer information
    # ---------------------------------------------------------

    manufacturer = _value(
        llm_fields,
        "manufacturer_address",
        "manufacturer",
    )

    packer = _value(
        llm_fields,
        "packer",
    )

    importer = _value(
        llm_fields,
        "importer",
    )

    consumer_care = _value(
        llm_fields,
        "consumer_care",
    )

    country_of_origin = _value(
        llm_fields,
        "country_of_origin",
    )

    # ---------------------------------------------------------
    # Date declarations
    # ---------------------------------------------------------

    # IMPORTANT:
    # These must remain separate.
    #
    # Never do:
    # best_before = mfg_date
    #
    # because that creates a false declaration.

    mfg_date = _value(
        llm_fields,
        "mfg_date",
        "manufacturing_date",
        "mfg_or_expiry_date",   # legacy compatibility only
    )

    best_before = _value(
        llm_fields,
        "best_before",
    )

    use_by = _value(
        llm_fields,
        "use_by",
        "expiry_date",
    )

    # ---------------------------------------------------------
    # Product classification
    # ---------------------------------------------------------

    product_type = _value(
        llm_fields,
        "product_type",
    )

    specific_product = _value(
        llm_fields,
        "specific_product",
    )

    is_food = _to_bool(
        llm_fields.get("is_food"),
        default=False,
    )

    is_cosmetic = _to_bool(
        llm_fields.get("is_cosmetic"),
        default=False,
    )

    is_electronic = _to_bool(
        llm_fields.get("is_electronic"),
        default=False,
    )

    is_imported = _to_bool(
        llm_fields.get("is_imported"),
        default=False,
    )

    # ---------------------------------------------------------
    # Shelf-life detection
    # ---------------------------------------------------------

    has_shelf_life = _to_bool(
        llm_fields.get("has_shelf_life"),
        default=bool(best_before or use_by),
    )

    # If an explicit shelf-life declaration exists,
    # make sure the rule engine knows the product has shelf life.
    if best_before or use_by:
        has_shelf_life = True

    # ---------------------------------------------------------
    # Final Rule Engine object
    # ---------------------------------------------------------

    return {
        # Basic declarations
        "brand": brand,
        "product_name": product_name,
        "generic_name": generic_name,
        "net_quantity": net_quantity,

        # Price declarations
        "mrp": mrp,
        "mrp_declaration_detected": bool(
            llm_fields.get("mrp_declaration_detected", False)
        ),
        "mrp_inclusive_of_taxes": mrp_inclusive_of_taxes,
        "unit_sale_price": unit_sale_price,

        # Manufacturer / importer declarations
        "manufacturer": manufacturer,
        "manufacturer_address": manufacturer,
        "packer": packer,
        "importer": importer,
        "consumer_care": consumer_care,
        "country_of_origin": country_of_origin,

        # Date declarations
        "mfg_date": mfg_date,
        "best_before": best_before,
        "use_by": use_by,

        # Classification
        "product_type": product_type or "general",
        "specific_product": specific_product,
        "is_food": is_food,
        "is_cosmetic": is_cosmetic,
        "is_electronic": is_electronic,
        "is_imported": is_imported,
        "has_shelf_life": has_shelf_life,
    }
