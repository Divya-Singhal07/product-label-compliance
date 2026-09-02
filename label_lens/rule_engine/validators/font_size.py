from typing import List
from ..models import ExtractedFields, Violation, Severity
from ..utils import get_min_font_height


def check_font_size(data: ExtractedFields) -> List[Violation]:
    """
    Check if estimated font height meets the minimum required by Rule 7
    based on Principal Display Panel area.
    """
    violations = []

    if data.pdp_area_cm2 is None or data.estimated_font_height_mm is None:
        # Cannot check without measurements
        return violations

    min_required = get_min_font_height(data.pdp_area_cm2)
    actual = data.estimated_font_height_mm

    if actual < min_required:
        violations.append(
            Violation(
                rule_id="FONT_001",
                field="font_size",
                message=f"Font height ({actual:.1f} mm) is below the minimum required ({min_required} mm) for PDP area of {data.pdp_area_cm2:.0f} cm²",
                severity=Severity.HIGH,
                suggestion=f"Increase font size of mandatory declarations to at least {min_required} mm",
                detected_value=f"{actual:.1f} mm",
                expected=f">= {min_required} mm",
            )
        )

    return violations