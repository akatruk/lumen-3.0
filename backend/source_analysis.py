"""Deferred source analysis — runs at generation time, never on create.

Invariant: PROJECT CREATION MUST NOT REQUIRE AI INFERENCE.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from .config import settings
from .db import connect, update
from . import media
from .providers import get_director_provider, get_llm_provider, get_transcript_provider

ANALYSIS_VERSION = "source-v1"
_PLACEHOLDER_LINE = re.compile(r'^\[(segment\s+\d+|audio|no speech)\]$', re.I)


def is_placeholder_transcript(segments) -> bool:
    """True when ASR fell back to silence-grid labels like [segment 1]."""
    rows = list(segments or [])
    if not rows:
        return True
    texts = []
    for row in rows:
        if isinstance(row, dict):
            texts.append(str(row.get('text') or row.get('original') or row.get('en') or '').strip())
        else:
            texts.append(str(getattr(row, 'original', None) or getattr(row, 'en', None) or getattr(row, 'text', None) or '').strip())
    usable = [t for t in texts if t]
    if not usable:
        return True
    hits = sum(1 for t in usable if _PLACEHOLDER_LINE.match(t) or t in ('…', '...'))
    return hits >= max(1, (len(usable) + 1) // 2)


def _transcribe_source(source: Path, *, language: str, duration: float | None) -> tuple[list[dict], str]:
    """Real ASR when available. Stamp the provider that actually produced the lines."""
    transcript_provider = get_transcript_provider()
    try:
        if transcript_provider.name == "placeholder":
            segments = transcript_provider.transcribe(
                source, language=language, duration=duration
            )
        else:
            segments = transcript_provider.transcribe(source, language=language)
        used = transcript_provider.name
    except Exception:
        placeholder = get_transcript_provider("placeholder")
        segments = placeholder.transcribe(
            source, language=language, duration=duration
        )
        used = placeholder.name
    if is_placeholder_transcript(segments) and used != "placeholder":
        # Provider claimed success but returned silence-grid labels.
        used = "placeholder"
    return segments, used


def source_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def enrich_metadata(meta: dict, path: Path | None = None) -> dict:
    """Add orientation / fps / checksum fields without LLM."""
    out = dict(meta or {})
    w, h = int(out.get("width") or 0), int(out.get("height") or 0)
    if w and h:
        out["orientation"] = "portrait" if h > w else ("landscape" if w > h else "square")
    if path and path.is_file() and not out.get("source_checksum"):
        out["source_checksum"] = source_checksum(path)
    out.setdefault("analysis_version", ANALYSIS_VERSION)
    out.setdefault("fps", out.get("fps"))
    return out


def _cache_valid(meta: dict, path: Path, plan: dict | None = None) -> bool:
    if not path.is_file():
        return False
    if (meta or {}).get("analysis_version") != ANALYSIS_VERSION:
        return False
    cached = (meta or {}).get("source_checksum")
    if not cached:
        return False
    if cached != source_checksum(path):
        return False
    # Placeholder ASR must never block a real Create Video re-analysis.
    if (meta or {}).get("transcript_provider") == "placeholder":
        return False
    if plan is not None and is_placeholder_transcript((plan or {}).get("transcript")):
        return False
    return True


def plan_cache_hit(pid: str) -> bool:
    from .studio import state

    s = state(pid)
    if not s or not s.get("plan"):
        return False
    folder = settings.data_dir / pid
    with connect() as db:
        row = db.execute("SELECT metadata FROM projects WHERE id=?", (pid,)).fetchone()
    meta = json.loads(row["metadata"] or "{}") if row else {}
    return _cache_valid(meta, folder / "source", s.get("plan"))


def build_local_plan(pid: str, *, language: str = "en") -> dict:
    """Transcript + heuristic Director — no OpenRouter."""
    folder = settings.data_dir / pid
    source = folder / "source"
    meta = media.probe(source)
    meta = enrich_metadata(meta, source)
    if not (folder / "analysis.mp4").exists():
        media.prepare(source, folder)
        meta["preview_ready"] = True

    segments, transcript_name = _transcribe_source(
        source, language=language, duration=float(meta["duration"])
    )

    director = get_director_provider("none")  # local baseline — never silent LLM claim
    from .experience_memory import context_for_transcript
    plan = director.build_plan(
        duration=float(meta["duration"]),
        language=language,
        transcript=segments,
        dna=[],
        experience=context_for_transcript(pid, segments),
    )
    media.validate_analysis(plan, meta["duration"])
    return {
        "plan": plan,
        "metadata": meta,
        "transcript_provider": transcript_name,
        "director_provider": director.name,
        "director_mode": "heuristic",
        "analysis_quality": "local_baseline",
    }


def _stamp_director_mode(pid: str, *, director_mode: str, director_provider: str, analysis_quality: str, transcript_provider: str | None = None):
    """Persist explicit provider mode — heuristic must never look like LLM Director."""
    from .studio import state

    with connect() as db:
        current = state(pid, db) or {}
        context = dict(current.get("context") or {})
        context["director_mode"] = director_mode
        context["director_provider"] = director_provider
        context["analysis_quality"] = analysis_quality
        if transcript_provider:
            context["transcript_provider"] = transcript_provider
        db.execute(
            "UPDATE studio_projects SET context=? WHERE project_id=?",
            (json.dumps(context, ensure_ascii=False), pid),
        )


def ensure_analysis(pid: str, *, language: str | None = None, force: bool = False) -> dict:
    """Reuse cached plan when source checksum matches; else build at generation time.

    Create stays AI-free. Generation may use OpenRouter when LLM_PROVIDER=openrouter,
    or RunPod-local LLM when LLM_PROVIDER=runpod (fail-closed: RUNPOD_LLM_UNAVAILABLE).
    Otherwise heuristic with explicit director_mode — never silent LLM claims.
    """
    from .studio import state, validate_director

    folder = settings.data_dir / pid
    source = folder / "source"
    if not source.is_file():
        raise ValueError("source_missing")

    with connect() as db:
        row = db.execute("SELECT metadata, language FROM projects WHERE id=?", (pid,)).fetchone()
    meta = json.loads(row["metadata"] or "{}") if row else {}
    lang = language or (row["language"] if row else None) or "en"

    s = state(pid)
    if not force and s and s.get("plan") and _cache_valid(meta, source, s.get("plan")):
        mode = (s.get("context") or {}).get("director_mode") or meta.get("director_mode") or "unknown"
        return {
            "reused": True,
            "plan": s["plan"],
            "metadata": meta,
            "director_mode": mode,
            "director_provider": (s.get("context") or {}).get("director_provider") or meta.get("director_provider"),
            "analysis_quality": (s.get("context") or {}).get("analysis_quality") or meta.get("analysis_quality"),
        }

    llm = get_llm_provider()
    provider_name = (getattr(settings, "llm_provider", "none") or "none").strip().lower()

    if provider_name in ("runpod", "runpod_llm", "local_runpod"):
        from .providers.director import RunPodDirectorProvider
        from .runpod_llm import RUNPOD_LLM_UNAVAILABLE, RunpodLlmError

        if not llm.available():
            raise RunpodLlmError(RUNPOD_LLM_UNAVAILABLE)
        director = RunPodDirectorProvider()
        duration = float(meta.get("duration") or media.probe(source)["duration"])
        segments, transcript_name = _transcribe_source(
            source, language=lang, duration=duration
        )
        if not (folder / "analysis.mp4").exists():
            media.prepare(source, folder)
            meta = {**meta, "preview_ready": True}
        from .experience_memory import context_for_transcript
        plan = director.build_plan(
            duration=duration,
            language=lang,
            transcript=segments,
            dna=[],
            experience=context_for_transcript(pid, segments),
        )
        validate_director(plan, [])
        stamp = {
            "analysis_provider": transcript_name,
            "transcript_provider": transcript_name,
            "director_provider": "runpod",
            "director_mode": "runpod",
            "analysis_quality": "llm",
            "llm_model": getattr(settings, "runpod_llm_model", ""),
        }
        with connect() as db:
            db.execute(
                "UPDATE studio_projects SET plan=?,decisions=?,revision=revision+1 WHERE project_id=?",
                (plan.model_dump_json(), json.dumps([]), pid),
            )
        _stamp_director_mode(
            pid,
            director_mode="runpod",
            director_provider="runpod",
            analysis_quality="llm",
            transcript_provider=transcript_provider.name,
        )
        update(
            pid,
            analysis=plan.model_dump(exclude={"transfers"}),
            metadata={**meta, **stamp},
            status="ready",
            stage="ready",
            progress=100,
            error=None,
        )
        return {
            "reused": False,
            "plan": plan.model_dump(),
            "metadata": {**meta, **stamp},
            "provider": "runpod",
            "director_mode": "runpod",
            "director_provider": "runpod",
            "analysis_quality": "llm",
            "built_at": time.time(),
        }

    if llm.available() and provider_name in ("openrouter", "or"):
        from .studio import analyze
        from .db import project as load_project

        analyze(load_project(pid))
        _stamp_director_mode(
            pid,
            director_mode="openrouter",
            director_provider="openrouter",
            analysis_quality="llm",
        )
        with connect() as db:
            row = db.execute("SELECT metadata FROM projects WHERE id=?", (pid,)).fetchone()
        fresh_meta = json.loads(row["metadata"] or "{}") if row else meta
        update(
            pid,
            metadata={
                **fresh_meta,
                "director_mode": "openrouter",
                "director_provider": "openrouter",
                "analysis_quality": "llm",
            },
        )
        s = state(pid)
        return {
            "reused": False,
            "plan": s["plan"],
            "metadata": fresh_meta,
            "provider": "openrouter",
            "director_mode": "openrouter",
            "director_provider": "openrouter",
            "analysis_quality": "llm",
        }

    built = build_local_plan(pid, language=lang)
    plan = built["plan"]
    validate_director(plan, [])
    decisions = []
    legacy = plan.model_dump(exclude={"transfers"})
    stamp = {
        "analysis_provider": built["transcript_provider"],
        "transcript_provider": built["transcript_provider"],
        "director_provider": built["director_provider"],
        "director_mode": built["director_mode"],
        "analysis_quality": built["analysis_quality"],
    }
    with connect() as db:
        db.execute(
            "UPDATE studio_projects SET plan=?,decisions=?,revision=revision+1 WHERE project_id=?",
            (plan.model_dump_json(), json.dumps(decisions), pid),
        )
    _stamp_director_mode(
        pid,
        director_mode=built["director_mode"],
        director_provider=built["director_provider"],
        analysis_quality=built["analysis_quality"],
        transcript_provider=built["transcript_provider"],
    )
    update(
        pid,
        analysis=legacy,
        metadata={**meta, **built["metadata"], **stamp},
        status="ready",
        stage="ready",
        progress=100,
        error=None,
    )
    return {
        "reused": False,
        "plan": plan.model_dump(),
        "metadata": {**built["metadata"], **stamp},
        "provider": built["transcript_provider"],
        "director_mode": built["director_mode"],
        "director_provider": built["director_provider"],
        "analysis_quality": built["analysis_quality"],
        "built_at": time.time(),
    }
