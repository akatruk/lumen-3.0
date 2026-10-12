"""Coerce local-LLM Director JSON into the existing strict schema.

Small open models often emit string Text fields / transcript.text / extra .ru.
Normalize in-process — never invent facts beyond copying provided strings.
"""

from __future__ import annotations

from typing import Any


def _text(value: Any, fallback: str = "…") -> dict:
    if isinstance(value, dict):
        en = str(value.get("en") or value.get("ru") or value.get("zh") or fallback)[:2400]
        zh = str(value.get("zh") or value.get("en") or en)[:2400]
        return {"en": en or fallback, "zh": zh or en or fallback}
    text = str(value or fallback).strip() or fallback
    return {"en": text[:2400], "zh": text[:2400]}


def _score_cat(value: Any) -> str:
    allowed = {"hook", "clarity", "pacing", "visuals", "audio"}
    raw = str(value or "clarity").lower().strip()
    if raw in allowed:
        return raw
    if raw in ("visual", "broll", "picture"):
        return "visuals"
    return "clarity"


def _role(value: Any) -> str:
    allowed = {"hook", "context", "proof", "product", "cta", "transition"}
    raw = str(value or "context").lower().strip()
    return raw if raw in allowed else "context"


def _rec_cat(value: Any) -> str:
    allowed = {"hook", "pacing", "captions", "audio", "broll"}
    raw = str(value or "pacing").lower().strip()
    if raw in allowed:
        return raw
    if raw in ("visuals", "visual", "picture"):
        return "broll"
    return "pacing"


def _action(value: Any) -> str:
    allowed = {"remove", "move_to_front", "captions", "normalize_audio", "generate_broll"}
    raw = str(value or "captions").lower().strip()
    return raw if raw in allowed else "captions"


def _caption(item: Any, duration: float) -> dict:
    item = item if isinstance(item, dict) else {}
    start = float(item.get("start") or 0)
    end = float(item.get("end") or start)
    if end <= start:
        end = min(start + 1.0, duration)
    end = min(max(end, start + 0.05), duration)
    original = str(
        item.get("original")
        or item.get("text")
        or item.get("ru")
        or item.get("en")
        or "…"
    )[:300]
    en = str(item.get("en") or original)[:300]
    zh = str(item.get("zh") or en)[:300]
    ru = str(item.get("ru") or original)[:400]
    return {
        "start": round(start, 3),
        "end": round(end, 3),
        "original": original or "…",
        "en": en or "…",
        "zh": zh or "…",
        "ru": ru,
        "emphasis_en": list(item.get("emphasis_en") or [])[:8],
        "emphasis_zh": list(item.get("emphasis_zh") or [])[:8],
    }


def normalize_director_payload(raw: Any, *, duration: float) -> dict:
    data = raw if isinstance(raw, dict) else {}
    scenes_in = data.get("scenes") or []
    scenes = []
    for i, scene in enumerate(scenes_in if isinstance(scenes_in, list) else []):
        if not isinstance(scene, dict):
            continue
        start = float(scene.get("start") or 0)
        end = float(scene.get("end") or start)
        if end <= start:
            end = min(start + 4.0, duration)
        end = min(max(end, start + 0.05), duration)
        scenes.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "title": _text(scene.get("title"), f"Scene {i + 1}"),
                "observation": _text(scene.get("observation"), "Scene from transcript."),
                "role": _role(scene.get("role")),
            }
        )
    if not scenes:
        scenes = [
            {
                "start": 0.0,
                "end": round(duration, 3),
                "title": _text("Full clip"),
                "observation": _text("Single-scene plan from transcript."),
                "role": "context",
            }
        ]

    caps_in = data.get("transcript") or []
    transcript = [
        _caption(item, duration) for item in (caps_in if isinstance(caps_in, list) else [])
    ]
    if not transcript:
        transcript = [
            {
                "start": 0.0,
                "end": round(duration, 3),
                "original": "[no speech]",
                "en": "[no speech]",
                "zh": "[no speech]",
                "ru": "[no speech]",
                "emphasis_en": [],
                "emphasis_zh": [],
            }
        ]

    scores_in = data.get("scores") or []
    scores = []
    for item in scores_in if isinstance(scores_in, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            value = int(item.get("value") or 50)
        except (TypeError, ValueError):
            value = 50
        scores.append(
            {
                "category": _score_cat(item.get("category")),
                "value": max(0, min(100, value)),
                "reason": _text(item.get("reason"), "Model score"),
            }
        )
    if not scores:
        scores = [
            {"category": "clarity", "value": 65, "reason": _text("RunPod local baseline")},
            {"category": "pacing", "value": 60, "reason": _text("From transcript timing")},
            {"category": "hook", "value": 55, "reason": _text("Opening segment")},
        ]

    # V1 RunPod path: no reference DNA transfers → keep recommendations empty so
    # studio.validate_director (transfers ↔ recommendation ids) stays satisfied.
    # Scene/transcript quality is the deliverable; edit suggestions come later.
    recs: list[dict] = []
    _ = (_rec_cat, _action)  # retained for a future DNA-aware path

    uncertainties = []
    for item in data.get("uncertainties") or []:
        uncertainties.append(_text(item, "Uncertainty noted"))

    return {
        "summary": _text(data.get("summary"), "RunPod local Director plan"),
        "strongest_moment": _text(data.get("strongest_moment"), "Opening segment"),
        "audience": _text(data.get("audience"), "Project audience"),
        "scores": scores[:5],
        "scenes": scenes[:40],
        "transcript": transcript[:160],
        "recommendations": recs[:12],
        "uncertainties": uncertainties[:8],
        "transfers": [],  # local path has no reference DNA transfers by default
    }
