"""Application configuration."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IS_VERCEL = bool(os.environ.get("VERCEL"))

# Vercel Functions only allow writes under /tmp (ephemeral between cold starts).
if IS_VERCEL:
    DATA_DIR = Path("/tmp/aisummarizer/data")
else:
    DATA_DIR = BASE_DIR / "data"

UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUTS_DIR = DATA_DIR / "outputs"
JOBS_DIR = DATA_DIR / "jobs"
DB_PATH = DATA_DIR / "app.db"

# Primary model — override with env GEMINI_MODEL
_default_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_MODEL_OUTLINE = os.environ.get("GEMINI_MODEL_OUTLINE", _default_model)
GEMINI_MODEL_CHAPTER = os.environ.get("GEMINI_MODEL_CHAPTER", _default_model)

# On 429/quota, try these models in order (each has separate free-tier quota)
GEMINI_MODEL_FALLBACKS = [
    m.strip()
    for m in os.environ.get(
        "GEMINI_MODEL_FALLBACKS",
        "gemini-2.5-flash-lite,gemini-1.5-flash",
    ).split(",")
    if m.strip()
]

GEMINI_MAX_RETRIES = int(os.environ.get("GEMINI_MAX_RETRIES", "8"))
GEMINI_RETRY_BASE_DELAY = float(os.environ.get("GEMINI_RETRY_BASE_DELAY", "3.0"))
# Free tier ~10 RPM — wait between chapter calls to avoid per-minute limits
GEMINI_INTER_REQUEST_DELAY = float(os.environ.get("GEMINI_INTER_REQUEST_DELAY", "7.0"))

CHUNK_CHAR_LIMIT = int(os.environ.get("CHUNK_CHAR_LIMIT", "120000"))

for d in (DATA_DIR, UPLOADS_DIR, OUTPUTS_DIR, JOBS_DIR):
    d.mkdir(parents=True, exist_ok=True)
