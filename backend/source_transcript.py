"""Verified source transcript. Placeholder grids are not speech."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .config import settings
from .language import decide_source_language, resolve_locale
from .source_analysis import is_placeholder_transcript, source_checksum

TRANSCRIPT_VERSION = "source-transcript-1"
LOCALES = ("ru-RU", "en-US", "zh-CN")


class TranscriptError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _archive_current(path: Path) -> None:
    if not path.is_file():
        return
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previous = {}
    label = str((previous or {}).get("modelId") or (previous or {}).get("provider") or "previous")
    label = label.replace("/", "-")
    archive = path.with_name(f"source-transcript-{label}.json")
    if not archive.exists():
        archive.write_bytes(path.read_bytes())


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
        item = {"start": round(start, 3), "end": round(end, 3), "text": text}
        if isinstance(row, dict) and row.get("words"):
            item["words"] = row["words"]
        out.append(item)
    if not out:
        raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
    return out


def assert_coverage(segments: list[dict], duration: float | None) -> None:
    if not duration or duration <= 0:
        return
    end = max(float(row["end"]) for row in segments)
    if end < float(duration) - 3.0 and end < float(duration) * 0.9:
        raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")


def language_decision(segments: list[dict], declared: str | None = None, *, detection: dict | None = None) -> dict:
    """Resolved source locale, or an unverified decision. Output language is not an input."""
    decision = decide_source_language(
        segments,
        user_source_language=None,
        detection=detection or {},
    )
    if declared:
        try:
            declared_locale = resolve_locale(declared)
        except Exception as exc:
            raise TranscriptError("SOURCE_LANGUAGE_UNVERIFIED") from exc
        if decision.get("sourceLanguage") != declared_locale:
            raise TranscriptError("SOURCE_LANGUAGE_UNVERIFIED")
    return decision


def language_of(segments: list[dict], declared: str | None = None, *, detection: dict | None = None) -> str:
    decision = language_decision(segments, declared, detection=detection)
    locale = decision.get("sourceLanguage")
    if locale not in LOCALES:
        raise TranscriptError("SOURCE_LANGUAGE_UNVERIFIED")
    return locale


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
    decision = language_decision(rows, declared_language, detection=provenance)
    locale = decision.get("sourceLanguage")
    if locale not in LOCALES:
        raise TranscriptError("SOURCE_LANGUAGE_UNVERIFIED")
    stored = []
    for index, row in enumerate(rows, start=1):
        item = {
            "id": f"segment_{index:03d}",
            "text": row["text"],
            "start": row["start"],
            "end": row["end"],
        }
        if row.get("words"):
            item["words"] = row["words"]
        stored.append(item)
    provenance = provenance or {}
    return {
        "projectId": project_id,
        "sourceChecksum": source_checksum_value,
        "sourceLanguage": locale,
        "languageStatus": decision.get("status"),
        "languageProvenance": decision.get("languageProvenance"),
        "detectedLanguage": decision.get("detectedLanguage"),
        "languageProbability": decision.get("languageProbability"),
        "forcedTranscriptionLanguage": decision.get("forcedTranscriptionLanguage"),
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
        "rawText": provenance.get("rawText") or "",
        "uncertain": list(provenance.get("uncertain") or []),
        "alignment": provenance.get("alignment") or {},
        "corrections": [],
        "provenance": provenance,
    }


def cache_matches_model(record: dict) -> bool:
    """Legacy small-model files stay valid. A different model version does not."""
    if record.get("corrections"):
        return True
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
    if not cache_matches_model(record):
        return None
    try:
        normalize_segments(record.get("segments") or [])
        language_of(
            record.get("segments") or [],
            record.get("sourceLanguage"),
            detection=record.get("provenance") if isinstance(record.get("provenance"), dict) else None,
        )
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
    _archive_current(path)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return record


def save_silence(pid: str, source: Path, *, provenance: dict, duration: float | None) -> dict:
    """A file with no speech. This is not a transcript and not a success."""
    record = {
        "projectId": pid,
        "sourceChecksum": source_checksum(source),
        "transcriptVersion": TRANSCRIPT_VERSION,
        "status": "silence",
        "speech": "silence",
        "segments": [],
        "text": "",
        "duration": duration,
        "modelId": provenance.get("modelId"),
        "modelVersion": provenance.get("modelVersion"),
        "createdAt": time.time(),
        "provenance": provenance,
    }
    path = transcript_path(pid)
    path.parent.mkdir(parents=True, exist_ok=True)
    _archive_current(path)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return record


def load_silence(pid: str, source: Path) -> dict | None:
    path = transcript_path(pid)
    if not path.is_file() or not source.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(record, dict) or record.get("status") != "silence":
        return None
    if record.get("sourceChecksum") != source_checksum(source):
        return None
    if not cache_matches_model(record):
        return None
    return record


def apply_correction(pid: str, source: Path, segment_id: str, text: str) -> dict:
    """Keep the raw recognition and append an auditable correction. Retries must not replace it."""
    record = load_verified(pid, source)
    if not record:
        raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
    updated = json.loads(json.dumps(record))
    found = False
    for row in updated["segments"]:
        if row["id"] == segment_id:
            row["text"] = text
            found = True
    if not found:
        raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
    updated["corrections"] = list(updated.get("corrections") or [])
    updated["corrections"].append({
        "segmentId": segment_id,
        "text": text,
        "at": time.time(),
    })
    updated["text"] = " ".join(row["text"] for row in updated["segments"])
    path = transcript_path(pid)
    _archive_current(path)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return updated


def as_ranged_rows(record: dict) -> list[dict]:
    return [
        {"start": row["start"], "end": row["end"], "text": row["text"]}
        for row in record.get("segments") or []
    ]


def source_language_decision(rows) -> dict:
    """Source-language decision for plan rows. Empty stays unset. A fake grid is rejected."""
    rows = list(rows or [])
    if not rows:
        return {
            "status": "unset",
            "sourceLanguage": None,
            "languageProvenance": None,
            "dubbing": "blocked",
        }
    if is_placeholder_transcript(rows):
        raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
    segments = normalize_segments(rows)
    return language_decision(segments)


def source_locale_for_rows(rows) -> str | None:
    """Resolved source locale. Empty or uncertain stays unset. A fake grid is rejected."""
    decision = source_language_decision(rows)
    if decision.get("status") != "resolved":
        return None
    return decision.get("sourceLanguage")
