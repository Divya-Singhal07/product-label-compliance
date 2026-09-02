from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from enum import Enum


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ExtractedFields(BaseModel):
    """Fields extracted from OCR + metadata about the package."""
    manufacturer: Optional[str] = None
    packer: Optional[str] = None
    importer: Optional[str] = None
    generic_name: Optional[str] = None
    net_quantity: Optional[str] = None
    mrp: Optional[str] = None
    mrp_declaration_detected: bool = False
    unit_sale_price: Optional[str] = None
    mfg_date: Optional[str] = None
    best_before: Optional[str] = None
    use_by: Optional[str] = None
    consumer_care: Optional[str] = None
    country_of_origin: Optional[str] = None
    dimensions: Optional[str] = None

    # ===== 3-Layer support =====
    product_type: str = "general"          # Layer 2 : Category
    specific_product: Optional[str] = None # Layer 3 : e.g. "toothpaste"

    is_imported: bool = False
    is_food: bool = False
    is_cosmetic: bool = False
    is_electronic: bool = False
    is_multi_piece: bool = False
    is_combination: bool = False
    is_ecommerce: bool = False
    is_wholesale: bool = False
    has_shelf_life: bool = False

    pdp_area_cm2: Optional[float] = None
    estimated_font_height_mm: Optional[float] = None
    ocr_confidence: Dict[str, float] = Field(default_factory=dict)
    raw_text: Optional[str] = None
    image_path: Optional[str] = None

    class Config:
        use_enum_values = True


class Violation(BaseModel):
    rule_id: str
    field: str
    message: str
    severity: Severity
    suggestion: Optional[str] = None
    detected_value: Optional[str] = None
    expected: Optional[str] = None
    layer: Optional[str] = None


class ComplianceResult(BaseModel):
    is_compliant: bool
    score: float = Field(ge=0, le=100)
    product_type: str
    specific_product: Optional[str] = None
    violations: List[Violation] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    needs_manual_review: bool = False
    summary: str = ""
    rule_version: str = "LMPC_3Layer_2024"
    layers_applied: List[str] = Field(default_factory=list)

    def high_severity_count(self) -> int:
        return len([v for v in self.violations if v.severity == Severity.HIGH])
