"""Deferred source analysis — runs at generation time, never on create.

Invariant: PROJECT CREATION MUST NOT REQUIRE AI INFERENCE.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from .config import settings
from .db import connect, update
from . import media
from .providers import get_director_provider, get_llm_provider, get_transcript_provider

ANALYSIS_VERSION = "source-v1"


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


def _cache_valid(meta: dict, path: Path) -> bool:
    if not path.is_file():
        return False
    if (meta or {}).get("analysis_version") != ANALYSIS_VERSION:
        return False
    cached = (meta or {}).get("source_checksum")
    if not cached:
        return False
    return cached == source_checksum(path)


def plan_cache_hit(pid: str) -> bool:
    from .studio import state

    s = state(pid)
    if not s or not s.get("plan"):
        return False
    folder = settings.data_dir / pid
    with connect() as db:
        row = db.execute("SELECT metadata FROM projects WHERE id=?", (pid,)).fetchone()
    meta = json.loads(row["metadata"] or "{}") if row else {}
    return _cache_valid(meta, folder / "source")


def build_local_plan(pid: str, *, language: str = "en") -> dict:
    """Transcript + heuristic Director — no OpenRouter."""
    folder = settings.data_dir / pid
    source = folder / "source"
    meta = media.probe(source)
    meta = enrich_metadata(meta, source)
    if not (folder / "analysis.mp4").exists():
        media.prepare(source, folder)
        meta["preview_ready"] = True

    transcript_provider = get_transcript_provider()
    try:
        if transcript_provider.name == "placeholder":
            segments = transcript_provider.transcribe(
                source, language=language, duration=float(meta["duration"])
            )
        else:
            segments = transcript_provider.transcribe(source, language=language)
    except Exception:
        placeholder = get_transcript_provider("placeholder")
        segments = placeholder.transcribe(
            source, language=language, duration=float(meta["duration"])
        )

    director = get_director_provider("none")  # local baseline — never silent LLM claim
    plan = director.build_plan(
        duration=float(meta["duration"]),
        language=language,
        transcript=segments,
        dna=[],
    )
    media.validate_analysis(plan, meta["duration"])
    return {
        "plan": plan,
        "metadata": meta,
        "transcript_provider": transcript_provider.name,
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

    Create stays AI-free. Generation may use OpenRouter only when LLM_PROVIDER=openrouter
    and a key is present — otherwise heuristic with explicit director_mode.
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
    if not force and s and s.get("plan") and _cache_valid(meta, source):
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
    # Generation-time LLM Director (optional). Fast create remains AI-free either way.
    if llm.available() and getattr(settings, "llm_provider", "none") in ("openrouter", "or"):
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
