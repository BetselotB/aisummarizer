"""FastAPI application — AI Study Guide Generator."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import database as db
from app.config import BASE_DIR, JOBS_DIR, UPLOADS_DIR, GEMINI_MODEL_FALLBACKS, GEMINI_MODEL_OUTLINE
from app.database import init_db
from app.services.job_runner import get_rotator, job_status_snapshot, resume_job, run_job, start_job
from app.services.checkpoint import can_resume_job, scan_checkpoint
from app.services.key_validation import validate_gemini_api_key

init_db()

app = FastAPI(title="AI Study Guide Generator", version="1.0.0")
STATIC_DIR = BASE_DIR / "app" / "static"
DIST_DIR = STATIC_DIR / "dist"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _index_html() -> Path:
    built = DIST_DIR / "index.html"
    if built.exists():
        return built
    return STATIC_DIR / "index.html"


@app.get("/", response_class=HTMLResponse)
async def index():
    return _index_html().read_text(encoding="utf-8")


class ApiKeyCreate(BaseModel):
    label: str = ""
    api_key: str = Field(min_length=10)


class ApiKeyToggle(BaseModel):
    enabled: bool


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    extra_context: str = ""


@app.get("/api/health")
async def health():
    rotator = get_rotator()
    model = db.get_app_state("gemini_model") or GEMINI_MODEL_OUTLINE
    return {
        "status": "ok",
        "gemini_keys": rotator.key_count,
        "gemini_model": model,
        "model_fallbacks": GEMINI_MODEL_FALLBACKS,
        **job_status_snapshot(),
    }


@app.get("/api/config")
async def get_config():
    return {
        "gemini_model": db.get_app_state("gemini_model") or GEMINI_MODEL_OUTLINE,
        "model_options": [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ],
        "model_fallbacks": GEMINI_MODEL_FALLBACKS,
    }


@app.put("/api/config")
async def put_config(body: dict):
    model = body.get("gemini_model")
    if model:
        db.set_app_state("gemini_model", model)
        db.log_activity("config", f"Model set to {model}")
    return {"ok": True, "gemini_model": db.get_app_state("gemini_model")}


@app.get("/api/keys")
async def list_keys():
    return {"keys": db.list_api_keys()}


@app.post("/api/keys")
async def add_key(body: ApiKeyCreate):
    key = body.api_key.strip()
    err = validate_gemini_api_key(key)
    if err:
        raise HTTPException(400, err)
    row = db.add_api_key(body.label.strip() or "Gemini Key", key)
    get_rotator().reload()
    return {"key": {k: row[k] for k in ("id", "label", "masked_key", "enabled", "created_at")}}


@app.post("/api/keys/bulk")
async def add_keys_bulk(body: dict):
    """Add multiple keys at once — one per line in `keys_text`."""
    raw = body.get("keys_text", "")
    label_prefix = body.get("label_prefix", "Gemini")
    added = []
    rejected = []
    for i, line in enumerate(raw.splitlines(), 1):
        key = line.strip()
        if not key or key.startswith("#"):
            continue
        err = validate_gemini_api_key(key)
        if err:
            rejected.append({"line": i, "preview": key[:12] + "…", "reason": err})
            continue
        row = db.add_api_key(f"{label_prefix} {i}", key)
        added.append(row["id"])
    get_rotator().reload()
    return {"added": len(added), "ids": added, "rejected": rejected}


@app.delete("/api/keys/{key_id}")
async def remove_key(key_id: str):
    try:
        db.delete_api_key(key_id)
    except KeyError:
        raise HTTPException(404, "Key not found")
    get_rotator().reload()
    return {"ok": True}


@app.patch("/api/keys/{key_id}")
async def patch_key(key_id: str, body: ApiKeyToggle):
    try:
        db.toggle_api_key(key_id, body.enabled)
    except KeyError:
        raise HTTPException(404, "Key not found")
    get_rotator().reload()
    return {"ok": True}


@app.get("/api/jobs")
async def list_jobs():
    jobs = db.list_jobs()
    for j in jobs:
        j["can_resume"] = can_resume_job(j["id"], j["status"])
        if j["can_resume"]:
            cp = scan_checkpoint(j["id"])
            j["resume_from"] = cp["next_step"]
            j["chapters_saved"] = len(cp["chapters_done"])
            if cp["chapters_total"]:
                j["chapters_total"] = cp["chapters_total"]
    return {"jobs": jobs}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    try:
        job = db.get_job(job_id)
    except KeyError:
        raise HTTPException(404, "Job not found")
    job.pop("document_json", None)
    job.pop("outline_json", None)
    return {"job": job}


@app.get("/api/jobs/{job_id}/logs")
async def get_job_logs(job_id: str):
    try:
        db.get_job(job_id)
    except KeyError:
        raise HTTPException(404, "Job not found")
    return {"logs": db.get_job_logs(job_id)}


@app.get("/api/state")
async def get_state():
    return {"state": db.get_all_app_state()}


@app.put("/api/state")
async def put_state(body: dict):
    state = body.get("state", body)
    if not isinstance(state, dict):
        raise HTTPException(400, "Expected state object")
    for key, value in state.items():
        db.set_app_state(str(key), value)
    return {"ok": True, "keys": list(state.keys())}


@app.get("/api/activity")
async def get_activity(limit: int = 80):
    return {"activity": db.list_activity(limit=limit)}


@app.post("/api/activity")
async def post_activity(body: dict):
    kind = body.get("kind", "ui")
    message = body.get("message", "")
    if not message:
        raise HTTPException(400, "message required")
    db.log_activity(kind, message, body.get("meta"))
    return {"ok": True}


@app.get("/api/jobs/{job_id}/document.json")
async def download_json(job_id: str):
    try:
        job = db.get_job(job_id)
    except KeyError:
        raise HTTPException(404, "Job not found")
    if not job.get("document_json"):
        raise HTTPException(404, "Document JSON not ready")
    path = JOBS_DIR / job_id / "document.json"
    if path.exists():
        return FileResponse(path, filename=f"{job['title']}.json", media_type="application/json")
    raise HTTPException(404, "File missing")


@app.get("/api/jobs/{job_id}/download")
async def download_pdf(job_id: str):
    try:
        job = db.get_job(job_id)
    except KeyError:
        raise HTTPException(404, "Job not found")
    pdf_path = job.get("pdf_path")
    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(404, "PDF not ready")
    safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in job["title"])[:80]
    return FileResponse(pdf_path, filename=f"{safe.strip() or 'study_guide'}.pdf", media_type="application/pdf")


@app.post("/api/jobs/{job_id}/resume")
async def resume_job_endpoint(job_id: str):
    try:
        job = db.get_job(job_id)
    except KeyError:
        raise HTTPException(404, "Job not found")
    if job["status"] == "running":
        raise HTTPException(409, "Job is already running")
    if not get_rotator().has_keys:
        raise HTTPException(400, "Add at least one Gemini API key first")
    if not can_resume_job(job_id, job["status"]):
        raise HTTPException(400, "No checkpoint to resume — job has no saved progress")
    if not resume_job(job_id):
        raise HTTPException(400, "Could not resume job")
    cp = scan_checkpoint(job_id)
    return {
        "ok": True,
        "job_id": job_id,
        "resume_from": cp["next_step"],
        "chapters_saved": len(cp["chapters_done"]),
    }


@app.post("/api/jobs")
async def create_job(
    title: str = Form(...),
    extra_context: str = Form(""),
    files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(400, "Upload at least one PDF")
    if not get_rotator().has_keys:
        raise HTTPException(400, "Add at least one Gemini API key first")

    job_id = str(uuid.uuid4())
    upload_dir = UPLOADS_DIR / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            raise HTTPException(400, f"Only PDF files allowed: {f.filename}")
        dest = upload_dir / Path(f.filename).name
        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(str(dest))

    job = db.create_job(title.strip(), saved, extra_context.strip())
    db.log_activity("job_created", f"Job queued: {title.strip()}", {"job_id": job["id"], "files": len(saved)})
    start_job(job["id"])
    return {"job": {k: job[k] for k in ("id", "title", "status", "created_at")}}


@app.post("/api/jobs/text-only")
async def create_text_job(body: JobCreate):
    """Create a job from pasted text context (no PDF)."""
    if not get_rotator().has_keys:
        raise HTTPException(400, "Add at least one Gemini API key first")
    if not body.extra_context.strip():
        raise HTTPException(400, "Provide context text")

    job_id = str(uuid.uuid4())
    txt_path = UPLOADS_DIR / job_id / "context.txt"
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.write_text(body.extra_context, encoding="utf-8")

    job = db.create_job(body.title.strip(), [str(txt_path)], "", job_id=job_id)
    db.log_activity("job_created", f"Text job queued: {body.title.strip()}", {"job_id": job["id"]})
    start_job(job["id"])
    return {"job": {k: job[k] for k in ("id", "title", "status", "created_at")}}


class InternalRunJob(BaseModel):
    job_id: str
    resume: bool = False


@app.post("/api/internal/run-job")
async def internal_run_job(body: InternalRunJob, authorization: Optional[str] = Header(default=None)):
    """Worker endpoint — runs the full pipeline in a dedicated serverless invocation."""
    secret = os.environ.get("INTERNAL_JOB_SECRET", "").strip()
    if not secret:
        raise HTTPException(503, "INTERNAL_JOB_SECRET not configured")
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != secret:
        raise HTTPException(401, "Unauthorized")
    try:
        db.get_job(body.job_id)
    except KeyError:
        raise HTTPException(404, "Job not found")
    await run_job(body.job_id, resume=body.resume)
    return {"ok": True}
