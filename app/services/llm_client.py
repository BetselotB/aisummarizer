"""Unified LLM client — routes to Gemini, OpenRouter, or Grok based on active provider."""

from __future__ import annotations

from typing import Any

from app import database as db
from app.config import (
    GEMINI_MODEL_CHAPTER,
    GEMINI_MODEL_OUTLINE,
    GROK_MODEL_CHAPTER,
    GROK_MODEL_OUTLINE,
    OPENROUTER_MODEL_CHAPTER,
    OPENROUTER_MODEL_OUTLINE,
)
from app.services.gemini import GeminiClient
from app.services.grok import GrokClient
from app.services.key_rotator import KeyRotator
from app.services.key_validation import Provider
from app.services.openrouter import OpenRouterClient

_PROVIDERS: tuple[Provider, ...] = ("gemini", "openrouter", "grok")


def get_active_provider() -> Provider:
    saved = db.get_app_state("llm_provider")
    rotator = KeyRotator()
    if saved in _PROVIDERS and rotator.has_keys_for(saved):
        return saved
    for provider in _PROVIDERS:
        if rotator.has_keys_for(provider):
            return provider
    return saved if saved in _PROVIDERS else "gemini"


def get_model_for_provider(provider: Provider, phase: str = "outline") -> str:
    model_key = f"{provider}_model"
    saved = db.get_app_state(model_key)
    if saved:
        return saved
    defaults = {
        "openrouter": (OPENROUTER_MODEL_OUTLINE, OPENROUTER_MODEL_CHAPTER),
        "grok": (GROK_MODEL_OUTLINE, GROK_MODEL_CHAPTER),
        "gemini": (GEMINI_MODEL_OUTLINE, GEMINI_MODEL_CHAPTER),
    }
    outline, chapter = defaults[provider]
    return outline if phase == "outline" else chapter


class LLMClient:
    def __init__(self, rotator: KeyRotator, provider: Provider | None = None):
        self.rotator = rotator
        self.provider = provider or get_active_provider()
        self._gemini = GeminiClient(rotator)
        self._openrouter = OpenRouterClient(rotator)
        self._grok = GrokClient(rotator)

    @property
    def model_outline(self) -> str:
        return get_model_for_provider(self.provider, "outline")

    @property
    def model_chapter(self) -> str:
        return get_model_for_provider(self.provider, "chapter")

    async def generate_json(
        self,
        prompt: str,
        system: str,
        model_name: str,
        temperature: float = 0.4,
        on_wait: Any | None = None,
    ) -> dict[str, Any]:
        if self.provider == "openrouter":
            return await self._openrouter.generate_json(
                prompt=prompt,
                system=system,
                model_name=model_name,
                temperature=temperature,
                on_wait=on_wait,
            )
        if self.provider == "grok":
            return await self._grok.generate_json(
                prompt=prompt,
                system=system,
                model_name=model_name,
                temperature=temperature,
                on_wait=on_wait,
            )
        return await self._gemini.generate_json(
            prompt=prompt,
            system=system,
            model_name=model_name,
            temperature=temperature,
            on_wait=on_wait,
        )
