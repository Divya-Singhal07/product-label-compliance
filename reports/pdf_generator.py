"""
Simple PDF Report Generator for Compliance Results
Uses reportlab (pure Python, easy to install)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
from pathlib import Path
from typing import Optional
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from rule_engine.models import ComplianceResult, ExtractedFields


def generate_compliance_pdf(
    result: ComplianceResult,
    fields: ExtractedFields,
    output_path: str = "compliance_report.pdf",
    officer_name: str = "Enforcement Officer",
) -> str:
    """
    Generate a clean PDF compliance report.
    Returns the path of the generated PDF.
    """

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=6,
        textColor=colors.HexColor("#1a365d"),
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4a5568"),
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "Heading2Custom",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#2c5282"),
        spaceBefore=12,
        spaceAfter=6,
    )
    normal = styles["Normal"]
    small = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
    )

    story = []

    # ===== Header =====
    story.append(Paragraph("LEGAL METROLOGY COMPLIANCE REPORT", title_style))
    story.append(
        Paragraph(
            "Packaged Commodities under Legal Metrology (Packaged Commodities) Rules, 2011",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2c5282")))
    story.append(Spacer(1, 8))

    # ===== Summary Box =====
    status_color = colors.HexColor("#276749") if result.is_compliant else colors.HexColor("#c53030")
    status_text = "COMPLIANT" if result.is_compliant else "NON-COMPLIANT"

    summary_data = [
        ["Status", status_text],
        ["Compliance Score", f"{result.score:.0f} / 100"],
        ["Product Type", result.product_type.upper()],
        ["Needs Manual Review", "Yes" if result.needs_manual_review else "No"],
        ["Report Generated", datetime.now().strftime("%d %b %Y, %H:%M")],
        ["Rule Version", result.rule_version],
    ]

    summary_table = Table(summary_data, colWidths=[60 * mm, 100 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf2f7")),
                ("TEXTCOLOR", (1, 0), (1, 0), status_color),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # ===== Summary Text =====
    story.append(Paragraph("Summary", heading_style))
    story.append(Paragraph(result.summary, normal))
    story.append(Spacer(1, 6))

    # ===== Extracted Fields =====
    story.append(Paragraph("Extracted Declarations", heading_style))

    field_rows = [["Field", "Detected Value"]]
    display_fields = [
        ("Manufacturer / Packer / Importer", fields.manufacturer),
        ("Generic / Common Name", fields.generic_name),
        ("Net Quantity", fields.net_quantity),
        ("MRP", fields.mrp),
        ("Unit Sale Price", fields.unit_sale_price),
        ("Mfg / Packing Date", fields.mfg_date),
        ("Best Before / Use By", fields.best_before or fields.use_by),
        ("Consumer Care", fields.consumer_care),
        ("Country of Origin", fields.country_of_origin),
    ]

    for label, value in display_fields:
        field_rows.append([label, value or "— Not Detected —"])

    field_table = Table(field_rows, colWidths=[65 * mm, 95 * mm])
    field_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#a0aec0")),
                ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f7fafc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(field_table)
    story.append(Spacer(1, 10))

    # ===== Violations =====
    story.append(Paragraph("Violations Found", heading_style))

    if not result.violations:
        story.append(Paragraph("No violations detected. Package appears fully compliant.", normal))
    else:
        viol_rows = [["Severity", "Field", "Issue", "Suggestion"]]
        for v in result.violations:
            viol_rows.append(
                [
                    v.severity.value.upper(),
                    v.field,
                    Paragraph(v.message, small),
                    Paragraph(v.suggestion or "—", small),
                ]
            )

        viol_table = Table(viol_rows, colWidths=[22 * mm, 28 * mm, 55 * mm, 50 * mm])
        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c53030")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#a0aec0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]

        # Color severity cells
        for i, v in enumerate(result.violations, start=1):
            if v.severity.value == "high":
                style_commands.append(("BACKGROUND", (0, i), (0, i), colors.HexColor("#fed7d7")))
            elif v.severity.value == "medium":
                style_commands.append(("BACKGROUND", (0, i), (0, i), colors.HexColor("#fefcbf")))
            else:
                style_commands.append(("BACKGROUND", (0, i), (0, i), colors.HexColor("#e2e8f0")))

        viol_table.setStyle(TableStyle(style_commands))
        story.append(viol_table)

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 6))

    # ===== Footer =====
    story.append(
        Paragraph(
            f"Generated for official use | Officer: {officer_name} | SIH26034 Compliance System",
            ParagraphStyle("Footer", parent=small, alignment=TA_CENTER, textColor=colors.grey),
        )
    )
    story.append(
        Paragraph(
            "This is a system-generated report based on automated image analysis and rule engine. "
            "Final decision rests with the authorized Legal Metrology officer.",
            ParagraphStyle("Disclaimer", parent=small, alignment=TA_CENTER, textColor=colors.grey, fontSize=8),
        )
    )

    doc.build(story)
    return output_path


# ---------- Quick test ----------
if __name__ == "__main__":
    from rule_engine import RuleEngine, ExtractedFields
    from rule_engine.examples.sample_inputs import NON_COMPLIANT_MRP

    engine = RuleEngine()
    fields = ExtractedFields(**NON_COMPLIANT_MRP)
    result = engine.validate(fields)

    path = generate_compliance_pdf(result, fields, "sample_compliance_report.pdf")
    print(f"PDF generated → {path}")