"""Generate a clean, filesystem-safe product_id from extracted fields."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional


def _slugify(text: str, max_len: int = 40) -> str:
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len]


def generate_product_id(
    brand: Optional[str],
    product_name: Optional[str],
    net_quantity: Optional[str],
    fallback_prefix: str = "PRODUCT",
) -> str:
    """
    Create a readable product_id.
    Example: BRITANNIA_GOODDAY_200G
    """
    parts = []

    if brand:
        # Take first meaningful part of brand
        brand_clean = _slugify(brand.split(",")[0].split("by")[-1].strip(), max_len=20)
        if brand_clean:
            parts.append(brand_clean)

    if product_name:
        name_clean = _slugify(product_name, max_len=25)
        if name_clean and name_clean not in (parts[0] if parts else ""):
            parts.append(name_clean)

    if net_quantity:
        qty_clean = _slugify(net_quantity, max_len=10)
        if qty_clean:
            parts.append(qty_clean)

    if not parts:
        return f"{fallback_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    return "_".join(parts)
