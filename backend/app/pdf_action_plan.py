"""
ESGBuddy – PDF Action Plan Generator
Generates a formatted, downloadable PDF for a Gap Analysis / Executive Action Plan.
"""

from __future__ import annotations

import io
import textwrap
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)

# ── Colour palette ──────────────────────────────────────────────────────
FOREST     = colors.HexColor("#3d8269")
FOREST_LT  = colors.HexColor("#e8f5e9")
AMBER      = colors.HexColor("#92400e")
AMBER_LT   = colors.HexColor("#fef3c7")
RED        = colors.HexColor("#991b1b")
RED_LT     = colors.HexColor("#fee2e2")
GREEN_LT   = colors.HexColor("#dcfce7")
GREEN_DK   = colors.HexColor("#166534")
INK        = colors.HexColor("#2d2f33")
GREY       = colors.HexColor("#6b7280")
MID_GREY   = colors.HexColor("#e0e0e0")
LIGHT_GREY = colors.HexColor("#f5f5f5")
WHITE      = colors.white

PILLAR_COLORS = {
    "Environment": (colors.HexColor("#059669"), colors.HexColor("#ecfdf5")),
    "Social":      (colors.HexColor("#4f46e5"), colors.HexColor("#eef2ff")),
    "Governance":  (colors.HexColor("#7c3aed"), colors.HexColor("#f5f3ff")),
}

EFFORT_LABELS = {
    "quick_win": "Quick Win",
    "moderate": "Moderate",
    "structural": "Structural",
}
EFFORT_COLORS = {
    "quick_win":   (GREEN_DK, GREEN_LT),
    "moderate":    (AMBER, AMBER_LT),
    "structural":  (RED, RED_LT),
}

PAGE_W, PAGE_H = A4


def _styles():
    ss = getSampleStyleSheet()
    return dict(
        title=ParagraphStyle(
            "APTitle", parent=ss["Title"],
            fontName="Helvetica-Bold", fontSize=22, leading=28,
            textColor=FOREST, alignment=TA_CENTER, spaceAfter=4,
        ),
        subtitle=ParagraphStyle(
            "APSub", parent=ss["Normal"],
            fontName="Helvetica", fontSize=11, leading=15,
            textColor=INK, alignment=TA_CENTER, spaceAfter=2,
        ),
        meta=ParagraphStyle(
            "APMeta", parent=ss["Normal"],
            fontName="Helvetica", fontSize=9, leading=12,
            textColor=GREY, alignment=TA_CENTER, spaceAfter=14,
        ),
        section=ParagraphStyle(
            "APSection", parent=ss["Heading1"],
            fontName="Helvetica-Bold", fontSize=14, leading=18,
            textColor=FOREST, spaceBefore=16, spaceAfter=8,
        ),
        summary_text=ParagraphStyle(
            "APSummary", parent=ss["Normal"],
            fontName="Helvetica", fontSize=10, leading=14,
            textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6,
        ),
        body=ParagraphStyle(
            "APBody", parent=ss["Normal"],
            fontName="Helvetica", fontSize=9, leading=12,
            textColor=INK, alignment=TA_JUSTIFY, spaceAfter=4,
        ),
        body_bold=ParagraphStyle(
            "APBodyBold", parent=ss["Normal"],
            fontName="Helvetica-Bold", fontSize=9, leading=12,
            textColor=INK, spaceAfter=2,
        ),
        small=ParagraphStyle(
            "APSmall", parent=ss["Normal"],
            fontName="Helvetica", fontSize=8, leading=10,
            textColor=GREY, spaceAfter=2,
        ),
        footer=ParagraphStyle(
            "APFooter", parent=ss["Normal"],
            fontName="Helvetica", fontSize=7, leading=9,
            textColor=GREY, alignment=TA_CENTER,
        ),
    )


def _effort_badge(effort: str) -> str:
    label = EFFORT_LABELS.get(effort, effort.replace("_", " ").title())
    return f"<b>[{label}]</b>"


