"""One CPU transcription job per source checksum, model, and config."""

from __future__ import annotations

import fcntl
import json
import time
import uuid
from pathlib import Path

from .config import settings
from .db import connect, project, update

TERMINAL_OK = "transcription_completed"
PENDING = "transcription_pending"
RUNNING = "transcription_running"
FAILED = "transcription_failed"


def mark_transcription(pid: str, state: str, **extra) -> None:
    current = project(pid) or {}
    meta = dict(current.get("metadata") or {})
    meta["transcription"] = state
    for key, value in extra.items():
        if value is None:
            meta.pop(key, None)
        else:
            meta[key] = value
    update(pid, metadata=meta)


def _payload_matches(raw: str, checksum: str) -> bool:
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return False
    model = (getattr(settings, "asr_model", "small") or "small").strip()
    config = (getattr(settings, "asr_config_version", "") or "").strip()
    return (
        payload.get("checksum") == checksum
        and payload.get("model") == model
        and payload.get("config") == config
    )


def enqueue_transcription(db, pid: str, checksum: str) -> str | None:
    """Queue at most one active job for this checksum + model + config."""
    if not checksum:
        return None
    model = (getattr(settings, "asr_model", "small") or "small").strip()
    config = (getattr(settings, "asr_config_version", "") or "").strip()
    rows = db.execute(
        "SELECT id, project_id, status, payload FROM jobs WHERE kind='transcribe' AND status IN ('queued','running')"
    ).fetchall()
    for row in rows:
        if not _payload_matches(row["payload"], checksum):
            continue
        if row["project_id"] == pid:
            return row["id"]
        payload = json.loads(row["payload"] or "{}")
        waiters = list(payload.get("waiters") or [])
        if pid not in waiters:
            waiters.append(pid)
            payload["waiters"] = waiters
            db.execute(
                "UPDATE jobs SET payload=?, updated=? WHERE id=?",
                (json.dumps(payload), time.time(), row["id"]),
            )
        return row["id"]
    now = time.time()
    job_id = uuid.uuid4().hex
    db.execute(
        "INSERT INTO jobs VALUES(?,?,?,?,?,?,?)",
        (
            job_id,
            pid,
            "transcribe",
            json.dumps({
                "checksum": checksum,
                "model": model,
                "config": config,
                "attempts": 0,
                "waiters": [],
            }),
            "queued",
            now,
            now,
        ),
    )
    return job_id


def recover_transcribe_job(db, row) -> str:
    """Requeue a transcription interrupted by a worker restart. Two attempts."""
    payload = json.loads(row["payload"] or "{}")
    attempts = int(payload.get("attempts") or 0) + 1
    payload["attempts"] = attempts
    if attempts <= 2:
        db.execute(
            "UPDATE jobs SET status='queued', payload=?, updated=? WHERE id=?",
            (json.dumps(payload), time.time(), row["id"]),
        )
        return "requeued"
    current = db.execute("SELECT metadata FROM projects WHERE id=?", (row["project_id"],)).fetchone()
    meta = json.loads((current["metadata"] if current else None) or "{}")
    meta["transcription"] = FAILED
    meta["transcription_error"] = "worker_interrupted"
    db.execute(
        "UPDATE projects SET metadata=?, updated=? WHERE id=?",
        (json.dumps(meta), time.time(), row["project_id"]),
    )
    return "failed"


def _lock_for(checksum: str):
    from .whisperx_local import cache_dir

    path = cache_dir() / "locks" / f"{checksum}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    fcntl.flock(handle, fcntl.LOCK_EX)
    return handle


