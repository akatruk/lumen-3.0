"""Passage retrieval. Keyword overlap alone is not a match."""

from __future__ import annotations

from pathlib import Path

GENERIC = {
    "business", "meeting", "video", "people", "office", "company", "corporate",
    "professional", "success", "team", "work", "the", "and", "for", "with",
    "商业", "会议", "视频", "公司", "办公室",
    "бизнес", "встреча", "видео", "офис", "компания",
}
BLOCKED_STATUS = {"quarantined", "rejected", "duplicate", "corrupt", "needs_review", "unreviewed", "restricted", "planned"}


def _meaning(text: str) -> set[str]:
    """English tags for a Chinese concept come from the library alias table."""
    words = _words(text)
    try:
        from media.library.search import _query_words, normalize_query
    except ImportError:
        return words
    expanded = {word for word in _query_words(normalize_query(text or "")) if word not in GENERIC and len(word) > 1}
    return words | expanded


def _overlap(start: float, end: float, seg_start: float, seg_end: float) -> float:
    return max(0.0, min(end, seg_end) - max(start, seg_start))


def _words(text: str) -> set[str]:
    out = set()
    token = []
    for char in (text or "").lower():
        if char.isalnum() or "\u4e00" <= char <= "\u9fff":
            token.append(char)
        elif token:
            out.add("".join(token))
            token = []
    if token:
        out.add("".join(token))
    return {word for word in out if word not in GENERIC and len(word) > 1}


def select_asset(concept: str | None, quote: str, assets: list[dict]) -> dict:
    """Return a real asset or NO_MATCH. Generic vocabulary cannot authorize footage."""
    specific = _meaning(concept or "") | _meaning(quote or "")
    rejected = []
    if not specific:
        return {"status": "NO_MATCH", "reason": "no_specific_concept", "rejected": rejected}
    chosen = None
    for asset in assets or []:
        status = str(asset.get("status") or asset.get("reviewStatus") or "reviewed")
        if status in BLOCKED_STATUS:
            rejected.append({"id": asset.get("id"), "reason": "ineligible", "status": status})
            continue
        if not asset.get("id") or not asset.get("file"):
            rejected.append({"id": asset.get("id"), "reason": "missing_file"})
            continue
        file_name = str(asset.get("file") or "")
        if file_name.endswith(".webm") or "premium3d" in file_name or str(asset.get("id") or "").startswith("l3d_"):
            rejected.append({"id": asset.get("id"), "reason": "unsupported_plate"})
            continue
        if "/layers/" in file_name.replace("\\", "/"):
            rejected.append({"id": asset.get("id"), "reason": "layer_fragment"})
            continue
        if asset.get("root") and not (Path(str(asset["root"])) / file_name).is_file():
            rejected.append({"id": asset.get("id"), "reason": "missing_file"})
            continue
        blob = " ".join(str(asset.get(key) or "") for key in ("title", "description", "tags", "caption", "category"))
        if "type is added later" in blob.casefold():
            rejected.append({"id": asset.get("id"), "reason": "unfinished_asset"})
            continue
        overlap = specific & _meaning(blob)
        if not overlap:
            rejected.append({"id": asset.get("id"), "reason": "no_meaning_overlap"})
            continue
        score = len(overlap)
        if str(asset.get("category") or "") == "metaphor":
            score -= 2
        if str(asset.get("visualFamily") or "") == "line":
            score -= 1
        candidate = {
            "status": "selected",
            "assetId": asset["id"],
            "file": asset["file"],
            "reason": "meaning_overlap:" + ",".join(sorted(overlap)),
            "_score": score,
        }
        if chosen is None or score > chosen["_score"]:
            if chosen is not None:
                rejected.append({"id": chosen["assetId"], "reason": "lower_rank"})
            chosen = candidate
        else:
            rejected.append({"id": asset.get("id"), "reason": "lower_rank"})
    if chosen is None:
        return {"status": "NO_MATCH", "reason": "no_relevant_asset", "rejected": rejected}
    chosen.pop("_score", None)
    chosen["rejected"] = rejected
    return chosen


def apply_passage_media(plan: dict, pid: str, transcript: list | None = None) -> dict:
    """Clear template queries when the semantic plan says the speaker should stay."""
    from .semantic_planner import PlannerError, load_valid

    ids = set()
    times = {}
    for index, row in enumerate(transcript or [], start=1):
        if not isinstance(row, dict):
            continue
        sid = row.get("id") or f"segment_{index:03d}"
        ids.add(sid)
        times[sid] = (float(row.get("start") or 0), float(row.get("end") or 0))
    try:
        semantic = load_valid(pid, ids) if ids else None
    except PlannerError:
        raise
    if not semantic:
        return plan
    out = dict(plan)
    scenes = []
    for scene in out.get("scenes") or []:
        scene = dict(scene)
        start = float(scene.get("start") or 0)
        end = float(scene.get("end") or start)
        related = []
        for passage in semantic["passages"]:
            covered = 0.0
            for sid in passage["segment_ids"]:
                if sid not in times:
                    continue
                seg_start, seg_end = times[sid]
                covered += _overlap(start, end, seg_start, seg_end)
            if covered > 0:
                related.append(passage)
        if not related:
            scenes.append(scene)
            continue
        needs = {item["visual_need"] for item in related}
        if needs <= {"talking_head"} or all(not item.get("visual_concept") for item in related):
            scene["query"] = None
            background = dict(scene.get("background") or {})
            for key in ("assetId", "file", "conceptId"):
                background.pop(key, None)
            scene["background"] = background
            scene["mediaDecision"] = {"status": "NO_MATCH", "reason": "talking_head"}
        scenes.append(scene)
    out["scenes"] = scenes
    out["semanticPlan"] = {
        "topic": semantic.get("topic"),
        "transcriptVersion": semantic.get("transcript_version"),
        "planner": semantic.get("planner"),
    }
    return out


