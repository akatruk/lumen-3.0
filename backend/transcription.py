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
    from .source_transcript import TranscriptError, save_silence, save_verified
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
        from .language import explicit_user_source_language
        from .source_transcript import load_silence
        from .studio import state

        silence = load_silence(pid, source)
        if silence:
            mark_transcription(pid, "transcription_silence")
            return silence
        # projects.language is the requested output. It must not force ASR.
        explicit = explicit_user_source_language((state(pid) or {}).get("context"))

        def on_phase(phase: str) -> None:
            mark_transcription(pid, phase)

        call = {
            "language": explicit,
            "duration": duration,
            "project_id": pid,
        }
        import inspect
        if "on_phase" in inspect.signature(_transcribe_source).parameters:
            call["on_phase"] = on_phase
        try:
            segments, provider = _transcribe_source(source, **call)
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
        from .qwen3_asr import transcribe as qwen_transcribe

        if provider == "qwen3-asr":
            info = dict(getattr(qwen_transcribe, "last_info", {}) or {})
        else:
            info = dict(getattr(transcribe_segments, "last_info", {}) or {})
        if info.get("speech") == "silence":
            saved = save_silence(
                pid,
                source,
                provenance={
                    "provider": provider,
                    "modelId": (info.get("recognition") or {}).get("model") or "Qwen/Qwen3-ASR-1.7B",
                    "modelVersion": (info.get("recognition") or {}).get("revision"),
                    "speech": "silence",
                },
                duration=duration,
            )
            mark_transcription(pid, "transcription_silence")
            return saved
        if not segments:
            raise TranscriptError("SOURCE_TRANSCRIPT_UNAVAILABLE")
        recognition = info.get("recognition") if isinstance(info.get("recognition"), dict) else {}
        names = {"Chinese": "zh", "English": "en", "Russian": "ru"}
        forced_code = names.get(info.get("forcedLanguage") or "")
        detected_code = None if forced_code else names.get(info.get("language") or "")
        saved = save_verified(
            pid,
            source,
            segments,
            provider=provider,
            provenance={
                "provider": provider,
                "modelId": recognition.get("model") or info.get("modelId"),
                "modelVersion": recognition.get("revision") or info.get("modelVersion"),
                "configVersion": info.get("configVersion") or (
                    "qwen3-asr-1.7b-bf16-cpu-align-0.6b-1" if provider == "qwen3-asr" else ""
                ),
                "detectedLanguage": detected_code or info.get("detectedLanguage"),
                "languageProbability": info.get("languageProbability"),
                "languageMode": "forced" if forced_code else info.get("languageMode"),
                "forcedTranscriptionLanguage": forced_code or info.get("forcedTranscriptionLanguage"),
                "projectLanguage": current.get("language"),
                "modelLoadSeconds": recognition.get("loadSeconds") or info.get("modelLoadSeconds"),
                "inferSeconds": recognition.get("inferSeconds") or info.get("inferSeconds"),
                "rawText": info.get("text") or "",
                "uncertain": info.get("uncertain") or [],
                "alignment": info.get("alignment") or {},
                "humanVerified": False,
            },
            duration=duration,
        )
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    mark_transcription(pid, "transcription_analyzing")
    try:
        from .source_brief import write_brief

        write_brief(pid, saved)
    except Exception:
        saved = {**saved, "analysisError": "source_brief_failed"}
    fresh = project(pid) or {}
    merged = dict(fresh.get("metadata") or {})
    merged["analysis_stale"] = True
    merged["transcription"] = TERMINAL_OK
    merged["source_language"] = saved.get("sourceLanguage")
    merged["source_language_status"] = saved.get("languageStatus")
    merged["source_language_provenance"] = saved.get("languageProvenance")
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
    from .source_transcript import TranscriptError, load_verified, source_language_decision
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
        decision = source_language_decision(rows)
    except TranscriptError as exc:
        raise ValueError(exc.code) from exc
    if decision.get("status") in ("uncertain", "mixed"):
        raise ValueError("SOURCE_LANGUAGE_UNVERIFIED")
    source_locale = decision.get("sourceLanguage")
    if not source_locale:
        raise ValueError("SOURCE_TRANSCRIPT_UNAVAILABLE")
    resolved = resolve_voice(
        source_language=source_locale,
        target_language=locale,
        voice=(payload or {}).get("voice"),
        language_status=decision.get("status") if decision.get("status") in ("uncertain", "mixed") else None,
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
