"""JSON document → ReportLab PDF renderer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from template.styles import (
    ACCENT,
    BLUE,
    DARK_BG,
    GRAY,
    S,
    W,
    bullet,
    chapter_header,
    code_block,
    compare_table,
    key_box,
    note_box,
    subbullet,
    three_col_table,
    two_col_table,
)


def _spacer(height_mm: float = 4) -> Spacer:
    return Spacer(1, height_mm * mm)


def render_block(block: dict[str, Any]) -> list:
    """Turn one JSON block into ReportLab flowables."""
    kind = block.get("type")
    out: list = []

    if kind == "section":
        out.append(Paragraph(block["title"], S["section"]))
    elif kind == "subsection":
        out.append(Paragraph(block["title"], S["subsection"]))
    elif kind == "body":
        out.append(Paragraph(block["text"], S["body"]))
    elif kind == "bullet":
        out.append(bullet(block["text"]))
    elif kind == "subbullet":
        out.append(subbullet(block["text"]))
    elif kind == "numbered_list":
        for i, item in enumerate(block.get("items", []), 1):
            out.append(Paragraph(f"{i}. {item}", S["bullet"]))
    elif kind == "note":
        out.append(note_box(block["text"]))
    elif kind == "key":
        out.append(key_box(block["text"]))
    elif kind == "code":
        out.extend(code_block(block.get("content", ""), block.get("label")))
    elif kind == "table":
        rows = [tuple(r) for r in block.get("rows", [])]
        cw = None
        if block.get("col_widths_mm"):
            cw = [w * mm for w in block["col_widths_mm"]]
        out.append(two_col_table(rows, header=block.get("header"), col_widths=cw))
    elif kind == "table_3col":
        rows = [tuple(r) for r in block.get("rows", [])]
        cw = None
        if block.get("col_widths_mm"):
            cw = [w * mm for w in block["col_widths_mm"]]
        out.append(three_col_table(rows, header=block.get("header"), col_widths=cw))
    elif kind == "compare_table":
        rows = [tuple(r) for r in block.get("rows", [])]
        cw = None
        if block.get("col_widths_mm"):
            cw = [w * mm for w in block["col_widths_mm"]]
        out.append(compare_table(block["header"], rows, col_widths=cw))
    elif kind == "spacer":
        out.append(_spacer(block.get("height_mm", 4)))
    elif kind == "page_break":
        out.append(PageBreak())
    elif kind == "exam_trap":
        out.append(Paragraph(f"⚠ {block['text']}", S["bullet"]))
    elif kind == "blocks":
        for child in block.get("items", []):
            out.extend(render_block(child))

    return out


def build_cover(story: list, doc_data: dict[str, Any]) -> None:
    title = doc_data.get("title", "Study Guide")
    subtitle = doc_data.get("subtitle", "Detailed Study Notes")
    scope = doc_data.get("scope", "")
    focus = doc_data.get("focus_areas", "")

    cover = Table([[Paragraph(title.upper(), S["cover_title"])]], colWidths=[W - 36 * mm])
    cover.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), DARK_BG),
                ("TOPPADDING", (0, 0), (-1, -1), 30),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ]
        )
    )
    story.append(cover)

    sub_tbl = Table([[Paragraph(subtitle, S["cover_sub"])]], colWidths=[W - 36 * mm])
    sub_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), DARK_BG),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ]
        )
    )
    story.append(sub_tbl)

    if scope:
        scope_tbl = Table([[Paragraph(scope, S["cover_sub"])]], colWidths=[W - 36 * mm])
        scope_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), BLUE),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                    ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ]
            )
        )
        story.append(scope_tbl)

    story.append(_spacer(10))

    if focus:
        focus_style = ParagraphStyle(
            "fh",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=ACCENT,
        )
        ft = Table(
            [
                [Paragraph("<b>🎯 Focus Areas</b>", focus_style)],
                [Paragraph(focus, S["body"])],
            ],
            colWidths=[W - 36 * mm],
        )
        ft.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f7f9ff")),
                    ("BOX", (0, 0), (-1, -1), 1.5, ACCENT),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(ft)

    story.append(PageBreak())


def build_chapter(story: list, chapter: dict[str, Any]) -> None:
    story.append(chapter_header(chapter["title"]))
    story.append(_spacer(4))
    for block in chapter.get("blocks", []):
        story.extend(render_block(block))


def build_appendix(story: list, appendix: dict[str, Any]) -> None:
    if appendix.get("cheat_sheet_title"):
        story.append(chapter_header(appendix["cheat_sheet_title"]))
        story.append(_spacer(4))

    for block in appendix.get("blocks", []):
        story.extend(render_block(block))

    traps = appendix.get("exam_traps", [])
    if traps:
        story.append(Paragraph("Common Exam Traps & Pitfalls", S["section"]))
        for trap in traps:
            story.append(Paragraph(f"⚠ {trap}", S["bullet"]))

    closing = appendix.get("closing_message", "Good luck! 🎯")
    footer = appendix.get("footer_text", "")
    story.append(_spacer(6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT))
    story.append(_spacer(3))
    story.append(
        Paragraph(
            closing,
            ParagraphStyle(
                "good",
                fontName="Helvetica-Bold",
                fontSize=12,
                textColor=ACCENT,
                alignment=TA_CENTER,
            ),
        )
    )
    if footer:
        story.append(
            Paragraph(
                footer,
                ParagraphStyle(
                    "footer",
                    fontName="Helvetica",
                    fontSize=8,
                    textColor=GRAY,
                    alignment=TA_CENTER,
                ),
            )
        )


def render_pdf(doc_data: dict[str, Any], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=doc_data.get("title", "Study Guide"),
    )

    story: list = []
    build_cover(story, doc_data)

    for chapter in doc_data.get("chapters", []):
        build_chapter(story, chapter)
        if chapter.get("page_break_after", True):
            story.append(PageBreak())

    appendix = doc_data.get("appendix")
    if appendix:
        build_appendix(story, appendix)

    doc.build(story)
    return output_path


def render_pdf_from_json(json_path: str | Path, output_path: str | Path) -> Path:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    return render_pdf(data, output_path)
