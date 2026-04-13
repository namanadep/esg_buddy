"""
ESGBuddy – PDF Compliance Report Generator
Generates a formatted, downloadable PDF for a single compliance report.
"""

from __future__ import annotations

import io
import textwrap
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.piecharts import Pie

# ── Colour palette (matches ESGBuddy frontend) ──────────────────────────
FOREST    = colors.HexColor("#3d8269")
FOREST_LT = colors.HexColor("#e8f5e9")
CLAY      = colors.HexColor("#f0ebe3")
INK       = colors.HexColor("#2d2f33")
WHITE     = colors.white
LIGHT_GREY = colors.HexColor("#f5f5f5")
MID_GREY   = colors.HexColor("#e0e0e0")

STATUS_COLOURS = {
    "supported":     (colors.HexColor("#dcfce7"), colors.HexColor("#166534")),
    "partial":       (colors.HexColor("#fef9c3"), colors.HexColor("#854d0e")),
    "not_supported": (colors.HexColor("#fee2e2"), colors.HexColor("#991b1b")),
}

PAGE_W, PAGE_H = A4


# ── Styles ───────────────────────────────────────────────────────────────
def _build_styles():
    ss = getSampleStyleSheet()

    cover_title = ParagraphStyle(
        "CoverTitle", parent=ss["Title"],
        fontName="Helvetica-Bold", fontSize=26, leading=32,
        textColor=FOREST, alignment=TA_CENTER, spaceAfter=6,
    )
    cover_sub = ParagraphStyle(
        "CoverSub", parent=ss["Normal"],
        fontName="Helvetica", fontSize=13, leading=18,
        textColor=INK, alignment=TA_CENTER, spaceAfter=4,
    )
    section = ParagraphStyle(
        "Section", parent=ss["Heading1"],
        fontName="Helvetica-Bold", fontSize=14, leading=18,
        textColor=FOREST, spaceBefore=18, spaceAfter=8,
    )
    subsection = ParagraphStyle(
        "Subsection", parent=ss["Heading2"],
        fontName="Helvetica-Bold", fontSize=11, leading=14,
        textColor=INK, spaceBefore=10, spaceAfter=4,
    )
    body = ParagraphStyle(
        "Body", parent=ss["Normal"],
        fontName="Helvetica", fontSize=9, leading=12,
        textColor=INK, alignment=TA_JUSTIFY, spaceAfter=4,
    )
    body_bold = ParagraphStyle(
        "BodyBold", parent=body,
        fontName="Helvetica-Bold",
    )
    small = ParagraphStyle(
        "Small", parent=body,
        fontSize=8, leading=10, textColor=colors.HexColor("#666666"),
    )
    table_header = ParagraphStyle(
        "TH", fontName="Helvetica-Bold", fontSize=9, leading=11,
        textColor=WHITE, alignment=TA_CENTER,
    )
    table_cell = ParagraphStyle(
        "TC", fontName="Helvetica", fontSize=8.5, leading=11,
        textColor=INK, alignment=TA_LEFT,
    )
    table_cell_center = ParagraphStyle(
        "TCC", parent=table_cell, alignment=TA_CENTER,
    )
    footer = ParagraphStyle(
        "Footer", fontName="Helvetica", fontSize=7, leading=9,
        textColor=colors.HexColor("#999999"), alignment=TA_CENTER,
    )
    return dict(
        cover_title=cover_title, cover_sub=cover_sub,
        section=section, subsection=subsection,
        body=body, body_bold=body_bold, small=small,
        th=table_header, tc=table_cell, tcc=table_cell_center,
        footer=footer,
    )


