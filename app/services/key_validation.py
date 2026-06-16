"""Validate Gemini, OpenRouter, and Grok API keys."""

from __future__ import annotations

import re
from typing import Literal

Provider = Literal["gemini", "openrouter", "grok"]

# Real Gemini API keys from AI Studio start with AIza and are ~39 chars
_GEMINI_KEY_RE = re.compile(r"^AIza[0-9A-Za-z_-]{30,}$")
_OPENROUTER_KEY_RE = re.compile(r"^sk-or-v1-[0-9A-Za-z]{20,}$")
_GROK_KEY_RE = re.compile(r"^xai-[0-9A-Za-z]{20,}$")


def detect_provider(key: str) -> Provider | None:
    key = key.strip()
    if is_valid_gemini_api_key(key):
        return "gemini"
    if is_valid_openrouter_api_key(key):
        return "openrouter"
    if is_valid_grok_api_key(key):
        return "grok"
    return None


def is_valid_gemini_api_key(key: str) -> bool:
    key = key.strip()
    if not key:
        return False
    if key.startswith("AQ."):
        return False
    if not key.startswith("AIza"):
        return False
    return bool(_GEMINI_KEY_RE.match(key))


def is_valid_openrouter_api_key(key: str) -> bool:
    key = key.strip()
    if not key:
        return False
    if not key.startswith("sk-or-v1-"):
        return False
    return bool(_OPENROUTER_KEY_RE.match(key))


def is_valid_grok_api_key(key: str) -> bool:
    key = key.strip()
    if not key:
        return False
    if not key.startswith("xai-"):
        return False
    return bool(_GROK_KEY_RE.match(key))


def is_valid_api_key(key: str) -> bool:
    return detect_provider(key) is not None


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


def validate_openrouter_api_key(key: str) -> str | None:
    """Return error message if invalid, else None."""
    key = key.strip()
    if not key:
        return "Key is empty"
    if not key.startswith("sk-or-v1-"):
        return "OpenRouter API keys must start with sk-or-v1- (from https://openrouter.ai/keys)"
    if not _OPENROUTER_KEY_RE.match(key):
        return "OpenRouter API key format is invalid"
    return None


def validate_grok_api_key(key: str) -> str | None:
    """Return error message if invalid, else None."""
    key = key.strip()
    if not key:
        return "Key is empty"
    if not key.startswith("xai-"):
        return "Grok API keys must start with xai- (from https://console.x.ai)"
    if not _GROK_KEY_RE.match(key):
        return "Grok API key format is invalid"
    return None


def validate_api_key(key: str) -> str | None:
    """Validate a Gemini, OpenRouter, or Grok key. Return error message if invalid."""
    key = key.strip()
    if not key:
        return "Key is empty"
    provider = detect_provider(key)
    if provider in ("gemini", "openrouter", "grok"):
        return None
    if key.startswith("AIza"):
        return validate_gemini_api_key(key)
    if key.startswith("sk-or"):
        return validate_openrouter_api_key(key)
    if key.startswith("xai-"):
        return validate_grok_api_key(key)
    return (
        "Unrecognized key format. Use AIza… (Gemini), sk-or-v1-… (OpenRouter), or xai-… (Grok)"
    )
