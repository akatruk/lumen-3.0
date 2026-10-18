"""Transcript providers — local Whisper preferred; never OpenRouter."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Protocol

from ..config import settings


class TranscriptProvider(Protocol):
    name: str

    def transcribe(self, video_path: Path, *, language: str | None = None) -> list[dict]:
        """Return [{start, end, text}, ...] in seconds."""


def _ffprobe_duration(path: Path) -> float:
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        text=True,
    )
    return float(json.loads(raw)["format"]["duration"])


class PlaceholderTranscriptProvider:
    """Silence-grid captions when ASR is unavailable — keeps pipeline unblocked."""

    name = "placeholder"

    def transcribe(self, video_path: Path, *, language: str | None = None, duration: float | None = None) -> list[dict]:
        if duration is None:
            try:
                from .. import media

                duration = float(media.probe(video_path)["duration"])
            except Exception:
                duration = float(_ffprobe_duration(video_path))
        duration = max(float(duration), 1.0)
        step = 8.0
        out = []
        t = 0.0
        i = 1
        while t < duration - 0.05:
            end = min(t + step, duration)
            out.append({"start": round(t, 3), "end": round(end, 3), "text": f"[segment {i}]"})
            t = end
            i += 1
        return out or [{"start": 0.0, "end": round(duration, 3), "text": "[audio]"}]


class Qwen3TranscriptProvider:
    """Local Qwen3-ASR. A missing service is a failure, not a smaller model."""

    name = "qwen3-asr"

    def transcribe(self, video_path: Path, *, language: str | None = None, on_phase=None) -> list[dict]:
        from ..qwen3_asr import transcribe

        result = transcribe(video_path, language=language, on_phase=on_phase)
        if result.get("speech") == "silence":
            return []
        return list(result.get("segments") or [])


class WhisperXTranscriptProvider:
    name = "whisperx"

    def transcribe(self, video_path: Path, *, language: str | None = None) -> list[dict]:
        from ..whisperx_local import transcribe_segments

        return transcribe_segments(video_path, language=language)


class UnavailableTranscriptProvider:
    """ASR could not be loaded. Callers must fail, not invent segments."""

    name = "unavailable"

    def transcribe(self, video_path: Path, *, language: str | None = None, duration: float | None = None) -> list[dict]:
        del video_path, language, duration
        raise ImportError("TRANSCRIPTION_PROVIDER_UNAVAILABLE")


def get_transcript_provider(name: str | None = None) -> TranscriptProvider:
    model = (getattr(settings, "asr_model", "") or "").strip()
    if model.startswith("Qwen/Qwen3-ASR"):
        return Qwen3TranscriptProvider()
    chosen = (name or getattr(settings, "transcript_provider", "auto") or "auto").strip().lower()
    if chosen == "placeholder":
        return PlaceholderTranscriptProvider()
    if chosen == "whisperx":
        return WhisperXTranscriptProvider()
    try:
        from .. import whisperx_local  # noqa: F401

        return WhisperXTranscriptProvider()
    except Exception:
        return UnavailableTranscriptProvider()
