"""Round-robin API key pool with rate-limit fallback (Gemini + OpenRouter)."""

from __future__ import annotations

import itertools
import threading
from typing import Any

from app import database as db
from app.services.key_validation import Provider, detect_provider, is_valid_api_key


class KeyRotator:
    def __init__(self, keys: list[dict[str, Any]] | None = None, provider: Provider | None = None):
        self._lock = threading.Lock()
        self._provider = provider
        self.reload(keys)

    def reload(self, keys: list[dict[str, Any]] | None = None) -> None:
        with self._lock:
            if keys is None:
                keys = db.get_enabled_api_keys()
            self._all_keys = [k for k in keys if is_valid_api_key(k.get("api_key", ""))]
            for k in self._all_keys:
                if not k.get("provider"):
                    k["provider"] = detect_provider(k.get("api_key", ""))
            self._apply_provider_filter()
            self._cycle = itertools.cycle(self._keys) if self._keys else None
            self._current = next(self._cycle) if self._cycle else None

    def set_provider(self, provider: Provider | None) -> None:
        with self._lock:
            self._provider = provider
            self._apply_provider_filter()
            self._cycle = itertools.cycle(self._keys) if self._keys else None
            self._current = next(self._cycle) if self._cycle else None

    def _apply_provider_filter(self) -> None:
        if self._provider:
            self._keys = [k for k in self._all_keys if k.get("provider") == self._provider]
        else:
            self._keys = list(self._all_keys)

    @property
    def provider(self) -> Provider | None:
        return self._provider

    @property
    def has_keys(self) -> bool:
        return bool(self._keys)

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def has_keys_for(self, provider: Provider) -> bool:
        return any(k.get("provider") == provider for k in self._all_keys)

    def count_for(self, provider: Provider) -> int:
        return sum(1 for k in self._all_keys if k.get("provider") == provider)

    def current(self) -> dict[str, Any]:
        with self._lock:
            if not self._current:
                label = self._provider or "API"
                raise RuntimeError(f"No {label} keys configured. Add at least one key in Settings.")
            return self._current

    def on_rate_limit(self) -> dict[str, Any]:
        with self._lock:
            if not self._cycle:
                raise RuntimeError("No API keys available.")
            self._current = next(self._cycle)
            return self._current

    def record_success(self, key_id: str) -> None:
        db.record_key_usage(key_id, error=None)

    def record_error(self, key_id: str, error: str) -> None:
        db.record_key_usage(key_id, error=error)
