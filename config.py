from pathlib import Path

BASE_DIR = Path(__file__).parent
RULES_DIR = BASE_DIR / "rules"

# Font size table from Rule 7 (PDP area in cm² → minimum height in mm)
FONT_SIZE_TABLE = [
    (0, 50, 1.0),
    (50, 100, 1.5),
    (100, 500, 2.5),
    (500, 2500, 4.0),
    (2500, float("inf"), 6.0),
]

# Minimum height when text is blown / formed / molded / embossed
BLOWN_FONT_MULTIPLIER = 1.5  # approximate; actual table has separate column

# OCR confidence thresholds
CONFIDENCE_HIGH = 0.85
CONFIDENCE_MEDIUM = 0.70
CONFIDENCE_LOW = 0.50

# Scoring weights
SEVERITY_WEIGHTS = {
    "high": 15,
    "medium": 8,
    "low": 3,
    "info": 0,
}

RULE_VERSION = "LMPC_Rules_2011_as_amended_upto_2024"