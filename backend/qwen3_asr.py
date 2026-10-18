"""Client for the isolated Qwen3-ASR service. This module does not load weights."""

from __future__ import annotations

import json
import os
import socket
import uuid
from pathlib import Path

SOCKET_PATH = os.environ.get(
    "QWEN_ASR_SOCKET",
    "/mnt/volume_nyc1_1791446889637/qwen3-asr/asr.sock",
)


class QwenAsrError(RuntimeError):
    pass


def transcribe(video_path: Path, *, language: str | None = None, on_phase=None) -> dict:
    request = {
        "id": uuid.uuid4().hex,
        "audio": str(video_path),
        "language": language or "",
    }
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    conn.settimeout(1500)
    try:
        conn.connect(SOCKET_PATH)
    except OSError as exc:
        raise QwenAsrError("TRANSCRIPTION_PROVIDER_UNAVAILABLE") from exc
    try:
        conn.sendall((json.dumps(request) + "\n").encode())
        buffer = b""
        result = None
        while result is None:
            chunk = conn.recv(1024 * 1024)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.strip():
                    continue
                event = json.loads(line)
                phase = event.get("phase")
                if phase == "error":
                    raise QwenAsrError(event.get("error") or "TRANSCRIPTION_FAILED")
                if phase == "done":
                    result = event
                elif on_phase and phase:
                    on_phase(phase)
        if result is None:
            raise QwenAsrError("TRANSCRIPTION_FAILED")
        transcribe.last_info = result
        return result
    finally:
        conn.close()


transcribe.last_info = {}
