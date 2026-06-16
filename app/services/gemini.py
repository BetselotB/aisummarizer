"""Gemini API client with JSON output, model fallback, and key rotation."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from app.config import (
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL_FALLBACKS,
    GEMINI_RETRY_BASE_DELAY,
)
from app.services.key_rotator import KeyRotator


RATE_LIMIT_MARKERS = (
    "429",
    "quota",
    "rate limit",
    "resource exhausted",
    "too many requests",
    "limit: 0",
)


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json_response(text: str) -> dict[str, Any]:
    cleaned = _strip_json_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group())
        raise


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    if isinstance(exc, google_exceptions.ResourceExhausted):
        return True
    return any(m in msg for m in RATE_LIMIT_MARKERS)


def _is_daily_quota_exhausted(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "limit: 0" in msg or "perday" in msg or "per_day" in msg


def _parse_retry_seconds(exc: Exception) -> float:
    msg = str(exc)
    m = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", msg, re.I)
    if m:
        return float(m.group(1)) + 1.0
    m = re.search(r'retry_delay\s*\{\s*seconds:\s*(\d+)', msg)
    if m:
        return float(m.group(1)) + 1.0
    return GEMINI_RETRY_BASE_DELAY


def _model_chain(preferred: str) -> list[str]:
    seen: set[str] = set()
    chain: list[str] = []
    for m in [preferred, *GEMINI_MODEL_FALLBACKS]:
        if m and m not in seen:
            seen.add(m)
            chain.append(m)
    return chain


def _friendly_quota_error(exc: Exception, keys_tried: int, models_tried: list[str]) -> str:
    base = str(exc).split("[links")[0].strip()[:400]
    hints = [
        "Free-tier quota is per Google Cloud project, not per API key — "
        "multiple keys from the same account/project share one limit.",
        "Daily quota resets at midnight Pacific Time. Per-minute limits need ~7s between calls.",
        "Use API keys from different Google accounts/projects, or enable billing on AI Studio.",
        f"Tried {keys_tried} key rotation(s) and models: {', '.join(models_tried)}.",
    ]
    return base + "\n\n" + "\n".join(f"• {h}" for h in hints)


class GeminiClient:
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
        full_prompt = f"{system.strip()}\n\n---\n\n{prompt.strip()}"
        models = _model_chain(model_name)
        last_error: Exception | None = None
        attempts = 0
        max_attempts = max(self.rotator.key_count, 1) * len(models) * GEMINI_MAX_RETRIES
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
                    full_prompt,
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
                daily = _is_daily_quota_exhausted(exc)

                if on_wait:
                    label = f"Rate limited on {current_model}"
                    if daily:
                        label += " (daily quota) — switching model/key"
                    await on_wait(wait, label)

                await asyncio.sleep(wait)

                if daily and len(models) > 1:
                    model_idx += 1
                    if on_wait:
                        await on_wait(0, f"Trying fallback model: {models[model_idx % len(models)]}")

                if self.rotator.key_count > 1:
                    self.rotator.on_rate_limit()

        raise RuntimeError(_friendly_quota_error(last_error, keys_used, models_tried))

    @staticmethod
    def _call_sync(api_key: str, model_name: str, prompt: str, temperature: float) -> str:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name,
            generation_config={
                "temperature": temperature,
                "response_mime_type": "application/json",
            },
        )
        response = model.generate_content(prompt)
        if not response.text:
            raise RuntimeError("Empty response from Gemini")
        return response.text


def load_prompt(name: str) -> str:
    path = Path(__file__).resolve().parents[2] / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")
