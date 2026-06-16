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
    GEMINI_MODEL_FALLBACKS,
    GROK_INTER_REQUEST_DELAY,
    GROK_MODEL_FALLBACKS,
    OPENROUTER_INTER_REQUEST_DELAY,
    OPENROUTER_MODEL_FALLBACKS,
    JOBS_DIR,
    OUTPUTS_DIR,
)
from app.services.checkpoint import scan_checkpoint
from app.services.detail_tiers import (
    appendix_tier_addon,
    chapter_tier_addon,
    get_tier_config,
    master_plan_tier_addon,
    normalize_detail_tier,
    section_tier_addon,
    outline_tier_addon,
)
from app.services.gemini import load_prompt
from app.services.job_progress import JobProgress
from app.services.key_rotator import KeyRotator
from app.services.llm_client import LLMClient, get_active_provider
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


def _merge_section_blocks(chapter_title: str, sections: list[dict[str, Any]]) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    for sec in sections:
        title = sec.get("section_title") or sec.get("title", "")
        if title:
            blocks.append({"type": "section", "title": title})
        blocks.extend(sec.get("blocks", []))
        blocks.append({"type": "spacer", "height_mm": 3})
    return {
        "title": chapter_title,
        "page_break_after": True,
        "blocks": blocks,
    }


