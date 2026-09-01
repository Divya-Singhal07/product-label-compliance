import re
from typing import Optional, Tuple
from .config import FONT_SIZE_TABLE


def normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def contains_any(text: str, phrases: list) -> bool:
    text = normalize_text(text)
    return any(p in text for p in phrases)


def extract_number(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"(\d+[.,]?\d*)", text.replace(",", ""))
    if match:
        try:
            return float(match.group(1).replace(",", "."))
        except ValueError:
            return None
    return None


def get_min_font_height(pdp_area_cm2: float) -> float:
    """Return minimum required font height (mm) based on PDP area."""
    for min_a, max_a, height in FONT_SIZE_TABLE:
        if min_a <= pdp_area_cm2 < max_a:
            return height
    return 6.0


def is_valid_email(text: str) -> bool:
    if not text:
        return False
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return bool(re.search(pattern, text))


def is_valid_phone(text: str) -> bool:
    if not text:
        return False
    # Basic Indian phone / toll-free patterns
    digits = re.sub(r"\D", "", text)
    return len(digits) >= 10


def parse_quantity_unit(text: str) -> Tuple[Optional[float], Optional[str]]:
    """Return (value, unit) from net quantity string."""
    if not text:
        return None, None
    text = normalize_text(text)
    match = re.search(
        r"(\d+[.,]?\d*)\s*(kg|g|gm|gram|grams|ml|l|ltr|litre|liter|cm|m|meter|metre|nos|no|number|pcs|pieces?)",
        text,
    )
    if match:
        value = float(match.group(1).replace(",", "."))
        unit = match.group(2)
        # Normalize units
        unit_map = {
            "gm": "g", "gram": "g", "grams": "g",
            "ltr": "l", "litre": "l", "liter": "l",
            "meter": "m", "metre": "m",
            "nos": "nos", "no": "nos", "number": "nos",
            "pcs": "nos", "piece": "nos", "pieces": "nos",
        }
        unit = unit_map.get(unit, unit)
        return value, unit
    return None, None


def has_inclusive_of_taxes(mrp_text: str) -> bool:
    phrases = [
        "inclusive of all taxes",
        "incl. of all taxes",
        "incl of all taxes",
        "inclusive of all tax",
        "incl. of all tax",
        "including all taxes",
        "inclusive of taxes",
    ]
    return contains_any(mrp_text, phrases)