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
    Layer 2 : Category Rules
    Layer 3 : Product-Specific Rules

    The engine combines:
    - Mandatory-field validation
    - Product/category-specific rules
    - Format validation
    - OCR confidence checking
    - Compliance scoring
    """

    def __init__(self, rules_dir: Optional[Path] = None):
        self.rules_dir = Path(rules_dir) if rules_dir else RULES_DIR

        self.universal_rules: dict = {}
        self.category_rules: Dict[str, dict] = {}
        self.product_rules: Dict[str, dict] = {}

        self._load_all_rules()

    # ============================================================
    # RULE LOADING
    # ============================================================

    def _load_all_rules(self):
        """
        Load all rules from the rules directory.

        Structure:

        rules/
        ├── universal.yaml
        ├── categories/
        │   ├── food.yaml
        │   ├── cosmetic.yaml
        │   └── electronic.yaml
        └── products/
            ├── toothpaste.yaml
            ├── fruit_juices.yaml
            └── ...
        """

        # --------------------------------------------------------
        # Layer 1: Universal Rules
        # --------------------------------------------------------

        universal_file = self.rules_dir / "universal.yaml"

        if universal_file.exists():
            with open(universal_file, "r", encoding="utf-8") as f:
                self.universal_rules = yaml.safe_load(f) or {}

        # --------------------------------------------------------
        # Layer 2: Category Rules
        # --------------------------------------------------------

        cat_dir = self.rules_dir / "categories"

        if cat_dir.exists():
            for f in cat_dir.glob("*.yaml"):
                with open(f, "r", encoding="utf-8") as file:
                    data = yaml.safe_load(file) or {}

                    key = data.get("product_type") or f.stem
                    key = str(key).lower().strip()

                    self.category_rules[key] = data

        # --------------------------------------------------------
        # Backward compatibility:
        # old flat YAML files directly inside rules/
        # --------------------------------------------------------

        for f in self.rules_dir.glob("*.yaml"):

            if f.name == "universal.yaml":
                continue

            with open(f, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}

                key = data.get("product_type") or f.stem
                key = str(key).lower().strip()

                if key not in self.category_rules:
                    self.category_rules[key] = data

        # --------------------------------------------------------
        # Layer 3: Product Rules
        # --------------------------------------------------------

        prod_dir = self.rules_dir / "products"

        if prod_dir.exists():

            for f in prod_dir.glob("*.yaml"):

                with open(f, "r", encoding="utf-8") as file:
                    data = yaml.safe_load(file) or {}

                    key = data.get("product") or f.stem
                    key = str(key).lower().strip()

                    self.product_rules[key] = data

    # ============================================================
    # AVAILABLE RULES
    # ============================================================

    def get_available_categories(self) -> List[str]:
        return list(self.category_rules.keys())

    def get_available_products(self) -> List[str]:
        return list(self.product_rules.keys())

    # ============================================================
    # RULE MERGING
    # ============================================================

    def _build_effective_category_rules(
        self,
        category_rules: dict,
        product_rules: Optional[dict] = None,
    ) -> dict:
        """
        Build the effective mandatory-rule configuration.

        Category rules are used as the base.

        Product-level exemptions can be merged into the effective
        configuration before mandatory validation.

        This keeps the rule engine flexible without hard-coding
        individual products inside Python.
        """

        effective_rules = dict(category_rules or {})

        # Copy nested structures so the original YAML-loaded
        # dictionaries are never modified.
        if "mandatory" in category_rules:
            effective_rules["mandatory"] = dict(
                category_rules.get("mandatory", {})
            )

        if "exempted" in category_rules:
            effective_rules["exempted"] = list(
                category_rules.get("exempted", [])
            )

        # --------------------------------------------------------
        # Product-level exemptions
        # --------------------------------------------------------

        if product_rules:

            product_exempted = product_rules.get(
                "exempted",
                []
            )

            if product_exempted:

                existing_exempted = set(
                    effective_rules.get(
                        "exempted",
                        []
                    )
                )

                existing_exempted.update(
                    product_exempted
                )

                effective_rules["exempted"] = list(
                    existing_exempted
                )

        return effective_rules

    # ============================================================
    # MAIN VALIDATION
    # ============================================================

    def validate(self, data: ExtractedFields) -> ComplianceResult:

        violations: List[Violation] = []
        layers_applied = []

        product_type = (
            data.product_type or "general"
        ).lower().strip()

        # Normalize aliases so Layer 2 hits the correct YAML
        # (e.g. LLM may emit "cosmetic" while file is cosmetics.yaml).
        _TYPE_ALIASES = {
            "cosmetic": "cosmetics",
            "cosmetics": "cosmetics",
            "electronics": "electronic",
            "electronic": "electronic",
            "garment": "garments",
            "garments": "garments",
            "drug": "drugs_medical",
            "drugs": "drugs_medical",
            "drugs_medical": "drugs_medical",
            "medical": "drugs_medical",
            "e-commerce": "ecommerce",
            "ecommerce": "ecommerce",
            "seed": "seeds",
            "seeds": "seeds",
            "multipiece": "multi_piece",
            "multi_piece": "multi_piece",
        }
        product_type = _TYPE_ALIASES.get(product_type, product_type)

        specific_product = (
            data.specific_product or ""
        ).lower().strip() or None

        # ========================================================
        # FIND PRODUCT-SPECIFIC RULES FIRST
        # ========================================================

        prod_rules = {}

        if (
            specific_product
            and specific_product in self.product_rules
        ):
            prod_rules = self.product_rules[
                specific_product
            ]

        # ========================================================
        # LAYER 1 — UNIVERSAL RULES
        # ========================================================

        layers_applied.append("universal")

        # Universal rules are represented primarily through
        # the common validators below.

        # ========================================================
        # LAYER 2 — CATEGORY RULES
        # ========================================================

        cat_rules = self.category_rules.get(
            product_type,
            self.category_rules.get("general", {})
        )

        if cat_rules:

            layers_applied.append(
                f"category:{product_type}"
            )

            # ----------------------------------------------------
            # Build effective category rules.
            #
            # Product-specific exemptions are applied before
            # check_mandatory_fields() runs.
            # ----------------------------------------------------

            effective_cat_rules = (
                self._build_effective_category_rules(
                    cat_rules,
                    prod_rules
                )
            )

            # Category mandatory fields
            violations += check_mandatory_fields(
                data,
                effective_cat_rules
            )

            # Category custom rules
            for check in cat_rules.get(
                "custom_checks",
                []
            ):

                violations += self._run_custom(
                    data,
                    check,
                    "category"
                )

        # ========================================================
        # LAYER 3 — PRODUCT-SPECIFIC RULES
        # ========================================================

        if prod_rules:

            layers_applied.append(
                f"product:{specific_product}"
            )

            violations += self._apply_product_layer(
                data,
                prod_rules
            )

        # ========================================================
        # COMMON FORMAT VALIDATORS
        # ========================================================

        violations += check_mrp_format(data)

        violations += check_quantity_format(data)

        violations += check_date_format(data)

        violations += check_consumer_care(data)

        violations += check_unit_sale_price(data)

        violations += check_country_of_origin(data)

        violations += check_manufacturer(data)

        violations += check_font_size(data)

        # ========================================================
        # OCR CONFIDENCE
        # ========================================================

        needs_review = any(
            data.ocr_confidence.get(field, 1.0)
            < CONFIDENCE_LOW
            for field in [
                "mrp",
                "net_quantity",
                "manufacturer",
                "consumer_care",
            ]
        )

        # ========================================================
        # COMPLIANCE SCORE
        # ========================================================

        score = 100.0

        for violation in violations:

            weight = SEVERITY_WEIGHTS.get(
                violation.severity.value,
                5
            )

            # Product-specific medium/low violations
            # receive slightly lower scoring penalty.
            if (
                violation.layer == "product"
                and violation.severity.value
                in ["medium", "low"]
            ):
                weight = max(
                    2,
                    weight // 2
                )

            score -= weight

        score = max(
            0.0,
            min(100.0, score)
        )

        # ========================================================
        # COMPLIANCE STATUS
        # ========================================================

        is_compliant = all(
            violation.severity != Severity.HIGH
            for violation in violations
        )

        # ========================================================
        # MISSING FIELDS
        # ========================================================

        missing = list({
            violation.field
            for violation in violations
            if violation.rule_id.startswith("PRESENCE_")
        })

        # ========================================================
        # VIOLATION COUNTS
        # ========================================================

        high = len([
            violation
            for violation in violations
            if violation.severity == Severity.HIGH
        ])

        medium = len([
            violation
            for violation in violations
            if violation.severity == Severity.MEDIUM
        ])

        low = len([
            violation
            for violation in violations
            if violation.severity == Severity.LOW
        ])

        # ========================================================
        # SUMMARY
        # ========================================================

        prod_text = (
            f" ({specific_product})"
            if specific_product
            else ""
        )

        if is_compliant and score >= 90:

            summary = (
                f"Package appears COMPLIANT under "
                f"{product_type}{prod_text} rules "
                f"(Score: {score:.0f}/100)."
            )

        elif high == 0:

            summary = (
                f"Mostly compliant with "
                f"{medium} medium and "
                f"{low} low issues "
                f"(Score: {score:.0f}/100). "
                f"Review recommended."
            )

        else:

            summary = (
                f"NON-COMPLIANT: "
                f"{high} high-severity and "
                f"{medium} medium-severity "
                f"violations found "
                f"(Score: {score:.0f}/100)."
            )

        # ========================================================
        # FINAL RESULT
        # ========================================================

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

    # ============================================================
    # PRODUCT LAYER
    # ============================================================

    def _apply_product_layer(
        self,
        data: ExtractedFields,
        rules: dict
    ) -> List[Violation]:

        violations = []

        # --------------------------------------------------------
        # Extra mandatory fields
        # --------------------------------------------------------

        for item in rules.get(
            "extra_mandatory",
            []
        ):

            field = item.get("field")

            if not field:
                continue

            value = getattr(
                data,
                field,
                None
            )

            if (
                not value
                or (
                    isinstance(value, str)
                    and not value.strip()
                )
            ):

                violations.append(
                    Violation(
                        rule_id=(
                            f"PROD_MANDATORY_"
                            f"{field.upper()}"
                        ),
                        field=field,
                        message=item.get(
                            "label",
                            f"Missing field for this product: {field}"
                        ),
                        severity=Severity(
                            item.get(
                                "severity",
                                "medium"
                            )
                        ),
                        suggestion=item.get(
                            "note"
                        ),
                        layer="product",
                    )
                )

        # --------------------------------------------------------
        # Product custom rules
        # --------------------------------------------------------

        for check in rules.get(
            "custom_checks",
            []
        ):

            violations += self._run_custom(
                data,
                check,
                "product"
            )

        return violations

    # ============================================================
    # CUSTOM RULE EVALUATION
    # ============================================================

    def _run_custom(
        self,
        data: ExtractedFields,
        check: dict,
        layer: str
    ) -> List[Violation]:

        """
        Evaluate a custom rule.

        Supported conditions:

        1. must_exist
           Field must contain a value.

        2. expected_contains
           Field must contain the specified text.

        3. expected_any
           Field must contain at least one of the specified values.

        4. must_not_exist
           Field must be empty.

        5. No condition
           The rule is treated as advisory metadata.
           It does NOT automatically become a violation.
        """

        field = check.get("field")

        rule_id = check.get(
            "rule_id",
            "CUSTOM"
        )

        message = check.get(
            "message",
            "Custom rule failed"
        )

        severity = Severity(
            check.get(
                "severity",
                "medium"
            )
        )

        suggestion = check.get(
            "suggestion"
        )

        # --------------------------------------------------------
        # Get field value
        # --------------------------------------------------------

        value = (
            getattr(data, field, None)
            if field
            else None
        )

        value_text = (
            str(value).strip().lower()
            if value is not None
            else ""
        )

        # ========================================================
        # CONDITION 1 — must_exist
        # ========================================================

        if check.get("must_exist"):

            if not value_text:

                return [
                    Violation(
                        rule_id=rule_id,
                        field=field or "general",
                        message=message,
                        severity=severity,
                        suggestion=suggestion,
                        layer=layer,
                    )
                ]

            return []

        # ========================================================
        # CONDITION 2 — expected_contains
        # ========================================================

        if "expected_contains" in check:

            expected = str(
                check["expected_contains"]
            ).strip().lower()

            if expected not in value_text:

                return [
                    Violation(
                        rule_id=rule_id,
                        field=field or "general",
                        message=message,
                        severity=severity,
                        suggestion=suggestion,
                        layer=layer,
                    )
                ]

            return []

        # ========================================================
        # CONDITION 3 — expected_any
        # ========================================================

        if "expected_any" in check:

            expected_values = check.get(
                "expected_any",
                []
            )

            if not any(
                str(item).strip().lower()
                in value_text
                for item in expected_values
            ):

                return [
                    Violation(
                        rule_id=rule_id,
                        field=field or "general",
                        message=message,
                        severity=severity,
                        suggestion=suggestion,
                        layer=layer,
                    )
                ]

            return []

        # ========================================================
        # CONDITION 4 — must_not_exist
        # ========================================================

        if check.get("must_not_exist"):

            if value_text:

                return [
                    Violation(
                        rule_id=rule_id,
                        field=field or "general",
                        message=message,
                        severity=severity,
                        suggestion=suggestion,
                        layer=layer,
                    )
                ]

            return []

        # ========================================================
        # CONDITION 5 — NO CONDITION
        # ========================================================

        # A custom rule without an actual condition is treated
        # as advisory metadata.

        # It must NOT automatically create a violation.

        return []


# ================================================================
# PUBLIC FUNCTION
# ================================================================

def run_compliance_check(data_dict: dict) -> dict:

    engine = RuleEngine()

    fields = ExtractedFields(
        **data_dict
    )

    result = engine.validate(
        fields
    )

    return result.model_dump()
