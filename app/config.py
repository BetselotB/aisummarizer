"""Application configuration."""

import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _resource_dir() -> Path:
    if _is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return Path(__file__).resolve().parent.parent


def _user_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AI Study Guide Generator"
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) if local else Path.home() / "AppData" / "Local"
        return base / "AIStudyGuideGenerator"
    return Path.home() / ".local" / "share" / "aisummarizer"


BASE_DIR = _resource_dir()
IS_VERCEL = bool(os.environ.get("VERCEL"))
IS_DESKTOP = _is_frozen() or bool(os.environ.get("AISUMMARIZER_DESKTOP"))

# Vercel Functions only allow writes under /tmp (ephemeral between cold starts).
if os.environ.get("DATA_DIR"):
    DATA_DIR = Path(os.environ["DATA_DIR"])
elif IS_VERCEL:
    DATA_DIR = Path("/tmp/aisummarizer/data")
elif IS_DESKTOP:
    DATA_DIR = _user_data_dir() / "data"
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

# OpenRouter — override with env OPENROUTER_MODEL
_default_or_model = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
OPENROUTER_MODEL_OUTLINE = os.environ.get("OPENROUTER_MODEL_OUTLINE", _default_or_model)
OPENROUTER_MODEL_CHAPTER = os.environ.get("OPENROUTER_MODEL_CHAPTER", _default_or_model)

OPENROUTER_MODEL_FALLBACKS = [
    m.strip()
    for m in os.environ.get(
        "OPENROUTER_MODEL_FALLBACKS",
        "meta-llama/llama-3.3-70b-instruct:free,google/gemini-2.5-flash-preview:free",
    ).split(",")
    if m.strip()
]

OPENROUTER_MAX_RETRIES = int(os.environ.get("OPENROUTER_MAX_RETRIES", "8"))
OPENROUTER_RETRY_BASE_DELAY = float(os.environ.get("OPENROUTER_RETRY_BASE_DELAY", "3.0"))
OPENROUTER_INTER_REQUEST_DELAY = float(os.environ.get("OPENROUTER_INTER_REQUEST_DELAY", "2.0"))

OPENROUTER_SITE_URL = os.environ.get("OPENROUTER_SITE_URL", "")
OPENROUTER_SITE_NAME = os.environ.get("OPENROUTER_SITE_NAME", "AI Study Guide Generator")

# Grok (x.ai) — override with env GROK_MODEL
_default_grok_model = os.environ.get("GROK_MODEL", "grok-4.3")
GROK_MODEL_OUTLINE = os.environ.get("GROK_MODEL_OUTLINE", _default_grok_model)
GROK_MODEL_CHAPTER = os.environ.get("GROK_MODEL_CHAPTER", _default_grok_model)

GROK_MODEL_FALLBACKS = [
    m.strip()
    for m in os.environ.get("GROK_MODEL_FALLBACKS", "grok-4,grok-3-mini").split(",")
    if m.strip()
]

GROK_MAX_RETRIES = int(os.environ.get("GROK_MAX_RETRIES", "8"))
GROK_RETRY_BASE_DELAY = float(os.environ.get("GROK_RETRY_BASE_DELAY", "3.0"))
GROK_INTER_REQUEST_DELAY = float(os.environ.get("GROK_INTER_REQUEST_DELAY", "2.0"))

for d in (DATA_DIR, UPLOADS_DIR, OUTPUTS_DIR, JOBS_DIR):
    d.mkdir(parents=True, exist_ok=True)
