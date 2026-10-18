"""Project passage overlay.

Shared code only applies a file that names one project. Copy, timestamps, and
asset ids live in that file. A label is kept only when the quote of its beat
contains it, and a plate is kept only when the reviewed picture supports it.
"""
from __future__ import annotations

import json
from pathlib import Path

_DIR = Path(__file__).resolve().parent / "experiments"


def _load(project_id: str | None) -> dict | None:
    if not project_id:
        return None
    path = _DIR / f"{project_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("projectId") != project_id:
        return None
    return data


def correct_transcript(rows, project_id: str | None):
    """Replace a confirmed token inside the row that still contains it."""
    config = _load(project_id)
    fixes = (config or {}).get("captions") or []
    if not fixes:
        return rows
    out = []
    for row in rows or []:
        if not isinstance(row, dict):
            out.append(row)
            continue
        start = round(float(row.get("start") or 0), 2)
        nxt = dict(row)
        for fix in fixes:
            if round(float(fix.get("start") or -1), 2) != start:
                continue
            find = str(fix.get("find") or "")
            replace = str(fix.get("replace") or "")
            if not find or find == replace:
                continue
            for key, value in list(nxt.items()):
                if isinstance(value, str) and find in value:
                    nxt[key] = value.replace(find, replace)
        out.append(nxt)
    return out


def _frames(ends: list[float], fps: int = 30) -> list[int]:
    cursor = 0
    weights = []
    for end in ends:
        target = int(round(float(end) * fps))
        weights.append(max(1, target - cursor))
        cursor = target
    return weights


def _stamp_plate(scene: dict, asset_id: str, quote: str) -> bool:
    from .visual_review import picture_supports, review_of

    if not picture_supports(asset_id, quote):
        return False
    row = review_of(asset_id) or {}
    scene["background"] = {
        "assetId": asset_id,
        "file": row.get("file"),
        "type": row.get("type") or "video",
        "kind": row.get("kind"),
        "visualGrounding": {
            "reviewed": True,
            "observed": row.get("visible") or "",
        },
    }
    speaker = dict(scene.get("speaker") or {})
    speaker["layout"] = "speaker_split_right"
    speaker["treatment"] = "speaker_split_right"
    speaker["framing"] = "split"
    speaker["visibility"] = "primary"
    scene["speaker"] = speaker
    composition = dict(scene.get("sceneComposition") or {})
    composition["speakerPresentation"] = "split"
    composition["editorial"] = "support"
    scene["sceneComposition"] = composition
    return True


def _clear_plate(scene: dict) -> None:
    background = dict(scene.get("background") or {})
    background["assetId"] = None
    background["file"] = None
    background["staged"] = None
    scene["background"] = background
    speaker = dict(scene.get("speaker") or {})
    speaker["layout"] = "speaker_fullscreen"
    speaker["treatment"] = "speaker_fullscreen"
    speaker["framing"] = "fullscreen"
    scene["speaker"] = speaker
    composition = dict(scene.get("sceneComposition") or {})
    composition["speakerPresentation"] = "fullscreen"
    composition["editorial"] = "speaker"
    scene["sceneComposition"] = composition
    scene["criteriaCards"] = []


def apply_passage_experiment(plan: dict, transcript, project_id: str | None, locale: str | None) -> dict:
    config = _load(project_id)
    beats = (config or {}).get("beats") or []
    scenes = [dict(scene) for scene in (plan or {}).get("scenes") or []]
    if not beats or len(beats) != len(scenes):
        return plan
    from .editorial_decision import labels_supported, quote_for_window

    ends = [float(beat["end"]) for beat in beats]
    weights = _frames(ends)
    starts = [0.0, *ends[:-1]]
    out_scenes = []
    for scene, beat, start, end in zip(scenes, beats, starts, ends):
        if beat.get("keep"):
            out_scenes.append(scene)
            continue
        quote = quote_for_window(transcript, start, end, locale)
        asset = beat.get("assetId")
        if asset:
            if not _stamp_plate(scene, str(asset), quote):
                _clear_plate(scene)
        else:
            _clear_plate(scene)
        labels = []
        for card in beat.get("labels") or []:
            title = str(card.get("title") or "").strip()
            if not title:
                continue
            labels.append({"title": title, "role": card.get("role") or "side", "explanation": ""})
        titles = [card["title"] for card in labels]
        if titles and labels_supported(titles, quote):
            scene["criteriaCards"] = labels
        else:
            scene["criteriaCards"] = []
        editorial = dict(scene.get("editorial") or {})
        editorial["quoteSeconds"] = [round(start, 3), round(end, 3)]
        editorial["purpose"] = "supporting-visual" if (scene.get("background") or {}).get("assetId") else editorial.get("purpose")
        scene["editorial"] = editorial
        out_scenes.append(scene)
    out = dict(plan)
    out["scenes"] = out_scenes
    out["beatWeights"] = weights
    out["passageExperiment"] = config.get("id") or project_id
    return out
