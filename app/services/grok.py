"""Grok (x.ai) API client with JSON output, model fallback, and key rotation."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from app.config import (
    GROK_MAX_RETRIES,
    GROK_MODEL_FALLBACKS,
    GROK_RETRY_BASE_DELAY,
)
from app.services.gemini import _parse_json_response
from app.services.key_rotator import KeyRotator


GROK_API_URL = "https://api.x.ai/v1/responses"

RATE_LIMIT_MARKERS = (
    "429",
    "quota",
    "rate limit",
    "too many requests",
    "credits",
    "resource exhausted",
)


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(m in msg for m in RATE_LIMIT_MARKERS)


def _parse_retry_seconds(exc: Exception) -> float:
    msg = str(exc)
    m = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", msg, re.I)
    if m:
        return float(m.group(1)) + 1.0
    m = re.search(r"retry.after[:\s]+(\d+)", msg, re.I)
    if m:
        return float(m.group(1)) + 1.0
    return GROK_RETRY_BASE_DELAY


def _model_chain(preferred: str) -> list[str]:
    seen: set[str] = set()
    chain: list[str] = []
    for m in [preferred, *GROK_MODEL_FALLBACKS]:
        if m and m not in seen:
            seen.add(m)
            chain.append(m)
    return chain


def _extract_text(data: dict[str, Any]) -> str:
    if data.get("output_text"):
        return str(data["output_text"])
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") == "output_text" and part.get("text"):
                return str(part["text"])
    raise RuntimeError("Empty response from Grok")


def _friendly_quota_error(exc: Exception, keys_tried: int, models_tried: list[str]) -> str:
    base = str(exc)[:400]
    hints = [
        "Grok API rate limits are per key — add more keys at https://console.x.ai",
        f"Tried {keys_tried} key rotation(s) and models: {', '.join(models_tried)}.",
    ]
    return base + "\n\n" + "\n".join(f"• {h}" for h in hints)


class GrokClient:
    def __init__(self, rotator: KeyRotator):
        self.rotator = rotator

    async def generate_json(
        self,
        prompt: str,
        system: str,
        model_name: str,
        temperature: float = 0.4,
        on_wait: Any | None = None,
    ) -> dict[str, Any]:
        models = _model_chain(model_name)
        last_error: Exception | None = None
        attempts = 0
        max_attempts = max(self.rotator.key_count, 1) * len(models) * GROK_MAX_RETRIES
        models_tried: list[str] = []
        keys_used = 0

        model_idx = 0
        while attempts < max_attempts:
            current_model = models[model_idx % len(models)]
            if current_model not in models_tried:
                models_tried.append(current_model)

            key_row = self.rotator.current()
            key_id = key_row["id"]
            api_key = key_row["api_key"]
            attempts += 1
            keys_used += 1

            try:
                result = await asyncio.to_thread(
                    self._call_sync,
                    api_key,
                    current_model,
                    system,
                    prompt,
                    temperature,
                )
                self.rotator.record_success(key_id)
                return _parse_json_response(result)
            except Exception as exc:
                last_error = exc
                self.rotator.record_error(key_id, str(exc)[:500])

                if not _is_rate_limit(exc):
                    raise

                wait = _parse_retry_seconds(exc)
                if on_wait:
                    await on_wait(wait, f"Rate limited on {current_model} — switching key")

                await asyncio.sleep(wait)

                if len(models) > 1:
                    model_idx += 1
                    if on_wait:
                        await on_wait(0, f"Trying fallback model: {models[model_idx % len(models)]}")

                if self.rotator.key_count > 1:
                    self.rotator.on_rate_limit()

        raise RuntimeError(_friendly_quota_error(last_error, keys_used, models_tried))

    @staticmethod
    def _call_sync(
        api_key: str,
        model_name: str,
        system: str,
        prompt: str,
        temperature: float,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model_name,
            "input": [
                {"role": "system", "content": system.strip()},
                {"role": "user", "content": prompt.strip()},
            ],
            "temperature": temperature,
            "text": {"format": {"type": "json_object"}},
            "store": False,
        }

        with httpx.Client(timeout=180.0) as client:
            response = client.post(GROK_API_URL, headers=headers, json=payload)

        if response.status_code >= 400:
            detail = response.text[:500]
            raise RuntimeError(f"Grok HTTP {response.status_code}: {detail}")

        return _extract_text(response.json())