def persist_source_transcript(pid: str) -> dict:
    """Transcribe once and store a verified project transcript. Cache hits skip the model."""
    from .source_analysis import _transcribe_source
    from .source_transcript import TranscriptError, save_verified
    from .whisperx_local import transcribe_segments

    current = project(pid)
    if not current:
        raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
    source = settings.data_dir / pid / "source"
    if not source.is_file():
        raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
    meta = dict(current.get("metadata") or {})
    from .source_analysis import source_checksum

    checksum = meta.get("source_checksum") or source_checksum(source)
    mark_transcription(pid, RUNNING)
    lock = _lock_for(str(checksum))
    try:
        duration = float(meta.get("duration") or 0) or None
        try:
            segments, provider = _transcribe_source(
                source,
                language=str(current.get("language") or ""),
                duration=duration,
                project_id=pid,
            )
        except TranscriptError:
            raise
        except Exception as exc:
            code = str(exc)
            if code in {
                "TRANSCRIPTION_PROVIDER_UNAVAILABLE",
                "TRANSCRIPTION_FAILED",
                "TRANSCRIPTION_TIMEOUT",
                "SOURCE_TRANSCRIPT_UNAVAILABLE",
                "SOURCE_LANGUAGE_UNVERIFIED",
            }:
                raise TranscriptError(code) from exc
            raise TranscriptError("TRANSCRIPTION_FAILED") from exc
        info = dict(getattr(transcribe_segments, "last_info", {}) or {})
        if not segments:
            raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
        saved = save_verified(
            pid,
            source,
            segments,
            provider=provider,
            provenance={
                "provider": provider,
                "modelId": info.get("modelId"),
                "modelVersion": info.get("modelVersion"),
                "configVersion": info.get("configVersion"),
                "detectedLanguage": info.get("detectedLanguage"),
                "languageProbability": info.get("languageProbability"),
                "modelLoadSeconds": info.get("modelLoadSeconds"),
                "inferSeconds": info.get("inferSeconds"),
            },
            duration=duration,
        )
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    fresh = project(pid) or {}
    merged = dict(fresh.get("metadata") or {})
    merged["transcription"] = TERMINAL_OK
    merged["source_language"] = saved.get("sourceLanguage")
    merged["transcript_version"] = saved.get("transcriptVersion")
    merged["transcription_model"] = saved.get("modelId")
    merged.pop("transcription_error", None)
    update(pid, metadata=merged)
    return saved


def run_job(p, payload):
    saved = persist_source_transcript(p["id"])
    waiters = list((payload or {}).get("waiters") or [])
    for other in waiters:
        try:
            persist_source_transcript(other)
        except Exception:
            mark_transcription(other, FAILED, transcription_error="TRANSCRIPTION_FAILED")
    return saved


def materialize_director_payload(p, payload):
    """Fill a deferred Create Video job after the transcript exists."""
    from .language import resolve_voice, short_code
    from .source_analysis import ensure_analysis
    from .source_transcript import TranscriptError, load_verified, source_locale_for_rows
    from .studio import state
    from .visual_variation import plan_for_request

    pid = p["id"]
    source = settings.data_dir / pid / "source"
    if not load_verified(pid, source):
        try:
            persist_source_transcript(pid)
        except TranscriptError as exc:
            raise ValueError(exc.code) from exc
    locale = (payload or {}).get("target_language") or (payload or {}).get("language")
    try:
        ensure_analysis(pid, language=locale, keep_status=True)
    except TranscriptError as exc:
        raise ValueError(exc.code) from exc
    s = state(pid)
    rows = (s.get("plan") or {}).get("transcript") or []
    try:
        source_locale = source_locale_for_rows(rows)
    except TranscriptError as exc:
        raise ValueError(exc.code) from exc
    if not source_locale:
        raise ValueError("SOURCE_TRANSCRIPT_UNAVAILABLE")
    resolved = resolve_voice(
        source_language=source_locale,
        target_language=locale,
        voice=(payload or {}).get("voice"),
    )
    if resolved["status"] == "VOICE_SETUP_REQUIRED":
        raise ValueError("MISSING_TARGET_LANGUAGE_VOICE")
    energy = (payload or {}).get("visual_energy") or "balanced"
    editing = (payload or {}).get("editing") or {}
    visual = plan_for_request(
        settings.data_dir,
        pid,
        (payload or {}).get("visual_variation") or "automatic",
        energy if energy in ("calm", "balanced", "dynamic") else "balanced",
        locale,
        editing=editing,
    )
    visual = {**visual, "language": locale}
    return {
        **(payload or {}),
        "await_transcript": False,
        "language": short_code(locale) if locale else (payload or {}).get("language"),
        "target_language": locale,
        "source_language": source_locale,
        "voice": (payload or {}).get("voice") or resolved.get("voiceId"),
        "voice_resolution": resolved,
        "dubbed": resolved["mode"] == "dubbed",
        "plan": s.get("plan") or {},
        "transcript": rows,
        "visual_plan": {**visual, "transcript": rows},
        "editing_controls": visual.get("editingControls") or editing,
        "director_mode": "heuristic",
    }
