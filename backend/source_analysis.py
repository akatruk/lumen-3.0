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

    director = get_director_provider("none")  # always heuristic here
    plan = director.build_plan(
        duration=float(meta["duration"]),
        language=language,
        transcript=segments,
        dna=[],
    )
    media.validate_analysis(plan, meta["duration"])
    return {"plan": plan, "metadata": meta, "transcript_provider": transcript_provider.name}


def ensure_analysis(pid: str, *, language: str | None = None, force: bool = False) -> dict:
    """Reuse cached plan when source checksum matches; else build locally.

    Does not call OpenRouter unless llm_provider=openrouter and force legacy analyze.
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
        return {"reused": True, "plan": s["plan"], "metadata": meta}

    llm = get_llm_provider()
    # Optional paid path only when explicitly configured AND flag allows legacy analyze.
    if (
        llm.available()
        and getattr(settings, "llm_provider", "none") in ("openrouter", "or")
        and not getattr(settings, "fast_project_creation_enabled", True)
    ):
        from .studio import analyze
        from .db import project as load_project

        analyze(load_project(pid))
        s = state(pid)
        return {"reused": False, "plan": s["plan"], "metadata": meta, "provider": "openrouter"}

    built = build_local_plan(pid, language=lang)
    plan = built["plan"]
    validate_director(plan, [])
    decisions = []
    legacy = plan.model_dump(exclude={"transfers"})
    with connect() as db:
        db.execute(
            "UPDATE studio_projects SET plan=?,decisions=?,revision=revision+1 WHERE project_id=?",
            (plan.model_dump_json(), json.dumps(decisions), pid),
        )
    update(
        pid,
        analysis=legacy,
        metadata={**meta, **built["metadata"], "analysis_provider": built["transcript_provider"]},
        status="ready",
        stage="ready",
        progress=100,
        error=None,
    )
    return {
        "reused": False,
        "plan": plan.model_dump(),
        "metadata": built["metadata"],
        "provider": built["transcript_provider"],
        "built_at": time.time(),
    }
