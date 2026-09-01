"""
FastAPI backend for Legal Metrology Compliance Checker (SIH26034)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
import sys
from pathlib import Path

# Allow importing the rule_engine package
sys.path.append(str(Path(__file__).parent.parent.parent))

from rule_engine import RuleEngine, ExtractedFields, ComplianceResult

app = FastAPI(
    title="Legal Metrology Compliance API",
    description="SIH26034 - Software System to check compliance of Packaged Commodities",
    version="1.0.0",
)

# Allow frontend (React / Flutter) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create engine once at startup
engine = RuleEngine()


class ComplianceRequest(BaseModel):
    """Data coming from OCR + frontend"""
    manufacturer: Optional[str] = None
    packer: Optional[str] = None
    importer: Optional[str] = None
    generic_name: Optional[str] = None
    net_quantity: Optional[str] = None
    mrp: Optional[str] = None
    unit_sale_price: Optional[str] = None
    mfg_date: Optional[str] = None
    best_before: Optional[str] = None
    use_by: Optional[str] = None
    consumer_care: Optional[str] = None
    country_of_origin: Optional[str] = None
    dimensions: Optional[str] = None

    product_type: str = "general"
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


class ViolationOut(BaseModel):
    rule_id: str
    field: str
    message: str
    severity: str
    suggestion: Optional[str] = None
    detected_value: Optional[str] = None
    expected: Optional[str] = None


class ComplianceResponse(BaseModel):
    is_compliant: bool
    score: float
    product_type: str
    summary: str
    needs_manual_review: bool
    missing_fields: List[str]
    violations: List[ViolationOut]
    rule_version: str


@app.get("/")
def root():
    return {
        "message": "Legal Metrology Compliance API is running",
        "docs": "/docs",
        "available_product_types": engine.get_available_product_types(),
    }


@app.get("/product-types")
def get_product_types():
    return {"product_types": engine.get_available_product_types()}


@app.post("/check-compliance", response_model=ComplianceResponse)
def check_compliance(request: ComplianceRequest):
    """
    Main endpoint: Send extracted OCR fields → Get compliance result
    """
    try:
        # Convert request to ExtractedFields
        data = ExtractedFields(**request.model_dump())

        # Run the rule engine
        result: ComplianceResult = engine.validate(data)

        # Convert to response format
        return ComplianceResponse(
            is_compliant=result.is_compliant,
            score=result.score,
            product_type=result.product_type,
            summary=result.summary,
            needs_manual_review=result.needs_manual_review,
            missing_fields=result.missing_fields,
            violations=[
                ViolationOut(
                    rule_id=v.rule_id,
                    field=v.field,
                    message=v.message,
                    severity=v.severity.value,
                    suggestion=v.suggestion,
                    detected_value=v.detected_value,
                    expected=v.expected,
                )
                for v in result.violations
            ],
            rule_version=result.rule_version,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}