"""Background job runner."""

from __future__ import annotations

import asyncio
import os
import threading
import traceback
from typing import Any

import httpx

from app import database as db
from app.config import IS_VERCEL
from app.database import init_db
from app.services.key_rotator import KeyRotator
from app.services.checkpoint import can_resume_job
from app.services.pipeline import StudyGuidePipeline

init_db()

_rotator: KeyRotator | None = None
_running: dict[str, asyncio.Task] = {}


def get_rotator() -> KeyRotator:
    global _rotator
    if _rotator is None:
        _rotator = KeyRotator()
    else:
        _rotator.reload()
    return _rotator


def _internal_job_secret() -> str:
    return os.environ.get("INTERNAL_JOB_SECRET", "").strip()


def _vercel_base_url() -> str:
    url = os.environ.get("VERCEL_URL", "").strip()
    if not url:
        return ""
    if not url.startswith("http"):
        url = f"https://{url}"
    return url.rstrip("/")


def _fire_vercel_job(job_id: str, resume: bool) -> None:
    """Kick off job processing in a separate serverless invocation."""
    base = _vercel_base_url()
    secret = _internal_job_secret()
    if not base or not secret:
        db.add_job_log(
            job_id,
            "Job runner misconfigured — set INTERNAL_JOB_SECRET on Vercel",
            "error",
        )
        db.update_job(
            job_id,
            status="failed",
            error="INTERNAL_JOB_SECRET is not configured",
            message="Failed — server misconfiguration",
        )
        return

    try:
        with httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=1.0, write=10.0, pool=10.0),
        ) as client:
            client.post(
                f"{base}/api/internal/run-job",
                json={"job_id": job_id, "resume": resume},
                headers={"Authorization": f"Bearer {secret}"},
            )
    except httpx.ReadTimeout:
        # Expected — the worker invocation continues after we disconnect.
        pass
    except Exception as exc:
        db.add_job_log(job_id, f"Failed to start worker: {exc}", "error")


async def run_job(job_id: str, resume: bool = False) -> None:
    if job_id in _running and not _running[job_id].done():
        return

    try:
        job = db.get_job(job_id)
        if resume:
            if not can_resume_job(job_id, job["status"]):
                db.add_job_log(job_id, "Resume rejected — no checkpoint", "error")
                return
            db.update_job(job_id, status="running", error=None, message="Resuming from checkpoint…")
            db.add_job_log(job_id, "Job resumed from checkpoint")
            db.log_activity("job_resumed", f"Resumed: {job['title']}", {"job_id": job_id})
        else:
            db.update_job(job_id, status="running", progress=0, message="Starting…", error=None)
            db.add_job_log(job_id, "Job started")
            db.log_activity("job_started", f"Job started: {job['title']}", {"job_id": job_id})

        rotator = get_rotator()
        if not rotator.has_keys:
            from app.services.job_progress import JobProgress

            prog = JobProgress(job_id)
            prog.fail("No Gemini API keys configured.", "pending")
            db.update_job(
                job_id,
                status="failed",
                error="No Gemini API keys configured.",
                message="Failed — no API keys",
            )
            db.log_activity("job_failed", "Job failed: no API keys", {"job_id": job_id})
            return

        pipeline = StudyGuidePipeline(rotator)
        await pipeline.run(
            job_id=job_id,
            title=job["title"],
            source_paths=job["source_files"],
            extra_context=job.get("extra_context") or "",
            resume=resume,
        )
    except Exception as exc:
        from app.services.job_progress import JobProgress

        job = db.get_job(job_id)
        tb = traceback.format_exc()
        prog = JobProgress(job_id)
        prog.fail(str(exc))
        db.update_job(
            job_id,
            status="failed",
            error=str(exc),
            message=f"Failed at step: {prog.stats.get('error_step', 'unknown')}",
            finished_at=prog.stats.get("finished_at"),
        )
        db.add_job_log(job_id, f"Error: {exc}", "error")
        db.add_job_log(job_id, tb, "error")
        db.log_activity("job_failed", f"Job failed: {job['title']} — {exc}", {"job_id": job_id})
    finally:
        _running.pop(job_id, None)


def start_job(job_id: str, resume: bool = False) -> None:
    if job_id in _running and not _running[job_id].done():
        return

    if IS_VERCEL:
        threading.Thread(
            target=_fire_vercel_job,
            args=(job_id, resume),
            daemon=True,
        ).start()
        return

    task = asyncio.create_task(run_job(job_id, resume=resume))
    _running[job_id] = task


def resume_job(job_id: str) -> bool:
    """Start a failed job from its last checkpoint. Returns False if not resumable."""
    job = db.get_job(job_id)
    if not can_resume_job(job_id, job["status"]):
        return False
    start_job(job_id, resume=True)
    return True


def job_status_snapshot() -> dict[str, Any]:
    return {
        "active_jobs": [jid for jid, t in _running.items() if not t.done()],
        "keys_loaded": get_rotator().key_count,
        "vercel": IS_VERCEL,
    }
