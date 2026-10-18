"""RunPod-local OpenAI-compatible LLM (Ollama on lumen-hypit-4090).

Traffic stays on the existing Hypit GPU SSH channel (localhost bind on the pod).
Load for Director planning; unload before image / Hypit / speech GPU jobs.
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any

from .config import settings
from .hypit_gpu import _ssh, _ssh_argv, pod_session

log = logging.getLogger("lumen.runpod_llm")

RUNPOD_LLM_UNAVAILABLE = "RUNPOD_LLM_UNAVAILABLE"
DEFAULT_MODEL = "qwen2.5:7b-instruct"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 11434
REMOTE_BIN = "/workspace/lumen-llm/bin/ollama"
REMOTE_MODELS = "/workspace/lumen-llm/models"
REMOTE_LIB = "/workspace/lumen-llm/lib"
REMOTE_LOG = "/workspace/lumen-llm/logs/serve.log"
REMOTE_PID = "/workspace/lumen-llm/ollama.pid"


class RunpodLlmError(RuntimeError):
    """Fail-closed signal when LLM_PROVIDER=runpod cannot serve."""

    def __init__(self, detail: str = ""):
        super().__init__(RUNPOD_LLM_UNAVAILABLE)
        self.detail = detail or RUNPOD_LLM_UNAVAILABLE


def _cfg_model() -> str:
    return (getattr(settings, "runpod_llm_model", None) or os.environ.get("RUNPOD_LLM_MODEL") or DEFAULT_MODEL).strip()


def _cfg_port() -> int:
    raw = getattr(settings, "runpod_llm_port", None) or os.environ.get("RUNPOD_LLM_PORT") or DEFAULT_PORT
    return int(raw)


def _cfg_api_key() -> str:
    return (getattr(settings, "runpod_llm_api_key", None) or os.environ.get("RUNPOD_LLM_API_KEY") or "lumen-runpod").strip()


def _remote_env() -> str:
    return (
        f"export OLLAMA_HOST={DEFAULT_HOST}:{_cfg_port()}; "
        f"export OLLAMA_MODELS={REMOTE_MODELS}; "
        f"export LD_LIBRARY_PATH={REMOTE_LIB}:${{LD_LIBRARY_PATH:-}}; "
    )


def _ensure_serve(ip: str, port: int) -> None:
    probe = (
        _remote_env()
        + f"curl -sf --max-time 3 http://{DEFAULT_HOST}:{_cfg_port()}/api/tags >/dev/null "
        f"&& echo UP || echo DOWN"
    )
    out = _ssh(ip, port, probe + "\n", timeout=60)
    if "UP" in out:
        return
    start = (
        _remote_env()
        + f"mkdir -p {REMOTE_MODELS} $(dirname {REMOTE_LOG}); "
        f"pkill -f '{REMOTE_BIN} serve' 2>/dev/null || true; sleep 1; "
        f"nohup {REMOTE_BIN} serve > {REMOTE_LOG} 2>&1 & echo $! > {REMOTE_PID}; "
        f"for i in 1 2 3 4 5 6 7 8 9 10; do "
        f"curl -sf --max-time 2 http://{DEFAULT_HOST}:{_cfg_port()}/api/tags >/dev/null && echo READY && break; "
        f"sleep 1; done"
    )
    ready = _ssh(ip, port, start + "\n", timeout=120)
    if "READY" not in ready:
        raise RunpodLlmError("ollama_serve_failed")


def _local_base_url() -> str | None:
    """Optional direct URL for tests / already-forwarded tunnels."""
    return (getattr(settings, "runpod_llm_base_url", None) or os.environ.get("RUNPOD_LLM_BASE_URL") or "").strip() or None


def _http_json(method: str, url: str, body: dict | None = None, timeout: float = 120) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_cfg_api_key()}",
            "User-Agent": "lumen-runpod-llm/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:400]
        raise RunpodLlmError(f"http_{exc.code}:{detail}") from exc
    except Exception as exc:
        raise RunpodLlmError(f"{type(exc).__name__}") from exc
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RunpodLlmError("invalid_json") from exc


class _Tunnel:
    """SSH local-forward to pod Ollama; used when RUNPOD_LLM_BASE_URL is unset."""

    def __init__(self, ip: str, ssh_port: int, local_port: int | None = None):
        self.ip = ip
        self.ssh_port = ssh_port
        self.local_port = local_port or (19000 + (ssh_port % 1000))
        self.proc: subprocess.Popen | None = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.local_port}/v1"

    def __enter__(self):
        argv = _ssh_argv(self.ip, self.ssh_port) + [
            "-N",
            "-L",
            f"{self.local_port}:{DEFAULT_HOST}:{_cfg_port()}",
        ]
        self.proc = subprocess.Popen(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 25
        last: Exception | None = None
        while time.time() < deadline:
            try:
                _http_json("GET", f"http://127.0.0.1:{self.local_port}/api/tags", timeout=3)
                return self
            except Exception as exc:
                last = exc
                if self.proc.poll() is not None:
                    break
                time.sleep(0.4)
        self.__exit__(None, None, None)
        raise RunpodLlmError(f"tunnel_failed:{type(last).__name__ if last else 'unknown'}")

    def __exit__(self, *args):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None


def health_check(*, ensure_model: bool = False) -> dict[str, Any]:
    """Probe local LLM. Never falls back to another provider."""
    base = _local_base_url()
    model = _cfg_model()
    try:
        if base:
            root = base.rstrip("/").removesuffix("/v1")
            tags = _http_json("GET", f"{root}/api/tags", timeout=8)
            models = [m.get("name") for m in (tags.get("models") or []) if m.get("name")]
            ok = True
            if ensure_model and model not in models and not any(model in (n or "") for n in models):
                ok = False
            return {
                "ok": ok,
                "provider": "runpod",
                "model": model,
                "models": models,
                "base_url": base,
                "mode": "direct",
            }
        with pod_session() as (ip, ssh_port, pod_id):
            _ensure_serve(ip, ssh_port)
            with _Tunnel(ip, ssh_port) as tunnel:
                root = tunnel.base_url.rstrip("/").removesuffix("/v1")
                tags = _http_json("GET", f"{root}/api/tags", timeout=8)
                models = [m.get("name") for m in (tags.get("models") or []) if m.get("name")]
                present = model in models or any(model in (n or "") for n in models)
                return {
                    "ok": bool(models) and (present if ensure_model else True),
                    "provider": "runpod",
                    "model": model,
                    "models": models,
                    "pod_id": pod_id,
                    "mode": "ssh_tunnel",
                    "model_present": present,
                }
    except RunpodLlmError as exc:
        return {"ok": False, "provider": "runpod", "error": exc.detail, "model": model}
    except Exception as exc:
        return {"ok": False, "provider": "runpod", "error": type(exc).__name__, "model": model}


def load_model(model: str | None = None) -> None:
    """Warm the configured model into VRAM via a tiny generation."""
    model = (model or _cfg_model()).strip()
    chat_completions(
        messages=[{"role": "user", "content": "Reply with OK"}],
        model=model,
        max_tokens=4,
        temperature=0,
        keep_alive="10m",
    )


def unload_model(model: str | None = None) -> None:
    """Free VRAM before image / Hypit / speech jobs."""
    model = (model or _cfg_model()).strip()
    base = _local_base_url()
    try:
        if base:
            root = base.rstrip("/").removesuffix("/v1")
            _http_json(
                "POST",
                f"{root}/api/generate",
                {"model": model, "keep_alive": 0, "prompt": ""},
                timeout=60,
            )
            return
        with pod_session() as (ip, ssh_port, _pod_id):
            _ensure_serve(ip, ssh_port)
            cmd = (
                _remote_env()
                + f"{REMOTE_BIN} stop {shlex.quote(model)} 2>/dev/null || true; "
                f"curl -sf -X POST http://{DEFAULT_HOST}:{_cfg_port()}/api/generate "
                f"-d {shlex.quote(json.dumps({'model': model, 'keep_alive': 0, 'prompt': ''}))} >/dev/null || true; "
                f"echo UNLOADED"
            )
            _ssh(ip, ssh_port, cmd + "\n", timeout=90)
    except Exception as exc:
        log.warning("runpod llm unload soft-fail: %s", type(exc).__name__)


def chat_completions(
    *,
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.15,
    max_tokens: int = 4096,
    response_format: dict | None = None,
    keep_alive: str | int | None = "10m",
    timeout: float = 180,
) -> dict:
    model = (model or _cfg_model()).strip()
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if response_format is not None:
        payload["response_format"] = response_format
    if keep_alive is not None:
        # Ollama OpenAI shim accepts keep_alive as extra body field.
        payload["keep_alive"] = keep_alive

    base = _local_base_url()
    if base:
        return _http_json("POST", f"{base.rstrip('/')}/chat/completions", payload, timeout=timeout)

    with pod_session() as (ip, ssh_port, _pod_id):
        _ensure_serve(ip, ssh_port)
        with _Tunnel(ip, ssh_port) as tunnel:
            return _http_json(
                "POST",
                f"{tunnel.base_url}/chat/completions",
                payload,
                timeout=timeout,
            )


def extract_message_content(data: dict) -> str:
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text") or "")
            elif isinstance(item, str):
                parts.append(item)
        content = "".join(parts)
    if not isinstance(content, str):
        raise RunpodLlmError("empty_content")
    content = content.strip()
    # Qwen3 may wrap reasoning in <think>...</think> before JSON.
    if "</think>" in content:
        content = content.split("</think>", 1)[-1].strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0].strip()
    if not content:
        raise RunpodLlmError("empty_content")
    return content
