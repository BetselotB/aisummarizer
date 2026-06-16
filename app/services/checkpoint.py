"""Detect and load job checkpoints for resume."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import JOBS_DIR


def scan_checkpoint(job_id: str) -> dict[str, Any]:
    job_dir = JOBS_DIR / job_id
    if not job_dir.is_dir():
        return {"can_resume": False}

    source_path = job_dir / "source.txt"
    outline_path = job_dir / "outline.json"
    appendix_path = job_dir / "appendix.json"
    document_path = job_dir / "document.json"

    chapters_done: list[int] = []
    loaded_chapters: list[dict[str, Any]] = []
    for path in sorted(job_dir.glob("chapter_*.json")):
        try:
            num = int(path.stem.split("_")[1])
        except (IndexError, ValueError):
            continue
        chapters_done.append(num)
        loaded_chapters.append(json.loads(path.read_text(encoding="utf-8")))

    outline = None
    if outline_path.exists():
        outline = json.loads(outline_path.read_text(encoding="utf-8"))

    appendix = None
    if appendix_path.exists():
        appendix = json.loads(appendix_path.read_text(encoding="utf-8"))

    total_chapters = len(outline.get("chapters", [])) if outline else 0
    next_chapter = 1
    for i in range(1, total_chapters + 1):
        if i not in chapters_done:
            next_chapter = i
            break
    else:
        if total_chapters > 0 and len(chapters_done) >= total_chapters:
            next_chapter = total_chapters + 1

    if appendix_path.exists():
        next_step = "render" if document_path.exists() or loaded_chapters else "appendix"
    elif total_chapters and len(chapters_done) >= total_chapters:
        next_step = "appendix"
    elif outline_path.exists() and chapters_done:
        next_step = f"chapter_{next_chapter}"
    elif outline_path.exists():
        next_step = "chapter_1"
    elif source_path.exists():
        next_step = "outline"
    else:
        next_step = "extract"

    can_resume = (
        source_path.exists()
        or outline_path.exists()
        or bool(chapters_done)
        or appendix_path.exists()
    )

    return {
        "can_resume": can_resume,
        "has_source": source_path.exists(),
        "has_outline": outline_path.exists(),
        "has_appendix": appendix_path.exists(),
        "chapters_done": chapters_done,
        "chapters_loaded": loaded_chapters,
        "chapters_total": total_chapters,
        "next_chapter_index": next_chapter - 1 if next_chapter <= total_chapters else total_chapters,
        "next_step": next_step,
        "outline": outline,
        "appendix": appendix,
        "source_path": source_path,
    }


def can_resume_job(job_id: str, status: str) -> bool:
    if status != "failed":
        return False
    return scan_checkpoint(job_id)["can_resume"]