# ── Page templates (header/footer) ──────────────────────────────────────
def _header_footer(canvas, doc, filename: str, framework: str):
    canvas.saveState()
    # Header line
    canvas.setStrokeColor(FOREST)
    canvas.setLineWidth(0.8)
    canvas.line(2 * cm, PAGE_H - 1.6 * cm, PAGE_W - 2 * cm, PAGE_H - 1.6 * cm)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(FOREST)
    canvas.drawString(2 * cm, PAGE_H - 1.45 * cm, "ESGBuddy Compliance Report")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(INK)
    canvas.drawRightString(PAGE_W - 2 * cm, PAGE_H - 1.45 * cm, f"{framework} | {filename}")
    # Footer
    canvas.setStrokeColor(MID_GREY)
    canvas.line(2 * cm, 1.6 * cm, PAGE_W - 2 * cm, 1.6 * cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#999999"))
    canvas.drawString(2 * cm, 1.2 * cm, f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}")
    canvas.drawRightString(PAGE_W - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


# ── Chart helpers ────────────────────────────────────────────────────────

# Dashboard-aligned palette
CHART_SUPPORTED     = colors.HexColor("#2a6752")
CHART_PARTIAL       = colors.HexColor("#c4a574")
CHART_NOT_SUPPORTED = colors.HexColor("#c45c5c")
CHART_TRACK         = colors.HexColor("#eae6dc")
CHART_GRID          = colors.HexColor("#e0d5c5")
CHART_TITLE         = colors.HexColor("#2d2f33")
CHART_SUB           = colors.HexColor("#6f6f78")
CHART_MUTED         = colors.HexColor("#9aa0a6")

CHART_W, CHART_H = 228, 190


def _chart_header(d: Drawing, title: str, subtitle: str) -> None:
    """Top-left aligned title + subtitle block on every chart."""
    d.add(String(16, CHART_H - 16, title,
                 fontName="Helvetica-Bold", fontSize=10.5,
                 fillColor=CHART_TITLE))
    d.add(String(16, CHART_H - 28, subtitle,
                 fontName="Helvetica", fontSize=7.5,
                 fillColor=CHART_SUB))


def _no_data(d: Drawing) -> Drawing:
    d.add(String(CHART_W / 2, CHART_H / 2 - 10, "No data",
                 fontName="Helvetica-Oblique", fontSize=9,
                 fillColor=CHART_MUTED, textAnchor="middle"))
    return d


def _make_compliance_gauge(rate: float) -> Drawing:
    """Donut gauge with big compliance % in the center."""
    d = Drawing(CHART_W, CHART_H)
    _chart_header(d, "Compliance Rate", "Overall supported + partial / total")

    pct = max(min(rate * 100, 100), 0)

    pc = Pie()
    pc.x = (CHART_W - 118) / 2
    pc.y = 32
    pc.width = 118
    pc.height = 118
    pc.data = [pct if pct > 0 else 0.0001, max(100 - pct, 0.0001)]
    pc.labels = None
    pc.slices[0].fillColor = CHART_SUPPORTED
    pc.slices[0].strokeColor = colors.white
    pc.slices[0].strokeWidth = 1.5
    pc.slices[1].fillColor = CHART_TRACK
    pc.slices[1].strokeColor = colors.white
    pc.slices[1].strokeWidth = 1.5
    pc.innerRadiusFraction = 0.68
    pc.startAngle = 90
    pc.direction = "clockwise"
    d.add(pc)

    cx = CHART_W / 2
    cy = 32 + 59
    d.add(String(cx, cy - 2, f"{pct:.1f}%",
                 fontName="Helvetica-Bold", fontSize=22,
                 fillColor=CHART_SUPPORTED, textAnchor="middle"))
    d.add(String(cx, cy - 16, "compliance",
                 fontName="Helvetica", fontSize=7.5,
                 fillColor=CHART_MUTED, textAnchor="middle"))
    return d


def _make_status_donut(supported: int, partial: int, not_supp: int, total: int) -> Drawing:
    """3-slice donut + side legend; total count in the hole."""
    d = Drawing(CHART_W, CHART_H)
    _chart_header(d, "Status Distribution", "Clauses by evaluation outcome")

    if total == 0:
        return _no_data(d)

    items = [
        (supported, CHART_SUPPORTED,     "Supported"),
        (partial,   CHART_PARTIAL,       "Partial"),
        (not_supp,  CHART_NOT_SUPPORTED, "Not Supported"),
    ]

    pc = Pie()
    pc.x = 18
    pc.y = 28
    pc.width = 118
    pc.height = 118
    pc.data   = [v for v, _, _ in items if v > 0]
    pc.labels = None
    vis_clrs  = [c for v, c, _ in items if v > 0]
    for i, c in enumerate(vis_clrs):
        pc.slices[i].fillColor = c
        pc.slices[i].strokeColor = colors.white
        pc.slices[i].strokeWidth = 1.5
    pc.innerRadiusFraction = 0.58
    pc.startAngle = 90
    pc.direction = "clockwise"
    d.add(pc)

    # Center total
    cx = 18 + 59
    cy = 28 + 59
    d.add(String(cx, cy + 1, str(total),
                 fontName="Helvetica-Bold", fontSize=18,
                 fillColor=CHART_TITLE, textAnchor="middle"))
    d.add(String(cx, cy - 11, "clauses",
                 fontName="Helvetica", fontSize=7,
                 fillColor=CHART_MUTED, textAnchor="middle"))

    # Legend on right
    ly = 130
    for v, c, lbl in items:
        if v == 0:
            continue
        d.add(Rect(150, ly, 10, 10, fillColor=c, strokeColor=None))
        d.add(String(164, ly + 2, lbl,
                     fontName="Helvetica-Bold", fontSize=8,
                     fillColor=CHART_TITLE))
        pct = f"{v / total * 100:.0f}%"
        d.add(String(164, ly - 9, f"{v}  ({pct})",
                     fontName="Helvetica", fontSize=7,
                     fillColor=CHART_SUB))
        ly -= 30
    return d


def _make_outcomes_bars(supported: int, partial: int, not_supp: int, total: int) -> Drawing:
    """Horizontal bar comparison — count + share by status."""
    d = Drawing(CHART_W, CHART_H)
    _chart_header(d, "Clause Outcomes", "Count and share by status")

    if total == 0:
        return _no_data(d)

    items = [
        ("Supported",     supported, CHART_SUPPORTED),
        ("Partial",       partial,   CHART_PARTIAL),
        ("Not Supported", not_supp,  CHART_NOT_SUPPORTED),
    ]

    track_x = 88
    track_w = 104
    bar_h   = 16
    gap     = 18
    y_top   = CHART_H - 62

    for i, (lbl, val, c) in enumerate(items):
        y = y_top - i * (bar_h + gap)
        # Label on left
        d.add(String(82, y + 5, lbl,
                     fontName="Helvetica-Bold", fontSize=8,
                     fillColor=CHART_TITLE, textAnchor="end"))
        # Track (background)
        d.add(Rect(track_x, y, track_w, bar_h,
                   fillColor=CHART_TRACK, strokeColor=None))
        # Value bar
        val_w = (val / total) * track_w if total else 0
        if val_w > 0:
            d.add(Rect(track_x, y, val_w, bar_h,
                       fillColor=c, strokeColor=None))
        # Count + pct on right
        pct = f"{val / total * 100:.0f}%"
        d.add(String(track_x + track_w + 6, y + 5, f"{val}  ({pct})",
                     fontName="Helvetica-Bold", fontSize=8,
                     fillColor=CHART_TITLE))
    return d


def _make_confidence_histogram(evaluations: list) -> Drawing:
    """5-bucket histogram of final_confidence values."""
    d = Drawing(CHART_W, CHART_H)
    _chart_header(d, "Confidence Distribution", "AI confidence score buckets")

    if not evaluations:
        return _no_data(d)

    buckets = [0, 0, 0, 0, 0]
    for ev in evaluations:
        conf = getattr(ev, "final_confidence", 0) or 0
        idx = min(int(conf * 5), 4)
        buckets[idx] += 1

    bar_colors = [
        colors.HexColor("#c45c5c"),
        colors.HexColor("#e09040"),
        colors.HexColor("#c4a574"),
        colors.HexColor("#7ab38a"),
        colors.HexColor("#2a6752"),
    ]
    x_labels = ["0–20%", "20–40%", "40–60%", "60–80%", "80–100%"]

    cx, cy = 34, 30
    cw, ch = 180, 120
    max_b = max(buckets) if max(buckets) > 0 else 1
    bw = cw / 5

    # Grid + y-axis ticks
    for i in range(5):
        t = i / 4
        y = cy + t * ch
        tick = int(round(t * max_b))
        d.add(Line(cx, y, cx + cw, y,
                   strokeColor=CHART_GRID, strokeWidth=0.4))
        d.add(String(cx - 4, y - 3, str(tick),
                     fontName="Helvetica", fontSize=6.5,
                     fillColor=CHART_MUTED, textAnchor="end"))

    # Baseline
    d.add(Line(cx, cy, cx + cw, cy,
               strokeColor=colors.HexColor("#bcbcbc"), strokeWidth=0.7))

    # Bars
    for i, (count, lbl, bc) in enumerate(zip(buckets, x_labels, bar_colors)):
        inner = bw - 10
        bx = cx + i * bw + 5
        bh = (count / max_b) * ch if count > 0 else 0
        if bh > 0:
            d.add(Rect(bx, cy, inner, bh, fillColor=bc, strokeColor=None))
        if count > 0:
            d.add(String(bx + inner / 2, cy + bh + 3, str(count),
                         fontName="Helvetica-Bold", fontSize=8,
                         fillColor=CHART_TITLE, textAnchor="middle"))
        d.add(String(bx + inner / 2, cy - 12, lbl,
                     fontName="Helvetica", fontSize=6.5,
                     fillColor=CHART_SUB, textAnchor="middle"))
    return d


def _build_visual_section(total: int, supported: int, partial: int,
                           not_supp: int, evaluations: list, rate: float) -> Table:
    """2×2 grid of polished charts: gauge, donut, outcomes, confidence."""
    gauge = _make_compliance_gauge(rate)
    donut = _make_status_donut(supported, partial, not_supp, total)
    bars  = _make_outcomes_bars(supported, partial, not_supp, total)
    hist  = _make_confidence_histogram(evaluations)

    chart_tbl = Table(
        [[gauge, donut],
         [bars,  hist]],
        colWidths=[CHART_W + 8, CHART_W + 8],
        rowHeights=[CHART_H + 4, CHART_H + 4],
    )
    chart_tbl.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND",    (0, 0), (-1, -1), WHITE),
        ("BOX",           (0, 0), (-1, -1), 0.6, MID_GREY),
        ("INNERGRID",     (0, 0), (-1, -1), 0.6, MID_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
    ]))
    return chart_tbl


