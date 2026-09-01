import yaml
from pathlib import Path
from typing import Dict, List, Optional
from .models import ExtractedFields, ComplianceResult, Violation, Severity
from .config import RULES_DIR, SEVERITY_WEIGHTS, CONFIDENCE_LOW
from .validators import (
    check_mandatory_fields,
    check_mrp_format,
    check_quantity_format,
    check_date_format,
    check_consumer_care,
    check_unit_sale_price,
    check_country_of_origin,
    check_manufacturer,
    check_font_size,
)


class RuleEngine:
    """
    3-Layer Legal Metrology Compliance Rule Engine
    Layer 1 : Universal Rules
    Layer 2 : Category Rules (food, cosmetics, electronic...)
    Layer 3 : Product-Specific Rules (toothpaste, packaged_drinking_water...)
    """

    def __init__(self, rules_dir: Optional[Path] = None):
        self.rules_dir = Path(rules_dir) if rules_dir else RULES_DIR
        self.universal_rules: dict = {}
        self.category_rules: Dict[str, dict] = {}
        self.product_rules: Dict[str, dict] = {}
        self._load_all_rules()

    def _load_all_rules(self):
        # Layer 1
        universal_file = self.rules_dir / "universal.yaml"
        if universal_file.exists():
            with open(universal_file, "r", encoding="utf-8") as f:
                self.universal_rules = yaml.safe_load(f) or {}

        # Layer 2 - categories folder
        cat_dir = self.rules_dir / "categories"
        if cat_dir.exists():
            for f in cat_dir.glob("*.yaml"):
                with open(f, "r", encoding="utf-8") as file:
                    data = yaml.safe_load(file) or {}
                    key = data.get("product_type") or f.stem
                    self.category_rules[key] = data

        # Backward compatibility (old flat yaml files)
        for f in self.rules_dir.glob("*.yaml"):
            if f.name == "universal.yaml":
                continue
            with open(f, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
                key = data.get("product_type") or f.stem
                if key not in self.category_rules:
                    self.category_rules[key] = data

        # Layer 3 - products folder
        prod_dir = self.rules_dir / "products"
        if prod_dir.exists():
            for f in prod_dir.glob("*.yaml"):
                with open(f, "r", encoding="utf-8") as file:
                    data = yaml.safe_load(file) or {}
                    key = (data.get("product") or f.stem).lower()
                    self.product_rules[key] = data

    def get_available_categories(self) -> List[str]:
        return list(self.category_rules.keys())

    def get_available_products(self) -> List[str]:
        return list(self.product_rules.keys())

    def validate(self, data: ExtractedFields) -> ComplianceResult:
        violations: List[Violation] = []
        layers_applied = []

        product_type = (data.product_type or "general").lower()
        specific_product = (data.specific_product or "").lower().strip() or None

        # LAYER 1
        layers_applied.append("universal")

        # LAYER 2
        cat_rules = self.category_rules.get(product_type, self.category_rules.get("general", {}))
        if cat_rules:
            layers_applied.append(f"category:{product_type}")
            violations += check_mandatory_fields(data, cat_rules)
            for check in cat_rules.get("custom_checks", []):
                violations += self._run_custom(data, check, "category")

        # LAYER 3
        if specific_product and specific_product in self.product_rules:
            prod_rules = self.product_rules[specific_product]
            layers_applied.append(f"product:{specific_product}")
            violations += self._apply_product_layer(data, prod_rules)

        # Common format validators
        violations += check_mrp_format(data)
        violations += check_quantity_format(data)
        violations += check_date_format(data)
        violations += check_consumer_care(data)
        violations += check_unit_sale_price(data)
        violations += check_country_of_origin(data)
        violations += check_manufacturer(data)
        violations += check_font_size(data)

        needs_review = any(
            data.ocr_confidence.get(f, 1.0) < CONFIDENCE_LOW
            for f in ["mrp", "net_quantity", "manufacturer", "consumer_care"]
        )

        score = 100.0
        for v in violations:
            weight = SEVERITY_WEIGHTS.get(v.severity.value, 5)
            if v.layer == "product" and v.severity.value in ["medium", "low"]:
                weight = max(2, weight // 2)
            score -= weight
        score = max(0.0, min(100.0, score))

        is_compliant = all(v.severity != Severity.HIGH for v in violations)
        missing = list({v.field for v in violations if v.rule_id.startswith("PRESENCE_")})

        high = len([v for v in violations if v.severity == Severity.HIGH])
        medium = len([v for v in violations if v.severity == Severity.MEDIUM])
        prod_text = f" ({specific_product})" if specific_product else ""

        if is_compliant and score >= 90:
            summary = f"Package appears COMPLIANT under {product_type}{prod_text} rules (Score: {score:.0f}/100)."
        elif high == 0:
            summary = f"Mostly compliant with {medium} medium issues (Score: {score:.0f}/100). Review recommended."
        else:
            summary = f"NON-COMPLIANT: {high} high-severity and {medium} medium-severity violations found (Score: {score:.0f}/100)."

        return ComplianceResult(
            is_compliant=is_compliant,
            score=score,
            product_type=product_type,
            specific_product=specific_product,
            violations=violations,
            missing_fields=missing,
            needs_manual_review=needs_review,
            summary=summary,
            rule_version="LMPC_3Layer_2024",
            layers_applied=layers_applied,
        )

    def _apply_product_layer(self, data: ExtractedFields, rules: dict) -> List[Violation]:
        violations = []
        for item in rules.get("extra_mandatory", []):
            field = item.get("field")
            if not field:
                continue
            value = getattr(data, field, None)
            if not value or (isinstance(value, str) and not value.strip()):
                violations.append(Violation(
                    rule_id=f"PROD_MANDATORY_{field.upper()}",
                    field=field,
                    message=item.get("label", f"Missing field for this product: {field}"),
                    severity=Severity(item.get("severity", "medium")),
                    suggestion=item.get("note"),
                    layer="product",
                ))
        for check in rules.get("custom_checks", []):
            violations += self._run_custom(data, check, "product")
        return violations

    def _run_custom(self, data: ExtractedFields, check: dict, layer: str) -> List[Violation]:
        field = check.get("field")
        rule_id = check.get("rule_id", "CUSTOM")
        message = check.get("message", "Custom rule failed")
        severity = Severity(check.get("severity", "medium"))
        suggestion = check.get("suggestion")

        if check.get("must_exist"):
            value = getattr(data, field, None) if field else None
            if not value:
                return [Violation(rule_id=rule_id, field=field or "general", message=message,
                                  severity=severity, suggestion=suggestion, layer=layer)]
            return []
        # Soft / advisory product rules
        return [Violation(rule_id=rule_id, field=field or "general", message=message,
                          severity=severity, suggestion=suggestion, layer=layer)]


def run_compliance_check(data_dict: dict) -> dict:
    engine = RuleEngine()
    fields = ExtractedFields(**data_dict)
    return engine.validate(fields).model_dump()