def _wrap(text: str, max_len: int = 200) -> str:
    """Safely truncate and XML-escape text for reportlab Paragraph."""
    t = (text or "").strip()
    if len(t) > max_len:
        t = t[:max_len].rstrip() + "..."
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_action_plan_pdf(plan: dict, filename: str, framework: str) -> bytes:
    """Return PDF bytes for the given action plan dict."""
    buf = io.BytesIO()
    s = _styles()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )

    story = []

    # ── Cover / Title ─────────────────────────────────────────────────
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph("Executive Action Plan", s["title"]))
    story.append(Paragraph(f"Gap Analysis &amp; Improvement Roadmap", s["subtitle"]))

    meta = plan.get("report_meta") or {}
    rate_pct = f'{meta.get("compliance_rate", 0) * 100:.1f}%' if meta.get("compliance_rate") is not None else "N/A"
    story.append(Paragraph(
        f"{_wrap(filename)} &bull; {framework} &bull; Compliance: {rate_pct} &bull; "
        f"Gaps: {meta.get('gaps_analyzed', '?')} &bull; "
        f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}",
        s["meta"],
    ))

    # Divider
    story.append(Table(
        [[""]], colWidths=[doc.width],
        style=TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 1, FOREST),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]),
    ))

    # ── Executive Summary ─────────────────────────────────────────────
    summary = plan.get("summary")
    if summary:
        story.append(Paragraph("Executive Summary", s["section"]))
        story.append(Table(
            [[Paragraph(_wrap(summary, 800), s["summary_text"])]],
            colWidths=[doc.width],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), FOREST_LT),
                ("BOX", (0, 0), (-1, -1), 0.5, FOREST),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]),
        ))
        story.append(Spacer(1, 8))

    # ── KPI strip ─────────────────────────────────────────────────────
    kpi_data = [
        [Paragraph(f"<b>{rate_pct}</b>", ParagraphStyle("k", parent=s["body_bold"], fontSize=14, alignment=TA_CENTER, textColor=FOREST)),
         Paragraph(f'<b>{meta.get("gaps_analyzed", 0)}</b>', ParagraphStyle("k2", parent=s["body_bold"], fontSize=14, alignment=TA_CENTER, textColor=INK)),
         Paragraph(f'<b>{len(plan.get("top_5") or [])}</b>', ParagraphStyle("k3", parent=s["body_bold"], fontSize=14, alignment=TA_CENTER, textColor=INK))],
        [Paragraph("Current Compliance", ParagraphStyle("kl", parent=s["small"], alignment=TA_CENTER)),
         Paragraph("Gaps Analyzed", ParagraphStyle("kl2", parent=s["small"], alignment=TA_CENTER)),
         Paragraph("Priority Actions", ParagraphStyle("kl3", parent=s["small"], alignment=TA_CENTER))],
    ]
    col_w = doc.width / 3
    story.append(Table(
        kpi_data, colWidths=[col_w] * 3,
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
            ("BOX", (0, 0), (-1, -1), 0.5, MID_GREY),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, MID_GREY),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
            ("TOPPADDING", (0, 1), (-1, 1), 2),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]),
    ))
    story.append(Spacer(1, 12))

    # ── Top 5 Priority Actions ────────────────────────────────────────
    top5 = plan.get("top_5") or []
    if top5:
        story.append(Paragraph(f"Top {len(top5)} Priority Actions", s["section"]))
        for i, item in enumerate(top5, 1):
            effort_text = _effort_badge(item.get("effort", ""))
            pillar = item.get("pillar", "")
            header = f"<b>{i}. {_wrap(item.get('action', ''), 120)}</b>  {effort_text}"
            if pillar:
                header += f"  <i>[{pillar}]</i>"

            rows = [[Paragraph(header, s["body_bold"])]]
            detail = item.get("detail", "")
            if detail:
                rows.append([Paragraph(_wrap(detail, 500), s["body"])])
            impact = item.get("impact", "")
            if impact:
                rows.append([Paragraph(f"<i>{_wrap(impact, 300)}</i>", s["small"])])
            clauses = item.get("clauses") or []
            if clauses:
                rows.append([Paragraph(f"Clauses: {', '.join(clauses)}", s["small"])])

            tbl = Table(rows, colWidths=[doc.width - 0.4 * cm], style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
                ("BOX", (0, 0), (-1, -1), 0.5, MID_GREY),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
            ]))
            story.append(KeepTogether([tbl, Spacer(1, 6)]))

    # ── Pillar breakdown ──────────────────────────────────────────────
    pillars = plan.get("pillars") or {}
    for pillar_name, actions in pillars.items():
        if not actions:
            continue
        p_fg, p_bg = PILLAR_COLORS.get(pillar_name, (FOREST, FOREST_LT))

        story.append(Paragraph(
            f"{pillar_name} — {len(actions)} action{'s' if len(actions) != 1 else ''}",
            ParagraphStyle("PillarHead", parent=s["section"], textColor=p_fg),
        ))

        for item in actions:
            effort_text = _effort_badge(item.get("effort", ""))
            header = f"<b>{_wrap(item.get('action', ''), 120)}</b>  {effort_text}"

            rows = [[Paragraph(header, s["body_bold"])]]
            detail = item.get("detail", "")
            if detail:
                rows.append([Paragraph(_wrap(detail, 500), s["body"])])
            impact = item.get("impact", "")
            if impact:
                rows.append([Paragraph(f"<i>{_wrap(impact, 300)}</i>", s["small"])])
            clauses = item.get("clauses") or []
            if clauses:
                rows.append([Paragraph(f"Clauses: {', '.join(clauses)}", s["small"])])

            tbl = Table(rows, colWidths=[doc.width - 0.4 * cm], style=TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), p_bg),
                ("BOX", (0, 0), (-1, -1), 0.5, MID_GREY),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
            ]))
            story.append(KeepTogether([tbl, Spacer(1, 5)]))

    # ── Footer note ───────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        f"Generated by ESGBuddy on {datetime.now().strftime('%d %b %Y at %H:%M')}",
        s["footer"],
    ))

    doc.build(story)
    return buf.getvalue()
