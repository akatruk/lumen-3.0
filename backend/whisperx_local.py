"""Local WhisperX / faster-whisper transcript helper.

Used at generation time only — never on project create.
Falls back by raising ImportError / RuntimeError so callers can use placeholder.
"""

from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np


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


def _load_wav_mono_f32(path: Path) -> np.ndarray:
    """Load PCM wav without PyAV (av/faster-whisper version conflicts)."""
    with wave.open(str(path), "rb") as fh:
        channels = fh.getnchannels()
        width = fh.getsampwidth()
        rate = fh.getframerate()
        frames = fh.readframes(fh.getnframes())
    if rate != 16000:
        raise RuntimeError(f"unexpected_wav_rate:{rate}")
    if width == 2:
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif width == 4:
        audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise RuntimeError(f"unsupported_wav_width:{width}")
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio


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
        audio = _load_wav_mono_f32(wav)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        lang = None
        if language:
            lang = language.split("-")[0].lower()
            if lang not in ("en", "ru", "zh"):
                lang = None
        segments, _info = model.transcribe(audio, language=lang, vad_filter=True)
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
