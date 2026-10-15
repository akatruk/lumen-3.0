"""CPU faster-whisper. Model weights stay on the media volume when it is mounted."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

from .config import settings

MODEL_REPO = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
}


def cache_dir() -> Path:
    """Volume when mounted, otherwise data/asr-models. Never the repo root."""
    raw = (getattr(settings, "asr_model_cache", "") or "").strip()
    if raw:
        path = Path(raw)
    else:
        volume = Path("/mnt/volume_nyc1_1791446889637")
        if volume.is_dir():
            path = volume / "lumen-asr"
        else:
            path = settings.data_dir / "asr-models"
    path.mkdir(parents=True, exist_ok=True)
    (path / "tmp").mkdir(parents=True, exist_ok=True)
    (path / "locks").mkdir(parents=True, exist_ok=True)
    (path / "transcripts").mkdir(parents=True, exist_ok=True)
    return path


def model_id() -> str:
    size = (getattr(settings, "asr_model", "small") or "small").strip()
    return MODEL_REPO.get(size, f"Systran/faster-whisper-{size}")


def config_version() -> str:
    return (getattr(settings, "asr_config_version", "cpu-int8-vad-1") or "cpu-int8-vad-1").strip()


def _file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def shared_transcript_path(checksum: str) -> Path:
    size = (getattr(settings, "asr_model", "small") or "small").strip()
    name = f"{size}-{config_version()}.json"
    return cache_dir() / "transcripts" / checksum / name


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
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
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
    """Return [{start, end, text}, ...]. last_info holds model and language metadata."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ImportError("TRANSCRIPTION_PROVIDER_UNAVAILABLE") from exc

    video_path = Path(video_path)
    size = (getattr(settings, "asr_model", "small") or "small").strip()
    root = cache_dir()
    os.environ["HF_HOME"] = str(root)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(root / "hub")
    os.environ["XDG_CACHE_HOME"] = str(root)
    with tempfile.TemporaryDirectory(prefix="lumen-asr-", dir=root / "tmp") as tmp:
        wav = Path(tmp) / "audio.wav"
        try:
            _extract_wav(video_path, wav)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("TRANSCRIPTION_FAILED") from exc
        audio = _load_wav_mono_f32(wav)
        import time
        from importlib.metadata import version

        started = time.perf_counter()
        model = WhisperModel(
            size,
            device="cpu",
            compute_type="int8",
            download_root=str(root / "hub"),
        )
        load_seconds = time.perf_counter() - started
        lang = None
        if language:
            lang = language.split("-")[0].lower()
            if lang not in ("en", "ru", "zh"):
                lang = None
        infer_started = time.perf_counter()
        segments, info = model.transcribe(
            audio,
            language=lang,
            vad_filter=True,
            beam_size=1,
            best_of=1,
            temperature=0.0,
            condition_on_previous_text=False,
        )
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
        wall = time.perf_counter() - infer_started
        try:
            fw = version("faster-whisper")
            ct = version("ctranslate2")
        except Exception:
            fw, ct = "1.2.1", "4.8.3"
        transcribe_segments.last_info = {
            "modelId": model_id(),
            "modelVersion": f"faster-whisper=={fw};ctranslate2=={ct};compute=int8;device=cpu",
            "configVersion": config_version(),
            "detectedLanguage": getattr(info, "language", None),
            "languageProbability": getattr(info, "language_probability", None),
            "modelLoadSeconds": round(load_seconds, 3),
            "inferSeconds": round(wall, 3),
            "checksum": _file_checksum(video_path),
        }
        return out


transcribe_segments.last_info = {}
