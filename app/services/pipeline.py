"""End-to-end study guide generation pipeline."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Callable

from app import database as db
from app.config import (
    CHUNK_CHAR_LIMIT,
    GEMINI_INTER_REQUEST_DELAY,
    GEMINI_MODEL_CHAPTER,
    GEMINI_MODEL_FALLBACKS,
    GEMINI_MODEL_OUTLINE,
    JOBS_DIR,
    OUTPUTS_DIR,
)
from app.services.checkpoint import scan_checkpoint
from app.services.gemini import GeminiClient, load_prompt
from app.services.job_progress import JobProgress
from app.services.key_rotator import KeyRotator
from app.services.pdf_extract import extract_multiple
from template.render import render_pdf


LogFn = Callable[[str, str], None]
ProgressFn = Callable[[float, str], None]


def _truncate_source(text: str, limit: int = CHUNK_CHAR_LIMIT) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + "\n\n[... middle truncated for context window ...]\n\n" + text[-half:]


def _relevant_excerpt(full_source: str, chapter_summary: str, max_chars: int = 40_000) -> str:
    if len(full_source) <= max_chars:
        return full_source
    words = [w.lower() for w in chapter_summary.split() if len(w) > 4][:12]
    if not words:
        return _truncate_source(full_source, max_chars)
    lines = full_source.splitlines()
    scored: list[tuple[int, str]] = []
    for line in lines:
        lower = line.lower()
        score = sum(1 for w in words if w in lower)
        if score:
            scored.append((score, line))
    if not scored:
        return _truncate_source(full_source, max_chars)
    scored.sort(key=lambda x: -x[0])
    picked = [ln for _, ln in scored[:400]]
    excerpt = "\n".join(picked)
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars]
    return excerpt


class StudyGuidePipeline:
    def __init__(self, rotator: KeyRotator):
        self.gemini = GeminiClient(rotator)
        self.outline_prompt = load_prompt("outline")
        self.chapter_prompt = load_prompt("chapter")
        self.appendix_prompt = load_prompt("appendix")
        saved = db.get_app_state("gemini_model")
        self.model_outline = saved or GEMINI_MODEL_OUTLINE
        self.model_chapter = saved or GEMINI_MODEL_CHAPTER

    async def _gemini(
        self,
        prog: JobProgress,
        prompt: str,
        system: str,
        model_name: str,
        temperature: float,
        _log: LogFn | None,
    ) -> dict[str, Any]:
        async def on_wait(seconds: float, label: str) -> None:
            msg = f"{label} — waiting {seconds:.0f}s" if seconds > 0 else label
            prog._save(msg)
            if _log:
                _log(msg, "warn")

        if GEMINI_INTER_REQUEST_DELAY > 0:
            await asyncio.sleep(GEMINI_INTER_REQUEST_DELAY)

        result = await self.gemini.generate_json(
            prompt=prompt,
            system=system,
            model_name=model_name,
            temperature=temperature,
            on_wait=on_wait,
        )
        prog.increment_api_calls()
        return result

    async def run(
        self,
        job_id: str,
        title: str,
        source_paths: list[str],
        extra_context: str = "",
        log: LogFn | None = None,
        resume: bool = False,
    ) -> dict[str, Any]:
        job_dir = JOBS_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        prog = JobProgress(job_id)
        checkpoint = scan_checkpoint(job_id) if resume else {"can_resume": False}

        def _log(msg: str, level: str = "info") -> None:
            db.add_job_log(job_id, msg, level)
            if log:
                log(msg, level)

        file_names = [Path(p).name for p in source_paths]

        if resume:
            if not checkpoint["can_resume"]:
                raise ValueError("No checkpoint found — cannot resume this job.")
            _log(
                f"Resuming from {checkpoint['next_step']} "
                f"({len(checkpoint['chapters_done'])}/{checkpoint['chapters_total']} chapters saved)"
            )
            prog.begin_resume(checkpoint)
        else:
            prog.start(file_names)

        # ── Source text ─────────────────────────────────────────────────────
        if resume and checkpoint["has_source"]:
            source_text = checkpoint["source_path"].read_text(encoding="utf-8")
            _log(f"Loaded cached source ({len(source_text):,} chars)")
        else:
            _log("Extracting text from source files")
            source_text = extract_multiple(source_paths)
            if extra_context.strip():
                source_text = (
                    f"{source_text}\n\n===== ADDITIONAL CONTEXT =====\n{extra_context.strip()}"
                )
            if not source_text.strip():
                raise ValueError("No text could be extracted from the uploaded files.")
            prog.set_source_chars(len(source_text))
            prog.finish_extract()
            _log(f"Extracted {len(source_text):,} characters from {len(file_names)} file(s)")
            (job_dir / "source.txt").write_text(source_text, encoding="utf-8")

        if not resume or not checkpoint["has_source"]:
            prog.set_source_chars(len(source_text))

        _log(f"Using model: {self.model_outline} (fallbacks: {', '.join(GEMINI_MODEL_FALLBACKS)})")

        # ── Outline ─────────────────────────────────────────────────────────
        if resume and checkpoint["has_outline"] and checkpoint["outline"]:
            outline = checkpoint["outline"]
            _log(f"Loaded cached outline ({len(outline.get('chapters', []))} chapters)")
            if not prog.stats.get("chapters_total"):
                prog.stats["chapters_total"] = len(outline.get("chapters", []))
                prog._save()
        else:
            source_for_outline = _truncate_source(source_text)
            _log("Calling Gemini for outline")
            outline = await self._gemini(
                prog,
                f"Document title hint: {title}\n\nSOURCE MATERIAL:\n{source_for_outline}",
                self.outline_prompt,
                self.model_outline,
                0.3,
                _log,
            )
            db.update_job(job_id, outline_json=json.dumps(outline))
            (job_dir / "outline.json").write_text(json.dumps(outline, indent=2), encoding="utf-8")
            chapters_plan = outline.get("chapters", [])
            prog.finish_outline(chapters_plan)
            _log(f"Outline ready: {len(chapters_plan)} chapters")

        chapters_plan = outline.get("chapters", [])

        document: dict[str, Any] = {
            "title": outline.get("title", title),
            "subtitle": outline.get("subtitle", "Study Guide"),
            "scope": outline.get("scope", ""),
            "focus_areas": outline.get("focus_areas", ""),
            "chapters": [],
        }

        # Load completed chapters from checkpoint files
        if resume and checkpoint["chapters_loaded"]:
            document["chapters"] = list(checkpoint["chapters_loaded"])
            _log(f"Loaded {len(document['chapters'])} saved chapter(s) from disk")

        total = max(len(chapters_plan), 1)
        done_set = set(checkpoint.get("chapters_done", [])) if resume else set()

        for idx, ch_plan in enumerate(chapters_plan):
            ch_num = idx + 1
            if ch_num in done_set and idx < len(document["chapters"]):
                continue

            pct = 12 + (68 * idx / total)
            ch_title = ch_plan.get("title", f"Chapter {ch_num}")
            prog.start_chapter(idx, ch_title, pct)
            _log(f"Generating chapter {ch_num}/{total}: {ch_title}")

            excerpt = _relevant_excerpt(source_text, ch_plan.get("summary", ""))
            priority = ch_plan.get("priority", "normal")
            chapter_user = (
                f"CHAPTER PLAN:\n{json.dumps(ch_plan, indent=2)}\n\n"
                f"DOCUMENT TITLE: {document['title']}\n"
                f"PRIORITY: {priority}\n\n"
                f"RELEVANT SOURCE EXCERPTS:\n{excerpt}"
            )
            temp = 0.45 if priority == "high" else 0.35
            chapter = await self._gemini(
                prog,
                chapter_user,
                self.chapter_prompt,
                self.model_chapter,
                temp,
                _log,
            )
            chapter.setdefault("title", ch_title)
            chapter.setdefault("page_break_after", True)

            if idx < len(document["chapters"]):
                document["chapters"][idx] = chapter
            else:
                document["chapters"].append(chapter)

            prog.finish_chapter(idx)
            (job_dir / f"chapter_{ch_num}.json").write_text(
                json.dumps(chapter, indent=2), encoding="utf-8"
            )
            _log(f"Chapter {ch_num} complete")

        # ── Appendix ────────────────────────────────────────────────────────
        if resume and checkpoint["has_appendix"] and checkpoint["appendix"]:
            appendix = checkpoint["appendix"]
            document["appendix"] = appendix
            _log("Loaded cached appendix")
        else:
            prog.start_appendix()
            _log("Generating appendix")
            appendix_plan = outline.get("appendix_plan", {})
            appendix_user = (
                f"FULL OUTLINE:\n{json.dumps(outline, indent=2)}\n\n"
                f"SOURCE SUMMARY (truncated):\n{_truncate_source(source_text, 60_000)}"
            )
            appendix = await self._gemini(
                prog,
                appendix_user,
                self.appendix_prompt,
                self.model_chapter,
                0.35,
                _log,
            )
            appendix.setdefault(
                "cheat_sheet_title", appendix_plan.get("cheat_sheet_title", "Quick Reference")
            )
            appendix.setdefault("footer_text", f"{document['title']} — Study Guide")
            document["appendix"] = appendix
            prog.finish_appendix()
            (job_dir / "appendix.json").write_text(json.dumps(appendix, indent=2), encoding="utf-8")

        doc_path = job_dir / "document.json"
        doc_path.write_text(json.dumps(document, indent=2), encoding="utf-8")
        db.update_job(job_id, document_json=json.dumps(document))

        _log("Rendering PDF with ReportLab")
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in title)[:80]
        pdf_path = OUTPUTS_DIR / f"{job_id}_{safe_name.strip()}.pdf"
        render_pdf(document, pdf_path)

        prog.finish_render(pdf_path.name)
        _log(f"PDF saved: {pdf_path.name}")
        db.update_job(
            job_id,
            pdf_path=str(pdf_path),
            status="completed",
            error=None,
            started_at=prog.stats.get("started_at"),
            finished_at=prog.stats.get("finished_at"),
        )
        db.log_activity("job_completed", f"Study guide ready: {title}", {"job_id": job_id})
        return document