def _index(transcript):
    ids, times, text = set(), {}, {}
    for index, row in enumerate(transcript or [], start=1):
        if not isinstance(row, dict):
            continue
        sid = row.get("id") or f"segment_{index:03d}"
        ids.add(sid)
        times[sid] = (float(row.get("start") or 0), float(row.get("end") or 0))
        text[sid] = str(row.get("text") or "")
    return ids, times, text


def _scene_from_passage(index: int, start: float, end: float, passage: dict) -> dict:
    quote = str(passage.get("quote") or "")
    concept = passage.get("visual_concept") or None
    executed = passage.get("executed_treatment") or (
        "talking_head" if passage.get("visual_need") == "talking_head" else "supporting_broll"
    )
    scene = {
        "sceneId": f"passage_{index:02d}",
        "start": round(start, 3),
        "end": round(end, 3),
        "quote": quote,
        "intent": passage.get("intent"),
        "narrativeRole": passage.get("narrative_role"),
        "kind": executed,
        "visualTreatment": passage.get("visual_treatment") or executed,
        "fallbackTreatment": passage.get("fallback_treatment"),
        "semanticReason": passage.get("semantic_reason"),
        "rendererCapability": {
            "treatment": executed,
            "component": passage.get("renderer_capability"),
            "stagedRequired": executed in {"supporting_broll", "pip"},
        },
        "query": None,
        "background": {},
        "speaker": {"layout": "speaker_fullscreen", "framing": "fullscreen"},
    }
    folded_quote = "".join(quote.split())
    card = str(concept) if concept and "".join(str(concept).split()) in folded_quote else quote[:48]
    if executed == "talking_head":
        scene["sceneComposition"] = {"speakerPresentation": "fullscreen"}
    elif executed in {"supporting_broll", "pip"}:
        scene["speaker"] = {
            "layout": "speaker_with_media" if executed == "pip" else "speaker_split_right",
            "framing": "pip" if executed == "pip" else "split",
        }
        scene["query"] = concept
        scene["background"] = {"query": concept}
    elif executed == "kinetic_typography":
        scene["cardMode"] = "progressive_one"
        scene["typography"] = {"cardMode": "progressive_one", "animate": "pop", "cards": [{"title": card, "explanation": ""}]}
        scene["execution"] = {"cardMode": "progressive_one"}
    elif executed == "process":
        scene["typography"] = {"steps": [quote[:80]], "stepsTitle": card[:40]}
    elif executed == "comparison":
        from .semantic_planner import _sides
        parts = _sides(str(concept or ""), quote)[:2]
        scene["cardMode"] = "progressive_one"
        scene["typography"] = {"cardMode": "progressive_one", "animate": "pop", "cards": [{"title": part, "explanation": ""} for part in parts]}
    return scene


def apply_semantic_beats(plan: dict, pid: str, transcript: list | None = None) -> dict:
    """Replace heuristic scene slices with passage windows taken from real segment times."""
    from .config import settings
    from .semantic_planner import PlannerError, load_valid

    ids, times, _text = _index(transcript)
    try:
        semantic = load_valid(pid, ids) if ids else None
    except PlannerError:
        raise
    if not semantic:
        if getattr(settings, "semantic_planner_required", False):
            raise PlannerError("PLANNER_UNAVAILABLE")
        return plan
    scenes = []
    ordered = []
    for passage in semantic["passages"]:
        span = [times[sid] for sid in passage["segment_ids"] if sid in times]
        if not span:
            raise PlannerError("PLANNER_INVALID")
        start = min(item[0] for item in span)
        end = max(item[1] for item in span)
        if end <= start:
            raise PlannerError("PLANNER_INVALID")
        ordered.append((start, end, passage))
    ordered.sort(key=lambda item: item[0])
    for index, (start, end, passage) in enumerate(ordered, start=1):
        scenes.append(_scene_from_passage(index, start, end, passage))
    out = dict(plan)
    out["scenes"] = scenes
    out["beatWeights"] = [round((scene["end"] - scene["start"]) * 1000) for scene in scenes]
    out["form"] = "semantic"
    out["director"] = "semantic_openrouter"
    out["directorMode"] = "semantic_openrouter"
    out.pop("heroObject", None)
    out["semanticPlan"] = {
        "topic": semantic.get("topic"),
        "model": semantic.get("model"),
        "planner": semantic.get("planner"),
    }
    return out