# ── Public API ───────────────────────────────────────────────────────────
def generate_compliance_pdf(report: Any) -> bytes:
    """
    Accept a ComplianceReport model instance and return PDF bytes.
    """
    buf = io.BytesIO()
    sty = _build_styles()

    filename = report.document_metadata.filename
    framework = report.framework.value

    frame_body = Frame(2 * cm, 2 * cm, PAGE_W - 4 * cm, PAGE_H - 4.2 * cm, id="body")
    frame_cover = Frame(2 * cm, 2 * cm, PAGE_W - 4 * cm, PAGE_H - 4 * cm, id="cover")

    def _on_page(canvas, doc):
        _header_footer(canvas, doc, filename, framework)

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2.2 * cm, bottomMargin=2 * cm,
    )
    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[frame_cover]),
        PageTemplate(id="Content", frames=[frame_body], onPage=_on_page),
    ])

    story: list = []

    # ── Cover page ───────────────────────────────────────────────────
    story.append(Spacer(1, 5 * cm))
    story.append(Paragraph("ESGBuddy", sty["cover_title"]))
    story.append(Paragraph("Compliance Report", sty["cover_sub"]))
    story.append(Spacer(1, 1.2 * cm))

    # Divider
    story.append(Table(
        [[""]], colWidths=[8 * cm],
        style=TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 2, FOREST),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]),
    ))
    story.append(Spacer(1, 1.2 * cm))

    story.append(Paragraph(filename, ParagraphStyle(
        "CoverFile", fontName="Helvetica-Bold", fontSize=16, leading=20,
        textColor=INK, alignment=TA_CENTER, spaceAfter=8,
    )))
    story.append(Paragraph(f"Framework: {framework}", sty["cover_sub"]))
    story.append(Paragraph(
        f"Generated: {report.generated_at.strftime('%d %B %Y, %H:%M')}",
        sty["cover_sub"],
    ))
    story.append(Spacer(1, 2 * cm))

    # Cover summary box
    rate = report.summary.get("compliance_rate", 0)
    total = report.summary.get("total_clauses", 0)
    supported = report.summary.get("supported", 0)
    partial = report.summary.get("partial", 0)
    not_supp = report.summary.get("not_supported", 0)

    box_data = [[
        Paragraph(f"<b>{rate * 100:.1f}%</b>", ParagraphStyle("bx", fontName="Helvetica-Bold", fontSize=22, textColor=FOREST, alignment=TA_CENTER)),
        Paragraph(f"<b>{total}</b><br/><font size=8>Total</font>", ParagraphStyle("bx2", fontName="Helvetica-Bold", fontSize=16, textColor=INK, alignment=TA_CENTER, leading=18)),
        Paragraph(f"<b>{supported}</b><br/><font size=8>Supported</font>", ParagraphStyle("bx3", fontName="Helvetica-Bold", fontSize=16, textColor=colors.HexColor("#166534"), alignment=TA_CENTER, leading=18)),
        Paragraph(f"<b>{partial}</b><br/><font size=8>Partial</font>", ParagraphStyle("bx4", fontName="Helvetica-Bold", fontSize=16, textColor=colors.HexColor("#854d0e"), alignment=TA_CENTER, leading=18)),
        Paragraph(f"<b>{not_supp}</b><br/><font size=8>Not Supported</font>", ParagraphStyle("bx5", fontName="Helvetica-Bold", fontSize=16, textColor=colors.HexColor("#991b1b"), alignment=TA_CENTER, leading=18)),
    ]]
    box_table = Table(box_data, colWidths=[3.2 * cm] * 5)
    box_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 1, FOREST),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, MID_GREY),
        ("BACKGROUND", (0, 0), (0, 0), FOREST_LT),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(box_table)

    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph(
        "Intelligent ESG Compliance Copilot",
        ParagraphStyle("tagline", fontName="Helvetica-Oblique", fontSize=10,
                        textColor=colors.HexColor("#888888"), alignment=TA_CENTER),
    ))

    # Switch to content template
    story.append(NextPageTemplate("Content"))
    story.append(PageBreak())

    # ── Executive Summary ────────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary", sty["section"]))
    story.append(Paragraph(
        f"This report presents the automated compliance evaluation of "
        f"<b>{filename}</b> against the <b>{framework}</b> ESG framework. "
        f"A total of <b>{total}</b> clauses were evaluated using ESGBuddy's hybrid pipeline "
        f"combining semantic retrieval (RAG), LLM-based reasoning (GPT-4o-mini), and "
        f"deterministic rule validation.",
        sty["body"],
    ))
    story.append(Paragraph(
        f"The overall compliance rate is <b>{rate * 100:.1f}%</b>, with "
        f"<b>{supported}</b> clauses fully supported, <b>{partial}</b> partially met, "
        f"and <b>{not_supp}</b> not supported. "
        f"The average confidence score across all evaluations is "
        f"<b>{report.summary.get('average_confidence', 0) * 100:.0f}%</b>.",
        sty["body"],
    ))
    story.append(Spacer(1, 4 * mm))

    # ── Visual charts ────────────────────────────────────────────────
    story.append(Paragraph("2. Visual Summary", sty["section"]))
    story.append(Paragraph(
        "The charts below visualise the headline compliance rate, the clause-level status "
        "breakdown, and the distribution of confidence scores assigned by the AI evaluator.",
        sty["body"],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(_build_visual_section(
        total, supported, partial, not_supp, report.evaluations, rate
    ))

    # ── Status distribution table ────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("3. Compliance Status Distribution", sty["section"]))

    dist_data = [
        [Paragraph("Status", sty["th"]),
         Paragraph("Count", sty["th"]),
         Paragraph("Percentage", sty["th"])],
        [Paragraph("Supported", sty["tc"]),
         Paragraph(str(supported), sty["tcc"]),
         Paragraph(f"{supported / total * 100:.1f}%" if total else "0%", sty["tcc"])],
        [Paragraph("Partial", sty["tc"]),
         Paragraph(str(partial), sty["tcc"]),
         Paragraph(f"{partial / total * 100:.1f}%" if total else "0%", sty["tcc"])],
        [Paragraph("Not Supported", sty["tc"]),
         Paragraph(str(not_supp), sty["tcc"]),
         Paragraph(f"{not_supp / total * 100:.1f}%" if total else "0%", sty["tcc"])],
        [Paragraph("<b>Total</b>", sty["tc"]),
         Paragraph(f"<b>{total}</b>", sty["tcc"]),
         Paragraph("<b>100%</b>", sty["tcc"])],
    ]
    dist_table = Table(dist_data, colWidths=[6 * cm, 4 * cm, 4 * cm])
    dist_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FOREST),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, MID_GREY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, LIGHT_GREY]),
        ("BACKGROUND", (0, -1), (-1, -1), CLAY),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(dist_table)
    story.append(Spacer(1, 6 * mm))

    # ── Clause-by-clause results ─────────────────────────────────────
    story.append(Paragraph("4. Clause-Level Evaluation Results", sty["section"]))
    story.append(Paragraph(
        "The following table summarises the compliance status, confidence score, "
        "and AI explanation for each evaluated clause.",
        sty["body"],
    ))
    story.append(Spacer(1, 3 * mm))

    # Build rows in groups to keep page breaks clean
    col_widths = [4.5 * cm, 2.2 * cm, 1.5 * cm, 8.8 * cm]

    header_row = [
        Paragraph("Clause", sty["th"]),
        Paragraph("Status", sty["th"]),
        Paragraph("Conf.", sty["th"]),
        Paragraph("Explanation", sty["th"]),
    ]

    # Process evaluations in batches for table splitting
    evals = report.evaluations
    BATCH = 30
    for batch_start in range(0, len(evals), BATCH):
        batch = evals[batch_start : batch_start + BATCH]
        rows = [header_row]
        for ev in batch:
            status_val = ev.final_status.value if hasattr(ev.final_status, "value") else str(ev.final_status)
            status_label = status_val.replace("_", " ").title()
            bg, fg = STATUS_COLOURS.get(status_val, (LIGHT_GREY, INK))

            # Truncate explanation for table
            expl = ""
            if ev.llm_evaluation and ev.llm_evaluation.explanation:
                expl = ev.llm_evaluation.explanation[:250]
                if len(ev.llm_evaluation.explanation) > 250:
                    expl += "..."

            clause_title = ev.clause.title if ev.clause.title else ev.clause_id
            if len(clause_title) > 50:
                clause_title = clause_title[:47] + "..."

            rows.append([
                Paragraph(f"<b>{_xml_safe(ev.clause_id)}</b><br/><font size=7>{_xml_safe(clause_title)}</font>", sty["tc"]),
                Paragraph(f"<font color='{fg.hexval()}'><b>{status_label}</b></font>", sty["tcc"]),
                Paragraph(f"{ev.final_confidence * 100:.0f}%", sty["tcc"]),
                Paragraph(_xml_safe(expl), sty["tc"]),
            ])

        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), FOREST),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, MID_GREY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        if batch_start + BATCH < len(evals):
            story.append(Spacer(1, 2 * mm))

    story.append(Spacer(1, 6 * mm))

    # ── Detailed evidence section (top evidence per clause) ──────────
    story.append(PageBreak())
    story.append(Paragraph("5. Evidence References", sty["section"]))
    story.append(Paragraph(
        "For each clause, the top retrieved evidence chunk is listed below with "
        "the source page number and semantic similarity score.",
        sty["body"],
    ))
    story.append(Spacer(1, 3 * mm))

    for ev in evals:
        if not ev.retrieved_evidence:
            continue
        top_ev = max(ev.retrieved_evidence, key=lambda e: e.similarity_score)
        status_val = ev.final_status.value if hasattr(ev.final_status, "value") else str(ev.final_status)
        _, fg = STATUS_COLOURS.get(status_val, (LIGHT_GREY, INK))

        evidence_text = top_ev.text[:300]
        if len(top_ev.text) > 300:
            evidence_text += "..."

        block = [
            Paragraph(
                f"<b>{_xml_safe(ev.clause_id)}</b> "
                f"<font color='{fg.hexval()}'>[{status_val.replace('_', ' ').title()}]</font> "
                f"&mdash; Page {top_ev.page_number} "
                f"({top_ev.similarity_score * 100:.0f}% match)",
                sty["body_bold"],
            ),
            Paragraph(
                f"<i>\"{_xml_safe(evidence_text)}\"</i>",
                sty["small"],
            ),
            Spacer(1, 3 * mm),
        ]
        story.append(KeepTogether(block))

    # ── Footer note ──────────────────────────────────────────────────
    story.append(Spacer(1, 1 * cm))
    story.append(Table(
        [[""]], colWidths=[14 * cm],
        style=TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.5, MID_GREY)]),
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "This report was generated automatically by ESGBuddy \u2014 Intelligent ESG Compliance Copilot. "
        "Results are based on AI-assisted analysis and should be reviewed by qualified professionals "
        "before making compliance decisions.",
        sty["small"],
    ))

    # ── Build ────────────────────────────────────────────────────────
    doc.build(story)
    return buf.getvalue()


def _xml_safe(text: str) -> str:
    """Escape characters that break ReportLab's XML parser."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
