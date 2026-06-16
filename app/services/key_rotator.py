"""Round-robin Gemini API key pool with rate-limit fallback."""

from __future__ import annotations

import itertools
import threading
from typing import Any

from app import database as db
from app.services.key_validation import is_valid_gemini_api_key


class KeyRotator:
    def __init__(self, keys: list[dict[str, Any]] | None = None):
        self._lock = threading.Lock()
        self.reload(keys)

    def reload(self, keys: list[dict[str, Any]] | None = None) -> None:
        with self._lock:
            if keys is None:
                keys = db.get_enabled_api_keys()
            self._keys = [k for k in keys if is_valid_gemini_api_key(k.get("api_key", ""))]
            self._cycle = itertools.cycle(self._keys) if self._keys else None
            self._current = next(self._cycle) if self._cycle else None

    @property
    def has_keys(self) -> bool:
        return bool(self._keys)

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def current(self) -> dict[str, Any]:
        with self._lock:
            if not self._current:
                raise RuntimeError("No Gemini API keys configured. Add at least one key in Settings.")
            return self._current

    def on_rate_limit(self) -> dict[str, Any]:
        with self._lock:
            if not self._cycle:
                raise RuntimeError("No Gemini API keys available.")
            self._current = next(self._cycle)
            return self._current

    def record_success(self, key_id: str) -> None:
        db.record_key_usage(key_id, error=None)

    def record_error(self, key_id: str, error: str) -> None:
        db.record_key_usage(key_id, error=error)
