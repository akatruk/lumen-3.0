"""LLM provider abstraction. OpenRouter is optional, never required for create."""

from __future__ import annotations

from typing import Any, Protocol

from ..config import settings


class LLMProvider(Protocol):
    name: str

    def available(self) -> bool: ...

    def json_call(self, *args, **kwargs) -> Any: ...


class NoneLLMProvider:
    name = "none"

    def available(self) -> bool:
        return False

    def json_call(self, *args, **kwargs):
        raise RuntimeError("llm_provider_unavailable")


class OpenRouterLLMProvider:
    name = "openrouter"

    def available(self) -> bool:
        return bool(settings.openrouter_api_key)

    def json_call(self, *args, **kwargs):
        from .. import ai

        return ai.json_call(*args, **kwargs)


def get_llm_provider(name: str | None = None) -> LLMProvider:
    chosen = (name or getattr(settings, "llm_provider", "none") or "none").strip().lower()
    if chosen in ("openrouter", "or"):
        return OpenRouterLLMProvider()
    return NoneLLMProvider()
