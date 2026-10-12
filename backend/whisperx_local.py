"""Local WhisperX / faster-whisper transcript helper.

Used at generation time only — never on project create.
Falls back by raising ImportError / RuntimeError so callers can use placeholder.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def _extract_wav(video_path: Path, wav_path: Path) -> None:
    subprocess.check_call(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(wav_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def transcribe_segments(video_path: Path, *, language: str | None = None) -> list[dict]:
    """Return [{start, end, text}, ...] using faster-whisper when installed."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ImportError("faster_whisper_unavailable") from exc

    video_path = Path(video_path)
    model_size = "small"
    with tempfile.TemporaryDirectory(prefix="lumen-asr-") as tmp:
        wav = Path(tmp) / "audio.wav"
        _extract_wav(video_path, wav)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        lang = None
        if language:
            lang = language.split("-")[0].lower()
            if lang not in ("en", "ru", "zh"):
                lang = None
        segments, _info = model.transcribe(str(wav), language=lang, vad_filter=True)
        out = []
        for seg in segments:
            text = (seg.text or "").strip()
            if not text:
                continue
            out.append(
                {
                    "start": round(float(seg.start), 3),
                    "end": round(float(seg.end), 3),
                    "text": text,
                }
            )
        return out