def revalidate_assets(plan: dict, pid: str, transcript: list | None = None, catalog: list[dict] | None = None) -> dict:
    """Drop assets that V11 query rewriting no longer supports."""
    from .config import settings
    from .semantic_planner import PlannerError, load_valid

    ids, times, _text = _index(transcript)
    semantic = load_valid(pid, ids) if ids else None
    if not semantic:
        if getattr(settings, "semantic_planner_required", False):
            raise PlannerError("PLANNER_UNAVAILABLE")
        return plan
    out = dict(plan)
    scenes = []
    for scene in out.get("scenes") or []:
        scene = dict(scene)
        start = float(scene.get("start") or 0)
        end = float(scene.get("end") or start)
        related = []
        for passage in semantic["passages"]:
            covered = sum(
                _overlap(start, end, *times[sid]) for sid in passage["segment_ids"] if sid in times
            )
            if covered > 0:
                related.append((covered, passage))
        related.sort(key=lambda item: item[0], reverse=True)
        passage = related[0][1] if related else None
        concept = (passage or {}).get("visual_concept") or None
        quote = (passage or {}).get("quote") or scene.get("quote") or ""
        executed = (passage or {}).get("executed_treatment") or (passage or {}).get("visual_need")
        if not passage or executed not in {"supporting_broll", "pip"} or not concept:
            reason = "no_passage" if not passage else (executed or "talking_head")
            _clear(scene, reason)
            if passage and executed not in {"supporting_broll", "pip"}:
                scene["mediaDecision"] = {"status": "NO_ASSET", "reason": reason, "searched": False}
            scenes.append(scene)
            continue
        assets = list(catalog or [])
        if catalog is None:
            assets = _library(concept)
        decision = select_asset(concept, quote, assets)
        scene["mediaDecision"] = decision
        if decision.get("status") != "selected":
            _clear(scene, decision.get("reason") or "NO_MATCH")
            scene["mediaDecision"] = decision
        else:
            background = dict(scene.get("background") or {})
            background["assetId"] = decision["assetId"]
            background["file"] = decision.get("file")
            background["query"] = concept
            scene["background"] = background
            scene["assetId"] = decision["assetId"]
            scene["query"] = concept
        scenes.append(scene)
    out["scenes"] = scenes
    return out


def _clear(scene: dict, reason: str) -> None:
    scene["query"] = None
    scene.pop("assetId", None)
    background = dict(scene.get("background") or {})
    for key in ("assetId", "file", "query", "conceptId"):
        background.pop(key, None)
    scene["background"] = background
    scene["mediaDecision"] = {"status": "NO_MATCH", "reason": reason}


def absolute_bounds(scenes: list[dict], duration: float, fps: int = 30) -> tuple[int, list[tuple[int, int]]]:
    """Same cut math as DirectorV3 beatsFromBounds. One frame is the tolerance."""
    frames = max(fps, round(float(duration) * fps))
    beats = []
    for scene in scenes:
        start = int(round(float(scene["start"]) * fps))
        end = int(round(float(scene["end"]) * fps))
        start = max(0, min(start, max(0, frames - 1)))
        end = max(start + 1, min(frames, end))
        beats.append((start, end))
    return frames, beats


def _library(concept: str) -> list[dict]:
    try:
        from search import search_assets
    except ImportError:
        return []
    root = Path(__file__).resolve().parent.parent / "media" / "library" / "out"
    found = search_assets(concept, limit=24) or []
    assets = []
    for hit in found:
        if not isinstance(hit, dict):
            continue
        file_name = hit.get("file") or hit.get("path")
        if not file_name or not (root / str(file_name)).is_file():
            continue
        description = hit.get("description") or hit.get("caption")
        if isinstance(description, dict):
            description = " ".join(str(value) for value in description.values())
        assets.append({
            "id": hit.get("id"),
            "file": file_name,
            "title": hit.get("title"),
            "description": description,
            "tags": " ".join(hit.get("tags") or []) if isinstance(hit.get("tags"), list) else hit.get("tags"),
            "status": hit.get("status") or hit.get("reviewStatus") or "reviewed",
            "category": hit.get("category"),
            "visualFamily": hit.get("visualFamily"),
        })
    return assets


def bound_semantic_duration(plan: dict, seconds: float) -> dict:
    """Respect the requested picture length without stretching speech windows."""
    from .semantic_planner import PlannerError
    scenes = []
    for scene in plan.get("scenes") or []:
        start = max(0.0, float(scene.get("start") or 0))
        end = min(float(seconds), float(scene.get("end") or 0))
        if end > start:
            scenes.append({**scene, "start": start, "end": end})
    if not scenes:
        raise PlannerError("PLANNER_INVALID", "no_passage_in_requested_duration")
    return {**plan, "scenes": scenes, "beatWeights": [round((s["end"] - s["start"]) * 1000) for s in scenes]}
