"""
Rule-based field extractor.

Acts as a deterministic fallback for the LLM extractor.
Designed for Indian packaged commodity labels and Legal Metrology fields.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def _clean(text: str) -> str:
    """Normalize whitespace while preserving useful text."""
    return re.sub(r"\s+", " ", str(text)).strip()


def _empty_fields() -> Dict[str, Any]:
    """Return the same schema used by the LLM extractor."""
    return {
        "brand": None,
        "product_name": None,
        "generic_name": None,
        "net_quantity": None,
        "mrp": None,
        "mrp_inclusive_of_taxes": False,
        "unit_sale_price": None,
        "manufacturer_address": None,
        "packer": None,
        "importer": None,
        "consumer_care": None,
        "mfg_date": None,
        "best_before": None,
        "use_by": None,
        "country_of_origin": None,
        "product_type": "general",
        "specific_product": None,
        "is_food": False,
        "is_cosmetic": False,
        "is_electronic": False,
        "is_imported": False,
        "has_shelf_life": False,
    }


def _first_match(
    patterns: List[str],
    text: str,
    flags: int = re.IGNORECASE,
) -> str | None:
    """Return first captured regex group that matches."""
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            value = match.group(1)
            if value:
                return _clean(value)
    return None


def _normalize_quantity(value: str) -> str:
    """Normalize common OCR quantity formatting."""
    value = _clean(value)

    value = re.sub(
        r"(\d+(?:\.\d+)?)\s*(millilitres?|milliliters?)",
        r"\1 ml",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(
        r"(\d+(?:\.\d+)?)\s*(litres?|liters?)",
        r"\1 L",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(
        r"(\d+(?:\.\d+)?)\s*(grams?)",
        r"\1 g",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(
        r"(\d+(?:\.\d+)?)\s*(kilograms?|kgs?)",
        r"\1 kg",
        value,
        flags=re.IGNORECASE,
    )

    return value


def _extract_mrp(text: str) -> str | None:
    """
    Extract MRP from common Indian packaged-product declarations.

    Handles OCR variations such as:
        MRP 249
        M.R.P. 249
        MRP: ₹249.00
        MRP ₹ 249
        MRP Rs. 249
        MRP INR 249
        Maximum Retail Price 249

    Also tolerates OCR whitespace/punctuation errors.
    """

    if not text:
        return None

    # Normalize common OCR spacing/punctuation problems.
    normalized = re.sub(r"\s+", " ", text).strip()

    patterns = [
        # MRP followed by currency and price
        r"\bM\s*\.?\s*R\s*\.?\s*P\s*\.?"
        r"\s*[:\-]?\s*"
        r"(?:₹|rs\.?|inr)?\s*"
        r"(\d{1,6}(?:\.\d{1,2})?)\b",

        # MRP where OCR may have inserted spaces between letters
        r"\bM\s+R\s+P\b"
        r"\s*[:\-]?\s*"
        r"(?:₹|rs\.?|inr)?\s*"
        r"(\d{1,6}(?:\.\d{1,2})?)\b",

        # Maximum Retail Price
        r"\bMAX(?:IMUM)?\s+RETAIL\s+PRICE\b"
        r"\s*[:\-]?\s*"
        r"(?:₹|rs\.?|inr)?\s*"
        r"(\d{1,6}(?:\.\d{1,2})?)\b",

        # Currency immediately before a value, but only when
        # the nearby text contains MRP.
        r"\bMRP\b.{0,20}?"
        r"(?:₹|rs\.?|inr)\s*"
        r"(\d{1,6}(?:\.\d{1,2})?)\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE,
        )

        if match:
            value = match.group(1)

            if value:
                return _clean(value)

    return None




def _detect_mrp_declaration(text: str) -> bool:
    """Detect whether an MRP declaration is present, even if its numeric value is not extracted."""
    if not text:
        return False

    patterns = [
        r"\bM\s*\.?\s*R\s*\.?\s*P\s*\.?",
        r"\bMAX(?:IMUM)?\s+RETAIL\s+PRICE\b",
        r"\bMRP\s+(?:INCL?\.?|INCLUDING)\s+OF\s+ALL\s+TAXES\b",
    ]

    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )


def _extract_mrp_tax_status(text: str) -> bool:
    """Detect explicit inclusive-of-tax wording."""

    patterns = [
        r"inclusive\s+of\s+all\s+taxes",
        r"incl\.?\s+of\s+all\s+taxes",
        r"incl\.?\s+all\s+taxes",
        r"including\s+all\s+taxes",
        r"taxes\s+included",
    ]

    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )


def _extract_date_field(
    text: str,
    labels: List[str],
) -> str | None:
    """
    Extract a date/period following labels such as MFD, EXP, BEST BEFORE.

    Supports:
    - 05/08/2026
    - 05-08-2026
    - 08/2026
    - 6 months
    - 12 months from MFD
    """

    label_pattern = "|".join(labels)

    pattern = (
        rf"(?:{label_pattern})"
        rf"\s*[:.\-]?\s*"
        rf"("
        rf"\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}"
        rf"|"
        rf"\d{{1,2}}[/-]\d{{2,4}}"
        rf"|"
        rf"\d+\s*(?:days?|months?|years?)"
        rf"(?:\s+from\s+(?:mfd|manufacturing|packing))?"
        rf")"
    )

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return _clean(match.group(1))

    return None


def _extract_consumer_care(text: str) -> str | None:
    """Extract email or Indian phone number."""

    email = re.search(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
        text,
        re.IGNORECASE,
    )

    phone = re.search(
        r"(?:\+91[\s\-]?)?[6-9]\d{9}\b",
        text,
        re.IGNORECASE,
    )

    values = []

    if email:
        values.append(email.group(0))

    if phone:
        values.append(phone.group(0))

    if values:
        return ", ".join(values)

    return None


def _extract_generic_name(
    text: str,
    product_type: str,
    specific_product: str | None,
) -> str | None:
    """
    Extract common/generic product name using explicit label wording first,
    followed by conservative product-category detection.
    """

    explicit_patterns = [
        r"(?:product\s+name|generic\s+name)\s*[:\-]\s*([A-Za-z][A-Za-z\s]+)",
    ]

    explicit = _first_match(explicit_patterns, text)

    if explicit:
        return explicit

    lower = text.lower()

    category_map = [
        ("fruit juice", "Fruit Juice"),
        ("fruit juices", "Fruit Juices"),
        ("juice", "Fruit Juice"),
        ("biscuits", "Biscuits"),
        ("cookies", "Cookies"),
        ("honey", "Honey"),
        ("shampoo", "Shampoo"),
        ("toothpaste", "Toothpaste"),
        ("soap", "Soap"),
        ("detergent", "Detergent"),
        ("edible oil", "Edible Oil"),
        ("cooking oil", "Cooking Oil"),
        ("spices", "Spices"),
        ("tea", "Tea"),
        ("coffee", "Coffee"),
        ("milk", "Milk"),
        ("namkeen", "Namkeen"),
        ("snack", "Snack"),
    ]

    for keyword, generic in category_map:
        if keyword in lower:
            return generic

    return None


def _classify_product(text: str) -> tuple[str, str | None]:
    """Basic deterministic product classification."""

    lower = text.lower()

    food_keywords = [
        "juice",
        "biscuits",
        "cookies",
        "honey",
        "milk",
        "tea",
        "coffee",
        "namkeen",
        "snack",
        "food",
        "flour",
        "atta",
        "rice",
        "spice",
        "masala",
        "oil",
        "beverage",
        "drink",
    ]

    cosmetic_keywords = [
        "shampoo",
        "toothpaste",
        "soap",
        "face wash",
        "cream",
        "lotion",
        "moisturizer",
        "cosmetic",
    ]

    electronic_keywords = [
        "charger",
        "adapter",
        "earphone",
        "headphone",
        "speaker",
        "battery",
        "electronic",
        "power bank",
    ]

    if any(keyword in lower for keyword in food_keywords):
        specific = None

        if "juice" in lower:
            specific = "fruit_juices"
        elif "biscuit" in lower or "cookie" in lower:
            specific = "biscuits"
        elif "honey" in lower:
            specific = "honey"
        elif "tea" in lower:
            specific = "tea"
        elif "coffee" in lower:
            specific = "coffee"
        elif "oil" in lower:
            specific = "edible_oil"

        return "food", specific

    if any(keyword in lower for keyword in cosmetic_keywords):
        specific = None

        if "shampoo" in lower:
            specific = "shampoo"
        elif "toothpaste" in lower:
            specific = "toothpaste"
        elif "soap" in lower:
            specific = "soap"

        return "cosmetic", specific

    if any(keyword in lower for keyword in electronic_keywords):
        specific = None

        if "charger" in lower:
            specific = "charger"
        elif "adapter" in lower:
            specific = "adapter"
        elif "battery" in lower:
            specific = "battery"

        return "electronic", specific

    return "general", None


def _extract_product_name(
    ocr_lines: List[Dict[str, Any]],
) -> str | None:
    """
    Conservative product-name extraction.

    Prefer medium/large high-confidence lines that look like actual
    product names rather than addresses, contact information, quantities,
    or regulatory text.
    """

    blacklist = [
        "nutrition",
        "ingredients",
        "manufactured",
        "manufactured by",
        "packed by",
        "marketed by",
        "consumer care",
        "customer care",
        "helpline",
        "fssai",
        "lic",
        "license",
        "mrp",
        "maximum retail",
        "best before",
        "use by",
        "expiry",
        "mfd",
        "mfg",
        "pkd",
        "net quantity",
        "net qty",
        "inclusive of",
        "all taxes",
        "barcode",
        "www.",
        "http",
        "@",
    ]

    candidates = []

    for line in ocr_lines:
        text = _clean(line.get("text", ""))
        confidence = float(line.get("confidence", 0.0))

        if not text:
            continue

        lower = text.lower()

        if confidence < 0.80:
            continue

        if len(text) < 3 or len(text) > 80:
            continue

        if any(item in lower for item in blacklist):
            continue

        if re.fullmatch(r"[\d\s./:%₹,\-]+", text):
            continue

        if re.search(
            r"\b(?:rs|inr|mrp|ml|kg|g|mg|litre|liter|l)\b",
            lower,
        ):
            continue

        candidates.append((confidence, text))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)

    return candidates[0][1]


def extract_fields(
    ocr_lines: List[Dict[str, Any]],
) -> Dict[str, Any]:

    if not ocr_lines:
        return {
            "raw_lines": [],
            "fields": _empty_fields(),
            "num_lines": 0,
        }

    texts = [
        _clean(line.get("text", ""))
        for line in ocr_lines
        if line.get("text")
    ]

    full_text = " ".join(texts)

    fields = _empty_fields()

    # -------------------------------------------------
    # Product classification
    # -------------------------------------------------

    product_type, specific_product = _classify_product(full_text)

    fields["product_type"] = product_type
    fields["specific_product"] = specific_product

    fields["is_food"] = product_type == "food"
    fields["is_cosmetic"] = product_type == "cosmetic"
    fields["is_electronic"] = product_type == "electronic"

    # -------------------------------------------------
    # Brand
    # -------------------------------------------------

    brand_keywords = [
        "tresca",
        "fresca",
        "colgate",
        "britannia",
        "parle",
        "nestle",
        "amul",
        "dabur",
        "patanjali",
        "itc",
        "hindustan unilever",
        "hul",
        "pepsodent",
        "closeup",
        "sensodyne",
        "vim",
        "surf",
        "tide",
        "ariel",
        "lux",
        "dove",
        "lifebuoy",
        "clinic plus",
        "sunsilk",
        "pantene",
        "loreal",
        "nivea",
        "himalaya",
        "godrej",
        "tata",
        "fortune",
        "saffola",
        "mdh",
        "everest",
        "maggi",
        "knorr",
        "kissan",
        "real",
        "tropicana",
        "frooti",
        "bisleri",
        "kinley",
        "aquafina",
    ]

    for brand in brand_keywords:
        if re.search(
            rf"\b{re.escape(brand)}\b",
            full_text,
            re.IGNORECASE,
        ):
            fields["brand"] = brand.title()
            break

    # -------------------------------------------------
    # Product name
    # -------------------------------------------------

    fields["product_name"] = _extract_product_name(ocr_lines)

    # -------------------------------------------------
    # Generic name
    # -------------------------------------------------

    fields["generic_name"] = _extract_generic_name(
        full_text,
        product_type,
        specific_product,
    )

    # -------------------------------------------------
    # Net quantity
    # -------------------------------------------------

    fields["net_quantity"] = _extract_net_quantity(full_text)

    # -------------------------------------------------
    # MRP
    # -------------------------------------------------

    fields["mrp"] = _extract_mrp(full_text)

    fields["mrp_declaration_detected"] = _detect_mrp_declaration(full_text)

    fields["mrp_inclusive_of_taxes"] = (
        _extract_mrp_tax_status(full_text)
    )

    # -------------------------------------------------
    # Unit sale price
    # -------------------------------------------------

    unit_price_patterns = [
        r"(?:unit\s+(?:sale\s+)?price)"
        r"\s*[:\-]?\s*(₹|rs\.?|inr)?\s*"
        r"(\d+(?:\.\d+)?)\s*(?:/|per)\s*(kg|g|l|ml)\b",

        r"(₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)\s*/\s*(kg|g|l|ml)\b",
    ]

    for pattern in unit_price_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)

        if match:
            fields["unit_sale_price"] = _clean(match.group(0))
            break

    # -------------------------------------------------
    # Manufacturer / Packer
    # -------------------------------------------------

    manufacturer_patterns = [
        r"(?:manufactured\s+by|mfd\.?\s*by)"
        r"\s*[:\-]?\s*(.+?)(?=\b(?:consumer|customer|fssai|lic|email|helpline)\b|$)",

        r"(?:packed\s+by|pkd\.?\s*by)"
        r"\s*[:\-]?\s*(.+?)(?=\b(?:consumer|customer|fssai|lic|email|helpline)\b|$)",
    ]

    manufacturer = _first_match(
        manufacturer_patterns,
        full_text,
    )

    if manufacturer:
        fields["manufacturer_address"] = manufacturer

    # -------------------------------------------------
    # Consumer care
    # -------------------------------------------------

    fields["consumer_care"] = _extract_consumer_care(full_text)

    # -------------------------------------------------
    # Manufacturing date
    # -------------------------------------------------

    fields["mfg_date"] = _extract_date_field(
        full_text,
        [
            r"mfd",
            r"mfg",
            r"manufactured\s+on",
            r"date\s+of\s+manufacture",
            r"pkd",
            r"packed\s+on",
            r"date\s+of\s+packing",
        ],
    )

    # -------------------------------------------------
    # Best before
    # -------------------------------------------------

    fields["best_before"] = _extract_date_field(
        full_text,
        [
            r"best\s+before",
            r"best\s+before\s+end",
            r"\bb\.?\s*b\.?\b",
        ],
    )

    # -------------------------------------------------
    # Use by / expiry
    # -------------------------------------------------

    fields["use_by"] = _extract_date_field(
        full_text,
        [
            r"use\s+by",
            r"expiry",
            r"expiry\s+date",
            r"exp",
        ],
    )

    # -------------------------------------------------
    # Shelf life
    # -------------------------------------------------

    fields["has_shelf_life"] = bool(
        fields["best_before"]
        or fields["use_by"]
        or re.search(
            r"\b(?:shelf\s+life|valid\s+for)\b",
            full_text,
            re.IGNORECASE,
        )
    )

    # -------------------------------------------------
    # Imported / country of origin
    # -------------------------------------------------

    country = _first_match(
        [
            r"(?:country\s+of\s+origin|made\s+in|origin)"
            r"\s*[:\-]?\s*([A-Za-z ]+)",
        ],
        full_text,
    )

    if country:
        fields["country_of_origin"] = country
        fields["is_imported"] = (
            country.strip().lower() not in {
                "india",
                "ind",
            }
        )

    return {
        "raw_lines": ocr_lines,
        "fields": fields,
        "num_lines": len(ocr_lines),
    }
