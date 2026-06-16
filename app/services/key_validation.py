"""Validate Google Gemini API keys."""

from __future__ import annotations

import re

# Real Gemini API keys from AI Studio start with AIza and are ~39 chars
_GEMINI_KEY_RE = re.compile(r"^AIza[0-9A-Za-z_-]{30,}$")


def is_valid_gemini_api_key(key: str) -> bool:
    key = key.strip()
    if not key:
        return False
    if key.startswith("AQ."):
        return False
    if not key.startswith("AIza"):
        return False
    return bool(_GEMINI_KEY_RE.match(key))


def validate_gemini_api_key(key: str) -> str | None:
    """Return error message if invalid, else None."""
    key = key.strip()
    if not key:
        return "Key is empty"
    if key.startswith("AQ."):
        return (
            "This looks like an OAuth token (AQ.…), not a Gemini API key. "
            "Get a key at https://aistudio.google.com/apikey — it must start with AIza"
        )
    if not key.startswith("AIza"):
        return "Gemini API keys must start with AIza (from Google AI Studio)"
    if len(key) < 35:
        return "API key looks too short"
    if not _GEMINI_KEY_RE.match(key):
        return "API key format is invalid"
    return None
