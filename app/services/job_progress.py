"""Structured job progress and stats tracking."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app import database as db


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _elapsed(started_at: str | None) -> int | None:
    if not started_at:
        return None
    try:
        start = datetime.fromisoformat(started_at)
        return max(0, int((datetime.now(timezone.utc) - start).total_seconds()))
    except ValueError:
        return None


def _default_steps() -> list[dict[str, Any]]:
    return [
        {"id": "extract", "label": "Extract text from files", "status": "pending"},
        {"id": "outline", "label": "Generate outline (Gemini)", "status": "pending"},
        {"id": "appendix", "label": "Cheat sheet & exam traps", "status": "pending"},
        {"id": "render", "label": "Render PDF (ReportLab)", "status": "pending"},
    ]


class JobProgress:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.stats = self._load()

    def _load(self) -> dict[str, Any]:
        job = db.get_job(self.job_id)
        raw = job.get("stats_json")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return {
            "current_step": "pending",
            "started_at": None,
            "finished_at": None,
            "api_calls": 0,
            "source_chars": 0,
            "chapters_total": 0,
            "chapters_done": 0,
            "source_file_names": [],
            "steps": [],
        }

    def _save(self, message: str | None = None, progress: float | None = None) -> None:
        self.stats["elapsed_seconds"] = _elapsed(self.stats.get("started_at"))
        fields: dict[str, Any] = {"stats_json": json.dumps(self.stats)}
        if message is not None:
            fields["message"] = message
        if progress is not None:
            fields["progress"] = progress
        db.update_job(self.job_id, **fields)

    def _ensure_base_steps(self) -> None:
        """Guarantee extract/outline/appendix/render skeleton exists (fixes resume StopIteration)."""
        steps = self.stats.get("steps") or []
        ids = {s.get("id") for s in steps}
        if {"extract", "outline", "appendix", "render"}.issubset(ids):
            return

        preserved = {s["id"]: s for s in steps if s.get("id")}
        rebuilt = []
        for template in _default_steps():
            sid = template["id"]
            if sid in preserved:
                rebuilt.append(preserved[sid])
            else:
                rebuilt.append(dict(template))

        # Keep any chapter steps that were already present
        chapter_steps = [s for s in steps if str(s.get("id", "")).startswith("chapter_")]
        if chapter_steps:
            outline_i = next(i for i, s in enumerate(rebuilt) if s["id"] == "outline")
            appendix_i = next(i for i, s in enumerate(rebuilt) if s["id"] == "appendix")
            rebuilt = rebuilt[: appendix_i] + chapter_steps + rebuilt[appendix_i:]

        self.stats["steps"] = rebuilt
        if not self.stats.get("started_at"):
            self.stats["started_at"] = _utcnow()

    def start(self, source_file_names: list[str]) -> None:
        self.stats["started_at"] = _utcnow()
        self.stats["source_file_names"] = source_file_names
        self.stats["steps"] = _default_steps()
        self._step("extract", "running")
        self._save("Extracting text from files…", 2)

    def set_source_chars(self, n: int) -> None:
        self.stats["source_chars"] = n
        self._save()

    def finish_extract(self) -> None:
        self._ensure_base_steps()
        self._step("extract", "done")
        self._step("outline", "running")
        self._save("Generating document outline…", 8)

    def finish_outline(self, chapters: list[dict[str, Any]]) -> None:
        self._ensure_base_steps()
        self._step("outline", "done")
        self.stats["chapters_total"] = len(chapters)

        base = self.stats["steps"]
        if any(s.get("id", "").startswith("chapter_") for s in base):
            self._save(f"Outline ready — {len(chapters)} chapters", 12)
            return

        chapter_steps = [
            {
                "id": f"chapter_{i + 1}",
                "label": ch.get("title", f"Chapter {i + 1}"),
                "status": "pending",
            }
            for i, ch in enumerate(chapters)
        ]

        appendix_idx = next(
            (i for i, s in enumerate(base) if s.get("id") == "appendix"),
            len(base),
        )
        self.stats["steps"] = base[:appendix_idx] + chapter_steps + base[appendix_idx:]
        if chapter_steps:
            self._step(chapter_steps[0]["id"], "running")
        self._save(f"Outline ready — {len(chapters)} chapters", 12)

    def start_chapter(self, index: int, title: str, progress: float) -> None:
        self._ensure_base_steps()
        step_id = f"chapter_{index + 1}"
        self.stats["current_step"] = step_id
        self._step(step_id, "running", label=title)
        self._save(f"Writing {title}…", progress)

    def finish_chapter(self, index: int) -> None:
        step_id = f"chapter_{index + 1}"
        self._step(step_id, "done")
        self.stats["chapters_done"] = index + 1
        self._save()

    def start_appendix(self) -> None:
        self._ensure_base_steps()
        self.stats["current_step"] = "appendix"
        self._step("appendix", "running")
        self._save("Writing cheat sheet & exam traps…", 85)

    def finish_appendix(self) -> None:
        self._ensure_base_steps()
        self._step("appendix", "done")
        self._step("render", "running")
        self._save("Rendering PDF…", 92)

    def finish_render(self, pdf_name: str) -> None:
        self._ensure_base_steps()
        self._step("render", "done")
        self.stats["current_step"] = "completed"
        self.stats["finished_at"] = _utcnow()
        self.stats["pdf_filename"] = pdf_name
        self.stats["elapsed_seconds"] = _elapsed(self.stats.get("started_at"))
        self._save("Complete", 100)

    def increment_api_calls(self) -> None:
        self.stats["api_calls"] = self.stats.get("api_calls", 0) + 1
        self._save()

    def fail(self, error: str, step_id: str | None = None) -> None:
        self._ensure_base_steps()
        sid = step_id or self.stats.get("current_step")
        if sid:
            self._step(sid, "failed", error=error)
        self.stats["finished_at"] = _utcnow()
        self.stats["elapsed_seconds"] = _elapsed(self.stats.get("started_at"))
        self.stats["error_step"] = sid
        self._save("Failed", self.stats.get("progress", 0))

    def begin_resume(self, checkpoint: dict[str, Any]) -> None:
        """Reset failed state and sync step statuses from checkpoint files."""
        self._ensure_base_steps()
        self.stats["finished_at"] = None
        self.stats.pop("error_step", None)

        for step in self.stats.get("steps", []):
            if step.get("status") == "failed":
                step["status"] = "pending"
                step.pop("error", None)
                step.pop("finished_at", None)

        outline = checkpoint.get("outline")
        chapters = outline.get("chapters", []) if outline else []
        has_chapter_steps = any(
            s.get("id", "").startswith("chapter_") for s in self.stats.get("steps", [])
        )

        if outline and chapters and not has_chapter_steps:
            self.finish_outline(chapters)

        if checkpoint.get("has_source"):
            self._step("extract", "done")
            if not self.stats.get("source_chars") and checkpoint.get("source_path"):
                try:
                    text = checkpoint["source_path"].read_text(encoding="utf-8")
                    self.stats["source_chars"] = len(text)
                except OSError:
                    pass

        if checkpoint.get("has_outline"):
            self._step("outline", "done")

        for n in checkpoint.get("chapters_done", []):
            self._step(f"chapter_{n}", "done")

        self.stats["chapters_done"] = len(checkpoint.get("chapters_done", []))
        self.stats["chapters_total"] = checkpoint.get("chapters_total", 0) or len(chapters)

        if checkpoint.get("has_appendix"):
            self._step("appendix", "done")

        next_step = checkpoint.get("next_step", "extract")
        if next_step == "render":
            self._step("render", "running")
        elif next_step.startswith("chapter_"):
            self._step(next_step, "running")
        elif next_step == "appendix":
            self._step("appendix", "running")
        elif next_step == "outline":
            self._step("outline", "running")
        elif next_step == "extract":
            self._step("extract", "running")

        self.stats["current_step"] = next_step
        self.stats["resumed_at"] = _utcnow()
        self._save(f"Resuming from {next_step}…", self.stats.get("progress", 0))

    def _step(
        self,
        step_id: str,
        status: str,
        label: str | None = None,
        error: str | None = None,
    ) -> None:
        self._ensure_base_steps()
        now = _utcnow()
        found = False
        for step in self.stats["steps"]:
            if step.get("id") != step_id:
                continue
            found = True
            if label:
                step["label"] = label
            if status == "running":
                step["status"] = "running"
                step["started_at"] = now
                self.stats["current_step"] = step_id
            elif status == "done":
                step["status"] = "done"
                step["finished_at"] = now
            elif status == "failed":
                step["status"] = "failed"
                step["finished_at"] = now
                step["error"] = error
            else:
                step["status"] = status
            break

        if not found and step_id.startswith("chapter_"):
            entry: dict[str, Any] = {
                "id": step_id,
                "label": label or step_id,
                "status": status,
            }
            if status == "done":
                entry["finished_at"] = now
            appendix_idx = next(
                (i for i, s in enumerate(self.stats["steps"]) if s.get("id") == "appendix"),
                len(self.stats["steps"]),
            )
            self.stats["steps"].insert(appendix_idx, entry)

        self._save()
