"""CSV and PDF rendering for the Reports module."""
from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any, Iterable, List, Optional, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BRAND_GREEN = colors.HexColor("#1B5E20")
BRAND_LIGHT = colors.HexColor("#E8F1E9")


def to_csv(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(["" if value is None else value for value in row])
    return buffer.getvalue().encode("utf-8-sig")


def to_pdf(
    title: str,
    headers: Sequence[str],
    rows: Iterable[Sequence[Any]],
    *,
    farm_name: str = "E&J's CHICKENS",
    subtitle: Optional[str] = None,
    summary_lines: Optional[List[str]] = None,
) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=title,
        author=farm_name,
    )

    styles = getSampleStyleSheet()
    brand_style = ParagraphStyle(
        "Brand", parent=styles["Title"], fontSize=18, textColor=BRAND_GREEN, alignment=0
    )
    subtitle_style = ParagraphStyle(
        "Sub", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#5A6B5C")
    )

    story = [
        Paragraph(farm_name, brand_style),
        Paragraph(title, styles["Heading2"]),
    ]
    if subtitle:
        story.append(Paragraph(subtitle, subtitle_style))
    story.append(
        Paragraph(f"Generated on {date.today():%d %B %Y}", subtitle_style)
    )
    story.append(Spacer(1, 6 * mm))

    if summary_lines:
        for line in summary_lines:
            story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 5 * mm))

    data = [list(headers)] + [["" if cell is None else str(cell) for cell in row] for row in rows]
    if len(data) == 1:
        data.append(["No records for this period."] + [""] * (len(headers) - 1))

    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C8D6C9")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(table)
    document.build(story)
    return buffer.getvalue()
