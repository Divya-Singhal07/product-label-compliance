import json
from pathlib import Path
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG_DIR = BASE_DIR / "debug_outputs"
OUTPUT_DIR = BASE_DIR / "outputs"
REPORT_DIR = BASE_DIR / "reports"

REPORT_DIR.mkdir(exist_ok=True)


# ------------------------------------------------------------
# FIND LATEST FILES
# ------------------------------------------------------------

def find_latest_structured_json():
    files = list(DEBUG_DIR.glob("product_*/structured_result.json"))

    if not files:
        raise FileNotFoundError(
            "No structured_result.json found in debug_outputs/"
        )

    return max(files, key=lambda f: f.stat().st_mtime)


def find_latest_compliance_json():
    files = list(OUTPUT_DIR.glob("*_compliance.json"))

    if not files:
        raise FileNotFoundError(
            "No compliance JSON found in outputs/"
        )

    return max(files, key=lambda f: f.stat().st_mtime)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe(value):
    if value is None or value == "":
        return "Not available"
    return str(value)


# ------------------------------------------------------------
# PDF GENERATOR
# ------------------------------------------------------------

def generate_report(structured, compliance, output_path):

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111827"),
        spaceAfter=3 * mm,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#6B7280"),
        spaceAfter=7 * mm,
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#111827"),
        spaceBefore=5 * mm,
        spaceAfter=3 * mm,
    )

    normal_style = ParagraphStyle(
        "NormalCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=12.5,
        textColor=colors.HexColor("#1F2937"),
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#6B7280"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=normal_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=normal_style,
        fontSize=8,
        leading=11,
    )

    table_label_style = ParagraphStyle(
        "TableLabel",
        parent=table_cell_style,
        fontName="Helvetica-Bold",
    )

    score_style = ParagraphStyle(
        "Score",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=32,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111827"),
    )

    status_style = ParagraphStyle(
        "Status",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#B91C1C"),
    )

    violation_title_style = ParagraphStyle(
        "ViolationTitle",
        parent=normal_style,
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
    )

    story = []

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    story.append(Paragraph("LABEL LENS", title_style))
    story.append(
        Paragraph(
            "PACKAGED COMMODITY COMPLIANCE REPORT",
            subtitle_style,
        )
    )

    generated = datetime.now().strftime(
        "%d %B %Y  |  %I:%M %p"
    )

    story.append(
        Paragraph(
            f"Generated: {generated}",
            small_style,
        )
    )

    story.append(Spacer(1, 4 * mm))

    # --------------------------------------------------------
    # PRODUCT CARD
    # --------------------------------------------------------

    story.append(Paragraph("1. Product Information", section_style))

    product_name = safe(structured.get("product_name"))
    generic_name = safe(structured.get("generic_name"))
    quantity = safe(structured.get("net_quantity"))

    product_card = [
        [
            Paragraph("<b>PRODUCT</b>", table_label_style),
            Paragraph(product_name, table_cell_style),
        ],
        [
            Paragraph("<b>GENERIC NAME</b>", table_label_style),
            Paragraph(generic_name, table_cell_style),
        ],
        [
            Paragraph("<b>NET QUANTITY</b>", table_label_style),
            Paragraph(quantity, table_cell_style),
        ],
        [
            Paragraph("<b>BRAND</b>", table_label_style),
            Paragraph(safe(structured.get("brand")), table_cell_style),
        ],
        [
            Paragraph("<b>MANUFACTURER</b>", table_label_style),
            Paragraph(
                safe(structured.get("manufacturer_address")),
                table_cell_style,
            ),
        ],
        [
            Paragraph("<b>COUNTRY OF ORIGIN</b>", table_label_style),
            Paragraph(
                safe(structured.get("country_of_origin")),
                table_cell_style,
            ),
        ],
    ]

    product_table = Table(
        product_card,
        colWidths=[48 * mm, 132 * mm],
    )

    product_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1),
                 colors.HexColor("#F3F4F6")),
                ("BOX", (0, 0), (-1, -1), 0.8,
                 colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5,
                 colors.HexColor("#E5E7EB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(product_table)

    # --------------------------------------------------------
    # COMPLIANCE SCORE
    # --------------------------------------------------------

    story.append(Paragraph("2. Compliance Assessment", section_style))

    score = float(compliance.get("score", 0))
    is_compliant = compliance.get("is_compliant", False)

    if is_compliant:
        status = "COMPLIANT"
        status_color = "#15803D"
        status_symbol = "PASS"
    else:
        status = "NON-COMPLIANT"
        status_color = "#B91C1C"
        status_symbol = "FAIL"

    status_style_local = ParagraphStyle(
        "StatusLocal",
        parent=status_style,
        textColor=colors.HexColor(status_color),
    )

    score_card = Table(
        [
            [Paragraph(f"{score:.0f} / 100", score_style)],
            [
                Paragraph(
                    f"{status_symbol}  {status}",
                    status_style_local,
                )
            ],
        ],
        colWidths=[180 * mm],
    )

    score_card.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.2,
                 colors.HexColor("#D1D5DB")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
                ("TOPPADDING", (0, 1), (-1, 1), 3),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
            ]
        )
    )

    story.append(score_card)
    story.append(Spacer(1, 2 * mm))

    story.append(
        Paragraph(
            safe(compliance.get("summary")),
            normal_style,
        )
    )

    # --------------------------------------------------------
    # DECLARATION CHECK
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "3. Declaration Checklist",
            section_style,
        )
    )

    fields = [
        ("Manufacturer", "manufacturer_address"),
        ("Generic / Common Name", "generic_name"),
        ("Net Quantity", "net_quantity"),
        ("Maximum Retail Price (MRP)", "mrp"),
        ("Consumer Care Details", "consumer_care"),
        ("Country of Origin", "country_of_origin"),
    ]

    missing_fields = compliance.get("missing_fields", [])

    checklist = [
        [
            Paragraph("REQUIREMENT", table_header_style),
            Paragraph("DETECTED VALUE", table_header_style),
            Paragraph("STATUS", table_header_style),
        ]
    ]

    for label, field in fields:

        value = structured.get(field)

        missing = (
            field in missing_fields
            or value is None
            or value == ""
        )

        if missing:
            status_text = "MISSING"
            status_color = colors.HexColor("#B91C1C")
        else:
            status_text = "PRESENT"
            status_color = colors.HexColor("#15803D")

        status_cell_style = ParagraphStyle(
            f"Status_{field}",
            parent=table_cell_style,
            fontName="Helvetica-Bold",
            textColor=status_color,
        )

        checklist.append(
            [
                Paragraph(label, table_cell_style),
                Paragraph(safe(value), table_cell_style),
                Paragraph(status_text, status_cell_style),
            ]
        )

    checklist_table = Table(
        checklist,
        colWidths=[62 * mm, 78 * mm, 40 * mm],
        repeatRows=1,
    )

    checklist_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0),
                 colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.5,
                 colors.HexColor("#D1D5DB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(checklist_table)

    # --------------------------------------------------------
    # VIOLATIONS
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "4. Violations",
            section_style,
        )
    )

    violations = compliance.get("violations", [])

    if not violations:

        story.append(
            Paragraph(
                "No violations detected.",
                normal_style,
            )
        )

    else:

        for index, violation in enumerate(
            violations,
            start=1
        ):

            severity = safe(
                violation.get("severity")
            ).upper()

            field = safe(
                violation.get("field")
            ).upper()

            message = safe(
                violation.get("message")
            )

            suggestion = safe(
                violation.get("suggestion")
            )

            detected = safe(
                violation.get("detected_value")
            )

            if severity == "HIGH":
                severity_color = "#B91C1C"
            elif severity == "MEDIUM":
                severity_color = "#C2410C"
            else:
                severity_color = "#A16207"

            violation_header_style = ParagraphStyle(
                f"ViolationHeader{index}",
                parent=violation_title_style,
                textColor=colors.HexColor(severity_color),
            )

            violation_content = [
                [
                    Paragraph(
                        f"{severity} — {field}",
                        violation_header_style,
                    )
                ],
                [
                    Paragraph(
                        f"<b>Issue:</b> {message}",
                        normal_style,
                    )
                ],
                [
                    Paragraph(
                        f"<b>Detected Value:</b> {detected}",
                        normal_style,
                    )
                ],
                [
                    Paragraph(
                        f"<b>Recommended Action:</b> "
                        f"{suggestion}",
                        normal_style,
                    )
                ],
            ]

            violation_table = Table(
                violation_content,
                colWidths=[180 * mm],
            )

            violation_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor("#F9FAFB"),
                        ),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.8,
                            colors.HexColor("#D1D5DB"),
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            7,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            7,
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            6,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            6,
                        ),
                    ]
                )
            )

            story.append(
                KeepTogether(
                    [
                        violation_table,
                        Spacer(1, 3 * mm),
                    ]
                )
            )

    # --------------------------------------------------------
    # WARNINGS
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "5. Warnings",
            section_style,
        )
    )

    warnings = compliance.get("warnings", [])

    if warnings:
        for warning in warnings:
            story.append(
                Paragraph(
                    f"• {safe(warning)}",
                    normal_style,
                )
            )
    else:
        story.append(
            Paragraph(
                "No warnings generated.",
                normal_style,
            )
        )

    # --------------------------------------------------------
    # MANUAL REVIEW
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "6. Manual Review",
            section_style,
        )
    )

    if compliance.get("needs_manual_review", False):
        review = "MANUAL REVIEW REQUIRED"
        review_color = "#B91C1C"
    else:
        review = "NO MANUAL REVIEW REQUIRED"
        review_color = "#15803D"

    review_style = ParagraphStyle(
        "Review",
        parent=normal_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor(review_color),
    )

    story.append(
        Paragraph(
            review,
            review_style,
        )
    )

    # --------------------------------------------------------
    # RULE ENGINE
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "7. Rule Engine Information",
            section_style,
        )
    )

    layers = compliance.get("layers_applied", [])

    rule_table = Table(
        [
            [
                Paragraph(
                    "<b>Rule Version</b>",
                    table_cell_style,
                ),
                Paragraph(
                    safe(compliance.get("rule_version")),
                    table_cell_style,
                ),
            ],
            [
                Paragraph(
                    "<b>Layers Applied</b>",
                    table_cell_style,
                ),
                Paragraph(
                    " → ".join(layers)
                    if layers
                    else "None",
                    table_cell_style,
                ),
            ],
        ],
        colWidths=[45 * mm, 135 * mm],
    )

    rule_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1),
                 colors.HexColor("#F3F4F6")),
                ("GRID", (0, 0), (-1, -1), 0.5,
                 colors.HexColor("#D1D5DB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(rule_table)

    # --------------------------------------------------------
    # FOOTER NOTE
    # --------------------------------------------------------

    story.append(Spacer(1, 8 * mm))

    story.append(
        Paragraph(
            "This report is automatically generated by Label Lens "
            "using OCR-extracted information and the configured "
            "compliance rule engine. The result is intended for "
            "automated screening and should not be considered an "
            "official legal or regulatory determination.",
            small_style,
        )
    )

    # --------------------------------------------------------
    # BUILD
    # --------------------------------------------------------

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Label Lens Compliance Report",
        author="Label Lens",
    )

    document.build(story)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    print("\n" + "=" * 60)
    print("LABEL LENS — PDF REPORT GENERATOR")
    print("=" * 60)

    try:

        structured_path = find_latest_structured_json()
        compliance_path = find_latest_compliance_json()

        print(f"\nStructured JSON : {structured_path}")
        print(f"Compliance JSON : {compliance_path}")

        structured = load_json(structured_path)
        compliance = load_json(compliance_path)

        product_name = safe(
            structured.get("product_name")
        )

        filename = (
            product_name
            .replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
            .replace("+", "")
            .replace(":", "")
        )

        output_path = (
            REPORT_DIR
            / f"{filename}_Compliance_Report.pdf"
        )

        generate_report(
            structured,
            compliance,
            output_path,
        )

        print("\n" + "=" * 60)
        print("REPORT GENERATED SUCCESSFULLY")
        print("=" * 60)

        print(f"\nPDF: {output_path}\n")

    except Exception as e:

        print("\nERROR:")
        print(e)


if __name__ == "__main__":
    main()
