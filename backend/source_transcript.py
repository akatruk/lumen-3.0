"""Verified source transcript. Placeholder grids are not speech."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .config import settings
from .language import detect_source_locale, resolve_locale
from .source_analysis import is_placeholder_transcript, source_checksum

TRANSCRIPT_VERSION = "source-transcript-1"
LOCALES = ("ru-RU", "en-US", "zh-CN")


class TranscriptError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def transcript_path(pid: str) -> Path:
    return settings.data_dir / pid / "localization" / "source-transcript.json"


def _row_text(row) -> str:
    if isinstance(row, dict):
        return str(row.get("text") or row.get("original") or "").strip()
    return str(getattr(row, "original", None) or getattr(row, "text", None) or "").strip()


def normalize_segments(rows) -> list[dict]:
    """Real timed lines only. A silence grid is not a transcript."""
    if is_placeholder_transcript(rows):
        raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
    out = []
    previous = -1.0
    for row in rows or []:
        if isinstance(row, dict):
            start = float(row.get("start") or 0)
            end = float(row.get("end") or 0)
        else:
            start = float(getattr(row, "start", 0) or 0)
            end = float(getattr(row, "end", 0) or 0)
        text = _row_text(row)
        if not text or end <= start:
            raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
        if start < previous - 0.05:
            raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
        previous = start
        out.append({"start": round(start, 3), "end": round(end, 3), "text": text})
    if not out:
        raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
    return out


def assert_coverage(segments: list[dict], duration: float | None) -> None:
    if not duration or duration <= 0:
        return
    end = max(float(row["end"]) for row in segments)
    if end < float(duration) - 3.0 and end < float(duration) * 0.9:
        raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")


def language_of(segments: list[dict], declared: str | None = None) -> str:
    text = " ".join(row["text"] for row in segments)
    detected = detect_source_locale(text)
    if detected not in LOCALES:
        raise TranscriptError("SOURCE_LANGUAGE_UNVERIFIED")
    if declared:
        try:
            declared_locale = resolve_locale(declared)
        except Exception as exc:
            raise TranscriptError("SOURCE_LANGUAGE_UNVERIFIED") from exc
        if declared_locale != detected:
            raise TranscriptError("SOURCE_LANGUAGE_UNVERIFIED")
        return declared_locale
    return detected


def build_record(
    *,
    project_id: str,
    source_checksum_value: str,
    segments: list[dict],
    provider: str,
    provenance: dict,
    declared_language: str | None = None,
    duration: float | None = None,
) -> dict:
    rows = normalize_segments(segments)
    assert_coverage(rows, duration)
    locale = language_of(rows, declared_language)
    stored = []
    for index, row in enumerate(rows, start=1):
        stored.append({
            "id": f"segment_{index:03d}",
            "text": row["text"],
            "start": row["start"],
            "end": row["end"],
        })
    provenance = provenance or {}
    return {
        "projectId": project_id,
        "sourceChecksum": source_checksum_value,
        "sourceLanguage": locale,
        "retrievalLocale": locale,
        "provider": provider,
        "modelId": provenance.get("modelId"),
        "modelVersion": provenance.get("modelVersion"),
        "configVersion": provenance.get("configVersion"),
        "transcriptVersion": TRANSCRIPT_VERSION,
        "segments": stored,
        "text": " ".join(row["text"] for row in stored),
        "status": "verified",
        "createdAt": time.time(),
        "provenance": provenance,
    }


def cache_matches_model(record: dict) -> bool:
    """Legacy small-model files stay valid. A different model version does not."""
    wanted = (getattr(settings, "asr_model", "small") or "small").strip()
    config = (getattr(settings, "asr_config_version", "") or "").strip()
    recorded = str(record.get("modelId") or "")
    recorded_config = str(record.get("configVersion") or "")
    provider = str(record.get("provider") or "")
    if provider == "fixture":
        return True
    if not recorded:
        if wanted != "small":
            return False
        return "small" in provider or provider in {"whisperx", "cached", "faster-whisper-small"}
    if wanted not in recorded and not recorded.endswith("/" + wanted) and f"faster-whisper-{wanted}" not in recorded:
        return False
    if recorded_config and config and recorded_config != config:
        return False
    return True


def load_verified(pid: str, source: Path) -> dict | None:
    path = transcript_path(pid)
    if not path.is_file() or not source.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(record, dict):
        return None
    if record.get("status") != "verified" or record.get("transcriptVersion") != TRANSCRIPT_VERSION:
        return None
    if record.get("projectId") != pid:
        return None
    if record.get("sourceChecksum") != source_checksum(source):
        return None
    try:
        normalize_segments(record.get("segments") or [])
        language_of(record.get("segments") or [], record.get("sourceLanguage"))
    except TranscriptError:
        return None
    return record


def save_verified(
    pid: str,
    source: Path,
    segments,
    *,
    provider: str,
    provenance: dict | None = None,
    declared_language: str | None = None,
    duration: float | None = None,
) -> dict:
    """Write the project transcript once the checksum matches. A valid cache is kept."""
    existing = load_verified(pid, source)
    if existing and cache_matches_model(existing):
        return existing
    record = build_record(
        project_id=pid,
        source_checksum_value=source_checksum(source),
        segments=segments,
        provider=provider,
        provenance=provenance or {},
        declared_language=declared_language,
        duration=duration,
    )
    path = transcript_path(pid)
    path.parent.mkdir(parents=True, exist_ok=True)
    if existing and path.is_file():
        label = str(existing.get("modelId") or existing.get("provider") or "previous").replace("/", "-")
        archive = path.with_name(f"source-transcript-{label}.json")
        if not archive.exists():
            archive.write_bytes(path.read_bytes())
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return record


def as_ranged_rows(record: dict) -> list[dict]:
    return [
        {
            "id": row.get("id") or f"segment_{index:03d}",
            "start": row["start"],
            "end": row["end"],
            "text": row["text"],
        }
        for index, row in enumerate(record.get("segments") or [], start=1)
    ]


def source_locale_for_rows(rows) -> str | None:
    """Language of a stored plan. Empty stays unset. A fake grid is rejected."""
    rows = list(rows or [])
    if not rows:
        return None
    if is_placeholder_transcript(rows):
        raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
    try:
        segments = normalize_segments(rows)
    except TranscriptError:
        raise
    return language_of(segments)
