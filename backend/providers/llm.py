"""LLM provider abstraction. OpenRouter is optional; RunPod is fail-closed."""

from __future__ import annotations

from typing import Any, Protocol

from ..config import settings


class LLMProvider(Protocol):
    name: str

    def available(self) -> bool: ...

    def health_check(self) -> dict: ...

    def json_call(self, *args, **kwargs) -> Any: ...


class NoneLLMProvider:
    name = "none"

    def available(self) -> bool:
        return False

    def health_check(self) -> dict:
        return {"ok": False, "provider": "none"}

    def json_call(self, *args, **kwargs):
        raise RuntimeError("llm_provider_unavailable")


class OpenRouterLLMProvider:
    name = "openrouter"

    def available(self) -> bool:
        return bool(settings.openrouter_api_key)

    def health_check(self) -> dict:
        return {"ok": self.available(), "provider": "openrouter"}

    def json_call(self, *args, **kwargs):
        from .. import ai

        return ai.json_call(*args, **kwargs)


class RunPodLLMProvider:
    """Local OpenAI-compatible LLM on lumen-hypit-4090 via SSH tunnel.

    When selected (LLM_PROVIDER=runpod), absence of a healthy endpoint is a hard
    error — never silently swap to heuristic / OpenRouter.
    """

    name = "runpod"

    def available(self) -> bool:
        try:
            from .. import runpod_llm

            return bool(runpod_llm.health_check().get("ok"))
        except Exception:
            return False

    def health_check(self) -> dict:
        from .. import runpod_llm

        return runpod_llm.health_check(ensure_model=True)

    def require_available(self) -> None:
        health = self.health_check()
        if not health.get("ok"):
            from ..runpod_llm import RUNPOD_LLM_UNAVAILABLE, RunpodLlmError

            raise RunpodLlmError(health.get("error") or RUNPOD_LLM_UNAVAILABLE)

    def json_call(self, *args, **kwargs):
        """Text-only structured JSON via RunPod local model (no OpenRouter)."""
        import json as _json

        from pydantic import ValidationError

        from ..runpod_director_normalize import normalize_director_payload
        from ..runpod_llm import RunpodLlmError, chat_completions, extract_message_content

        self.require_available()
        prompt = kwargs.get("prompt")
        schema = kwargs.get("schema")
        system = kwargs.get("system")
        if args:
            if len(args) >= 3 and prompt is None:
                prompt = args[2]
            if len(args) >= 4 and schema is None:
                schema = args[3]
        if not prompt or schema is None:
            raise RunpodLlmError("json_call_args")

        schema_text = schema.model_json_schema() if hasattr(schema, "model_json_schema") else schema
        messages = [
            {
                "role": "system",
                "content": system
                or (
                    "You are Lumen Director. Return ONLY valid JSON matching the schema. "
                    "Do not invent claims, metrics, or speech. Multilingual fields: en, zh."
                ),
            },
            {
                "role": "user",
                "content": f"{prompt}\nRequired JSON schema:\n{_json.dumps(schema_text, ensure_ascii=False)}",
            },
        ]
        duration = float(kwargs.get("duration") or 0) or None
        normalize = bool(kwargs.get("normalize"))
        validator = kwargs.get("validator")
        last_err: Exception | None = None
        for attempt in range(2):
            payload_messages = messages
            if attempt == 1:
                payload_messages = messages + [
                    {
                        "role": "user",
                        "content": (
                            "Previous JSON failed schema validation. Return a complete object again. "
                            "Text fields MUST be {\"en\":\"...\",\"zh\":\"...\"}. "
                            "Captions use original/en/zh/ru (not text). transfers=[]. recommendations=[] is OK."
                        ),
                    }
                ]
            data = chat_completions(messages=payload_messages, temperature=0.1, max_tokens=8192)
            content = extract_message_content(data)
            try:
                raw = _json.loads(content)
                if normalize and duration is not None and hasattr(schema, "model_validate"):
                    raw = normalize_director_payload(raw, duration=duration)
                    result = schema.model_validate(raw)
                else:
                    result = schema.model_validate_json(content)
                if validator:
                    validator(result)
                return result
            except (ValidationError, ValueError, _json.JSONDecodeError) as exc:
                last_err = exc
                continue
        raise RunpodLlmError(f"invalid_director_json:{type(last_err).__name__}") from last_err


def get_llm_provider(name: str | None = None) -> LLMProvider:
    chosen = (name or getattr(settings, "llm_provider", "none") or "none").strip().lower()
    if chosen in ("openrouter", "or"):
        return OpenRouterLLMProvider()
    if chosen in ("runpod", "runpod_llm", "local_runpod"):
        return RunPodLLMProvider()
    return NoneLLMProvider()
