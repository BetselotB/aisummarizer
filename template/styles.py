"""ReportLab design system — extracted from references/study_guide.py."""

from __future__ import annotations

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Table, TableStyle

DARK_BG = HexColor("#1a1a2e")
ACCENT = HexColor("#e94560")
BLUE = HexColor("#0f3460")
LIGHT_BG = HexColor("#f0f4ff")
CODE_BG = HexColor("#1e1e2e")
CODE_TXT = HexColor("#cdd6f4")
HEADING_COLOR = HexColor("#0f3460")
GRAY = HexColor("#555577")
YELLOW = HexColor("#fffbe6")

W, H = A4


def make_styles():
    s = {}
    s["cover_title"] = ParagraphStyle(
        "cover_title",
        fontName="Helvetica-Bold",
        fontSize=32,
        textColor=white,
        spaceAfter=8,
        alignment=1,
        leading=40,
    )
    s["cover_sub"] = ParagraphStyle(
        "cover_sub",
        fontName="Helvetica",
        fontSize=14,
        textColor=HexColor("#ccddff"),
        spaceAfter=4,
        alignment=1,
    )
    s["chapter"] = ParagraphStyle(
        "chapter",
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=white,
        spaceBefore=4,
        spaceAfter=6,
        alignment=0,
        backColor=HEADING_COLOR,
        borderPad=8,
    )
    s["section"] = ParagraphStyle(
        "section",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=ACCENT,
        spaceBefore=10,
        spaceAfter=4,
    )
    s["subsection"] = ParagraphStyle(
        "subsection",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=HEADING_COLOR,
        spaceBefore=6,
        spaceAfter=3,
    )
    s["body"] = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=9.5,
        textColor=HexColor("#222233"),
        spaceAfter=3,
        leading=14,
        alignment=4,
    )
    s["bullet"] = ParagraphStyle(
        "bullet",
        fontName="Helvetica",
        fontSize=9.5,
        textColor=HexColor("#222233"),
        spaceAfter=2,
        leading=13,
        leftIndent=14,
        bulletIndent=4,
        bulletFontName="Helvetica",
        bulletFontSize=9,
    )
    s["code"] = ParagraphStyle(
        "code",
        fontName="Courier",
        fontSize=8.2,
        textColor=CODE_TXT,
        backColor=CODE_BG,
        spaceAfter=2,
        spaceBefore=2,
        leading=12,
        leftIndent=8,
        rightIndent=8,
        borderPad=6,
        borderWidth=0,
    )
    s["code_label"] = ParagraphStyle(
        "code_label",
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=HexColor("#888aaa"),
        spaceAfter=0,
        spaceBefore=6,
    )
    s["note"] = ParagraphStyle(
        "note",
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=HexColor("#553300"),
        backColor=YELLOW,
        spaceAfter=4,
        leading=13,
        leftIndent=10,
        rightIndent=10,
        borderPad=5,
    )
    s["key"] = ParagraphStyle(
        "key",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=HexColor("#000033"),
        backColor=HexColor("#dde8ff"),
        spaceAfter=4,
        leading=13,
        leftIndent=10,
        rightIndent=10,
        borderPad=5,
    )
    return s


S = make_styles()


def chapter_header(title: str) -> Table:
    data = [[Paragraph(title, S["chapter"])]]
    t = Table(data, colWidths=[W - 40 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HEADING_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )
    return t


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def code_block(lines: str, label: str | None = None) -> list:
    items = []
    if label:
        items.append(Paragraph(label, S["code_label"]))
    safe = escape_html(lines)
    parts = [ln if ln.strip() else " " for ln in safe.split("\n")]
    full = "<br/>".join(parts)
    items.append(Paragraph(full, S["code"]))
    return items


def note_box(text: str) -> Paragraph:
    return Paragraph(f"💡 {text}", S["note"])


def key_box(text: str) -> Paragraph:
    return Paragraph(f"⚡ {text}", S["key"])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"• {text}", S["bullet"])


def subbullet(text: str) -> Paragraph:
    return Paragraph(f"  ◦ {text}", S["bullet"])


def two_col_table(rows, header=None, col_widths=None) -> Table:
    cw = col_widths or [60 * mm, 110 * mm]
    data = []
    if header:
        data.append(
            [
                Paragraph(f"<b>{header[0]}</b>", S["body"]),
                Paragraph(f"<b>{header[1]}</b>", S["body"]),
            ]
        )
    for r in rows:
        data.append([Paragraph(str(r[0]), S["body"]), Paragraph(str(r[1]), S["body"])])
    t = Table(data, colWidths=cw)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#aabbcc")),
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#dde8ff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    t.setStyle(TableStyle(style))
    return t


def three_col_table(rows, header=None, col_widths=None) -> Table:
    cw = col_widths or [30 * mm, 55 * mm, 85 * mm]
    data = []
    if header:
        data.append(
            [
                Paragraph(f"<b>{header[0]}</b>", S["body"]),
                Paragraph(f"<b>{header[1]}</b>", S["body"]),
                Paragraph(f"<b>{header[2]}</b>", S["body"]),
            ]
        )
    for r in rows:
        data.append(
            [
                Paragraph(str(r[0]), S["body"]),
                Paragraph(str(r[1]), S["code"] if header and len(header) == 3 else S["body"]),
                Paragraph(str(r[2]), S["body"]),
            ]
        )
    t = Table(data, colWidths=cw)
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#aabbcc")),
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#dde8ff")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_BG]),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


def compare_table(header, rows, col_widths=None) -> Table:
    cw = col_widths or [87 * mm, 83 * mm]
    data = [
        [
            Paragraph(f"<b>{header[0]}</b>", S["body"]),
            Paragraph(f"<b>{header[1]}</b>", S["body"]),
        ]
    ]
    for r in rows:
        data.append([Paragraph(r[0], S["body"]), Paragraph(r[1], S["body"])])
    t = Table(data, colWidths=cw)
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#aabbcc")),
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#dde8ff")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_BG]),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t