class StudyGuidePipeline:
    def __init__(self, rotator: KeyRotator, provider: str | None = None):
        self.provider = provider or rotator.provider or get_active_provider()
        self.llm = LLMClient(rotator, self.provider)
        self.outline_prompt = load_prompt("outline")
        self.chapter_prompt = load_prompt("chapter")
        self.appendix_prompt = load_prompt("appendix")
        self.master_plan_prompt = load_prompt("master_plan")
        self.chapter_section_prompt = load_prompt("chapter_section")
        self.model_outline = self.llm.model_outline
        self.model_chapter = self.llm.model_chapter

    async def _llm_call(
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

        delays = {
            "openrouter": OPENROUTER_INTER_REQUEST_DELAY,
            "grok": GROK_INTER_REQUEST_DELAY,
        }
        delay = delays.get(self.provider, GEMINI_INTER_REQUEST_DELAY)
        if delay > 0:
            await asyncio.sleep(delay)

        result = await self.llm.generate_json(
            prompt=prompt,
            system=system,
            model_name=model_name,
            temperature=temperature,
            on_wait=on_wait,
        )
        prog.increment_api_calls()
        return result

    async def _generate_chapter_single(
        self,
        prog: JobProgress,
        ch_plan: dict[str, Any],
        document: dict[str, Any],
        source_text: str,
        tier_cfg: Any,
        _log: LogFn,
    ) -> dict[str, Any]:
        excerpt = _relevant_excerpt(
            source_text,
            ch_plan.get("summary", ""),
            max_chars=tier_cfg.excerpt_chars,
        )
        priority = ch_plan.get("priority", "normal")
        chapter_user = (
            f"CHAPTER PLAN:\n{json.dumps(ch_plan, indent=2)}\n\n"
            f"DOCUMENT TITLE: {document['title']}\n"
            f"PRIORITY: {priority}\n\n"
            f"RELEVANT SOURCE EXCERPTS:\n{excerpt}"
        )
        system = self.chapter_prompt + chapter_tier_addon(tier_cfg, priority)
        temp = tier_cfg.chapter_temp + (0.05 if priority == "high" else 0)
        chapter = await self._llm_call(
            prog,
            chapter_user,
            system,
            self.model_chapter,
            temp,
            _log,
        )
        chapter.setdefault("title", ch_plan.get("title", "Chapter"))
        chapter.setdefault("page_break_after", True)
        return chapter

    async def _generate_chapter_comprehensive(
        self,
        prog: JobProgress,
        job_dir: Path,
        ch_num: int,
        ch_plan: dict[str, Any],
        document: dict[str, Any],
        source_text: str,
        tier_cfg: Any,
        done_sections: set[int],
        _log: LogFn,
    ) -> dict[str, Any]:
        sections_plan = ch_plan.get("sections") or []
        ch_title = ch_plan.get("title", f"Chapter {ch_num}")

        if not sections_plan:
            _log(f"Chapter {ch_num}: no section plan — falling back to single-pass generation", "warn")
            return await self._generate_chapter_single(
                prog, ch_plan, document, source_text, tier_cfg, _log
            )

        section_results: list[dict[str, Any]] = []
        total_secs = len(sections_plan)
        excerpt = _relevant_excerpt(
            source_text,
            ch_plan.get("summary", "") + " " + " ".join(
                c for s in sections_plan for c in s.get("key_concepts", [])
            ),
            max_chars=tier_cfg.excerpt_chars,
        )

        for sec_idx, sec_plan in enumerate(sections_plan):
            sec_num = sec_idx + 1
            sec_path = job_dir / f"chapter_{ch_num}_sec_{sec_num}.json"

            if sec_num in done_sections and sec_path.exists():
                section_results.append(json.loads(sec_path.read_text(encoding="utf-8")))
                continue

            _log(f"  Section {sec_num}/{total_secs}: {sec_plan.get('title', sec_plan.get('id', ''))}")
            section_user = (
                f"SECTION PLAN:\n{json.dumps(sec_plan, indent=2)}\n\n"
                f"CHAPTER CONTEXT:\n{json.dumps({'title': ch_title, 'summary': ch_plan.get('summary', '')}, indent=2)}\n\n"
                f"DOCUMENT TITLE: {document['title']}\n\n"
                f"RELEVANT SOURCE EXCERPTS:\n{excerpt}"
            )
            system = self.chapter_section_prompt + section_tier_addon(tier_cfg)
            section = await self._llm_call(
                prog,
                section_user,
                system,
                self.model_chapter,
                tier_cfg.chapter_temp,
                _log,
            )
            section.setdefault("section_title", sec_plan.get("title", f"Section {sec_num}"))
            sec_path.write_text(json.dumps(section, indent=2), encoding="utf-8")
            section_results.append(section)

        return _merge_section_blocks(ch_title, section_results)

    async def run(
        self,
        job_id: str,
        title: str,
        source_paths: list[str],
        extra_context: str = "",
        detail_tier: str | None = None,
        log: LogFn | None = None,
        resume: bool = False,
    ) -> dict[str, Any]:
        job_dir = JOBS_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        tier = normalize_detail_tier(detail_tier)
        tier_cfg = get_tier_config(tier)
        (job_dir / "detail_tier.txt").write_text(tier, encoding="utf-8")
        prog = JobProgress(job_id)
        if resume:
            if not prog.stats.get("steps"):
                prog.configure_tier(tier_cfg.use_master_plan)
        else:
            prog.configure_tier(tier_cfg.use_master_plan)
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

        _log(f"Detail tier: {tier_cfg.label} ({tier_cfg.id})")

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

        fallbacks_map = {
            "openrouter": OPENROUTER_MODEL_FALLBACKS,
            "grok": GROK_MODEL_FALLBACKS,
        }
        fallbacks = fallbacks_map.get(self.provider, GEMINI_MODEL_FALLBACKS)
        _log(f"Using provider: {self.provider} · model: {self.model_outline} (fallbacks: {', '.join(fallbacks)})")

        outline: dict[str, Any]

        # ── Master plan (detailed / comprehensive) ──────────────────────────
        if tier_cfg.use_master_plan:
            if resume and checkpoint["has_master_plan"] and checkpoint["master_plan"]:
                outline = checkpoint["master_plan"]
                _log(f"Loaded cached master plan ({len(outline.get('chapters', []))} chapters)")
                if not prog.stats.get("chapters_total"):
                    prog.stats["chapters_total"] = len(outline.get("chapters", []))
                    prog._save()
            else:
                prog.start_master_plan()
                source_for_plan = _truncate_source(source_text)
                _log(f"Calling {self.provider} for master plan ({tier_cfg.label})")
                master_user = (
                    f"Document title hint: {title}\n\n"
                    f"SOURCE MATERIAL:\n{source_for_plan}"
                )
                system = self.master_plan_prompt + master_plan_tier_addon(tier_cfg, extra_context)
                outline = await self._llm_call(
                    prog,
                    master_user,
                    system,
                    self.model_outline,
                    tier_cfg.outline_temp,
                    _log,
                )
                (job_dir / "master_plan.json").write_text(
                    json.dumps(outline, indent=2), encoding="utf-8"
                )
                db.update_job(job_id, outline_json=json.dumps(outline))
                (job_dir / "outline.json").write_text(json.dumps(outline, indent=2), encoding="utf-8")
                chapters_plan = outline.get("chapters", [])
                prog.finish_master_plan(chapters_plan)
                _log(f"Master plan ready: {len(chapters_plan)} chapters, section-level structure")
        else:
            # ── Outline (concise / standard) ────────────────────────────────
            if resume and checkpoint["has_outline"] and checkpoint["outline"]:
                outline = checkpoint["outline"]
                _log(f"Loaded cached outline ({len(outline.get('chapters', []))} chapters)")
                if not prog.stats.get("chapters_total"):
                    prog.stats["chapters_total"] = len(outline.get("chapters", []))
                    prog._save()
            else:
                source_for_outline = _truncate_source(source_text)
                _log(f"Calling {self.provider} for outline")
                outline = await self._llm_call(
                    prog,
                    f"Document title hint: {title}\n\nSOURCE MATERIAL:\n{source_for_outline}",
                    self.outline_prompt + outline_tier_addon(tier_cfg),
                    self.model_outline,
                    tier_cfg.outline_temp,
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
            "subtitle": outline.get("subtitle", tier_cfg.subtitle_suffix),
            "scope": outline.get("scope", ""),
            "focus_areas": outline.get("focus_areas", ""),
            "detail_tier": tier,
            "chapters": [],
        }
        if outline.get("learning_objectives"):
            document["learning_objectives"] = outline["learning_objectives"]

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

            if tier_cfg.split_chapters:
                done_sections = set(checkpoint.get("chapter_sections_done", {}).get(ch_num, []))
                chapter = await self._generate_chapter_comprehensive(
                    prog,
                    job_dir,
                    ch_num,
                    ch_plan,
                    document,
                    source_text,
                    tier_cfg,
                    done_sections,
                    _log,
                )
            else:
                chapter = await self._generate_chapter_single(
                    prog, ch_plan, document, source_text, tier_cfg, _log
                )

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
            appendix = await self._llm_call(
                prog,
                appendix_user,
                self.appendix_prompt + appendix_tier_addon(tier_cfg),
                self.model_chapter,
                tier_cfg.chapter_temp,
                _log,
            )
            appendix.setdefault(
                "cheat_sheet_title", appendix_plan.get("cheat_sheet_title", "Quick Reference")
            )
            appendix.setdefault("footer_text", f"{document['title']} — {tier_cfg.subtitle_suffix}")
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
        db.log_activity(
            "job_completed",
            f"Study guide ready ({tier_cfg.label}): {title}",
            {"job_id": job_id, "detail_tier": tier},
        )
        return document
