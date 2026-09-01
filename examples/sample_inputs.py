"""
Sample inputs for testing the Rule Engine.
"""

from rule_engine.models import ExtractedFields, ProductType

# 1. Fully compliant general packaged commodity
COMPLIANT_GENERAL = {
    "manufacturer": "ABC Foods Pvt Ltd, Plot 12, MIDC, Pune - 411019",
    "generic_name": "Tomato Ketchup",
    "net_quantity": "500 g",
    "mrp": "MRP Rs. 95.00 (Inclusive of all taxes)",
    "unit_sale_price": "Rs. 0.19 per g",
    "mfg_date": "Jan 2025",
    "consumer_care": "care@abcfoods.com, 1800-123-4567",
    "product_type": "general",
    "is_imported": False,
    "is_food": False,
    "pdp_area_cm2": 180,
    "estimated_font_height_mm": 2.8,
    "ocr_confidence": {
        "mrp": 0.94,
        "net_quantity": 0.91,
        "manufacturer": 0.89,
    },
}

# 2. Non-compliant – missing inclusive of taxes + no email
NON_COMPLIANT_MRP = {
    "manufacturer": "XYZ Ltd, Mumbai",
    "generic_name": "Biscuits",
    "net_quantity": "200 g",
    "mrp": "MRP Rs. 30",
    "consumer_care": "1800-999-8888",
    "product_type": "general",
    "pdp_area_cm2": 120,
    "estimated_font_height_mm": 1.2,  # too small
}

# 3. Food product
FOOD_SAMPLE = {
    "manufacturer": "Fresh Farms, Nashik",
    "generic_name": "Organic Honey",
    "net_quantity": "250 g",
    "mrp": "MRP ₹220 (incl. of all taxes)",
    "best_before": "Dec 2026",
    "consumer_care": "support@freshfarms.in, 022-12345678",
    "product_type": "food",
    "is_food": True,
    "has_shelf_life": True,
}

# 4. Imported electronic item
IMPORTED_ELECTRONIC = {
    "manufacturer": "TechGlobal Importers, Delhi",
    "generic_name": "Wireless Earbuds",
    "net_quantity": "1 Nos",
    "mrp": "MRP Rs. 1999.00 (Inclusive of all taxes)",
    "country_of_origin": "China",
    "consumer_care": "care@techglobal.in",
    "product_type": "electronic",
    "is_imported": True,
    "is_electronic": True,
}

# 5. E-commerce listing
ECOMMERCE_SAMPLE = {
    "manufacturer": "HomeCare Ltd, Bangalore",
    "generic_name": "Floor Cleaner",
    "net_quantity": "1 L",
    "mrp": "MRP Rs. 185 (Inclusive of all taxes)",
    "consumer_care": "help@homecare.com",
    "product_type": "ecommerce",
    "is_ecommerce": True,
}