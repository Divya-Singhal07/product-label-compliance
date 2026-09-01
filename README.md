# Legal Metrology Compliance Rule Engine (SIH26034)

Complete, production-ready Rule Engine for checking compliance of packaged commodities under the **Legal Metrology (Packaged Commodities) Rules, 2011** (as amended up to 2024).

## Features

- Separate rule sets for **12 product types**
- Presence + Format + Font-size validation
- Severity levels (High / Medium / Low)
- Compliance Score (0–100)
- OCR confidence handling → Manual Review flag
- Clear violation messages + suggestions
- Easy to extend via YAML files

## Supported Product Types

| Type | YAML File | Notes |
|------|-----------|-------|
| general | general.yaml | Default retail packages |
| food | food.yaml | FSSAI priority |
| cosmetics | cosmetics.yaml | Drugs & Cosmetics Rules |
| drugs_medical | drugs_medical.yaml | Limited LMPC scope |
| imported | imported.yaml | Country of Origin mandatory |
| electronic | electronic.yaml | QR code relaxation |
| multi_piece | multi_piece.yaml | USP exempted |
| ecommerce | ecommerce.yaml | No mfg month/year required |
| wholesale | wholesale.yaml | Lighter declarations |
| garments | garments.yaml | Partial exemption |
| seeds | seeds.yaml | Seeds Act exemption |
| alcohol | alcohol.yaml | State Excise priority |

## Project Structure

```
rule_engine/
├── rules/                  # One YAML per product type
├── validators/             # Presence, format, font-size checkers
├── models.py               # Pydantic models
├── engine.py               # Main RuleEngine class
├── config.py
├── utils.py
├── examples/
│   └── sample_inputs.py
├── test_engine.py
└── requirements.txt
```

## Quick Start

```bash
pip install -r requirements.txt

# Run tests
python -m rule_engine.test_engine
```

## Usage Example

```python
from rule_engine import RuleEngine, ExtractedFields

engine = RuleEngine()

data = ExtractedFields(
    manufacturer="ABC Ltd, Mumbai",
    generic_name="Handwash",
    net_quantity="200 ml",
    mrp="MRP Rs. 99 (Inclusive of all taxes)",
    consumer_care="care@abc.com, 1800-111-2222",
    product_type="general",
    pdp_area_cm2=150,
    estimated_font_height_mm=2.6,
)

result = engine.validate(data)

print(result.is_compliant)
print(result.score)
print(result.summary)
for v in result.violations:
    print(v.severity, v.message)
```

## How to Add / Modify Rules

1. Edit the corresponding YAML file in `rules/`.
2. Or add new custom checks under the `custom_checks` key.
3. Restart / reload the engine.

## Integration with Your SIH Project

```python
# After OCR extraction
from rule_engine import RuleEngine, ExtractedFields

engine = RuleEngine()
fields = ExtractedFields(**ocr_output_dict)
compliance = engine.validate(fields)

# Return to frontend / generate PDF report
return compliance.model_dump()
```

## License

Built for Smart India Hackathon 2026 – PS 26034.
Free to use and modify for the hackathon.
```