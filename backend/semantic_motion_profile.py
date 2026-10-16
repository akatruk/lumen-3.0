"""Per-generation opt-in for evidence-gated semantic motion.

The global V14–V18 flags and SEMANTIC_NUMERIC_RANGE_ENABLED stay at their
defaults. A Create Video job that names this profile runs the existing
classifiers for that job only.
"""
from __future__ import annotations

import re
from typing import Any

PROFILE = "evidence_gated_v1"
_UNVERIFIED_UNIT = {"泰国", "泰诸"}
_FAKE_STEP = re.compile(r"^(?:步骤|Step|Шаг)\s*\d+$")


def selected(value: str | None) -> bool:
    return value == PROFILE


def with_segment_ids(transcript: list | None) -> list[dict]:
    """Studio captions omit the id that the verified transcript already has.

    The heuristic plan copies segments in order and drops the id. The index
    matches source-transcript.json (`segment_001`…). A row that already has
    an id keeps it.
    """
    rows = []
    for index, row in enumerate(transcript or [], start=1):
        if hasattr(row, "model_dump"):
            row = row.model_dump()
        if not isinstance(row, dict):
            continue
        row = dict(row)
        if not row.get("id"):
            row["id"] = f"segment_{index:03d}"
        rows.append(row)
    return rows


def apply_profile(plan: dict, transcript: list | None, *, locale: str | None) -> dict:
    """Existing V14 selection plus numeric range, then the evidence gate.

    Does not call V15, V16, V17, or V18. Does not set the process-wide flags.
    """
    from . import director_v14, semantic_numeric_range
    from .director_evidence import apply_evidence_gate

    transcript = with_segment_ids(transcript)
    out = director_v14.apply_semantic_motion(plan, transcript, locale=locale, force=True)
    out = semantic_numeric_range.apply_numeric_range(out, transcript, locale=locale, force=True)
    out = apply_evidence_gate(out, transcript, locale=locale)
    out["semanticMotionProfile"] = PROFILE
    return bind_graphic_lifecycle(out, transcript)


def bind_graphic_lifecycle(plan: dict, transcript: list | None) -> dict:
    """Drop a graphic whose display interval is not its evidence interval.

    An unverified ASR unit is removed from the picture. The numbers stay when
    they are grounded in the quote. One bad graphic does not fail the plan.
    """
    from .director_evidence import scene_windows
    from .semantic_numeric_range import parameters_grounded

    rows = list(transcript or [])
    windows = scene_windows(plan, rows)
    rejections: list[dict[str, Any]] = list(plan.get("semanticMotionRejections") or [])
    scenes = []
    for index, scene in enumerate(plan.get("scenes") or []):
        scene = dict(scene)
        window = windows[index] if index < len(windows) else None
        scene["criteriaCards"] = _cards_inside(scene.get("criteriaCards") or [], window, rejections)
        typography = dict(scene.get("typography") or {})
        if typography.get("cards"):
            typography["cards"] = _cards_inside(typography.get("cards") or [], window, rejections)
            scene["typography"] = typography
        payload = scene.get("semanticMotionV14")
        if not isinstance(payload, dict) or not payload.get("componentId"):
            scenes.append(scene)
            continue
        kept, reason = _accept_payload(payload, parameters_grounded)
        if reason:
            scene.pop("semanticMotionV14", None)
            rejections.append({
                "sceneId": scene.get("sceneId"),
                "componentId": payload.get("componentId"),
                "reason": reason,
                "sourceQuote": (payload.get("evidence") or {}).get("sourceQuote"),
            })
        else:
            scene["semanticMotionV14"] = kept
        scenes.append(scene)
    out = dict(plan)
    out["scenes"] = scenes
    out["semanticMotionRejections"] = rejections
    return out


def _cards_inside(cards: list, window: tuple[float, float] | None, rejections: list[dict[str, Any]]) -> list:
    kept = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        stamp = (card.get("evidence") or {}).get("sourceTimestamp")
        if window and isinstance(stamp, (list, tuple)) and len(stamp) == 2:
            try:
                start, end = float(stamp[0]), float(stamp[1])
            except (TypeError, ValueError):
                kept.append(card)
                continue
            if end < window[0] - 0.05 or start > window[1] + 0.05:
                rejections.append({
                    "sceneId": None,
                    "componentId": "criteria_card",
                    "reason": "stale_after_evidence",
                    "sourceQuote": card.get("title"),
                })
                continue
        kept.append(card)
    return kept


def _segment_ids(payload: dict) -> list[str]:
    evidence = payload.get("evidence") or {}
    ids = [str(item) for item in (evidence.get("segmentIds") or []) if item]
    if not ids and evidence.get("segmentId"):
        ids = [str(evidence["segmentId"])]
    return ids


def _accept_payload(payload: dict, grounded) -> tuple[dict | None, str | None]:
    evidence = payload.get("evidence") or {}
    stamp = evidence.get("sourceTimestamp")
    output = payload.get("outputTime")
    if not isinstance(stamp, (list, tuple)) or len(stamp) != 2:
        return None, "missing_source_time"
    if not _segment_ids(payload):
        return None, "missing_source_segment_ids"
    if not isinstance(output, (list, tuple)) or len(output) != 2:
        return None, "missing_display_interval"
    try:
        evidence_start, evidence_end = float(stamp[0]), float(stamp[1])
        display_start, display_end = float(output[0]), float(output[1])
    except (TypeError, ValueError):
        return None, "missing_display_interval"
    # The last ordered label may hold for about a second after its line.
    # A graphic that runs into the next topic is still rejected.
    if display_end > evidence_end + 1.5 or display_start < evidence_start - 0.35:
        return None, "stale_after_evidence"
    kept = dict(payload)
    if kept.get("visualIntent") == "numeric_range":
        if not grounded(kept):
            return None, "ungrounded_range"
        rng = dict(kept.get("range") or {})
        unit = str(rng.get("unit") or "")
        if unit in _UNVERIFIED_UNIT:
            rng["unit"] = ""
            rng.pop("currency", None)
            kept["range"] = rng
            kept["unitOmitted"] = "asr_unit_unverified"
        elif str(rng.get("currency") or "") == "泰铢" and "泰铢" not in str(evidence.get("sourceQuote") or ""):
            return None, "unverified_currency"
    steps = []
    for step in kept.get("steps") or []:
        label = str(step.get("label") if isinstance(step, dict) else step)
        if _FAKE_STEP.match(label):
            continue
        steps.append(step)
    if kept.get("visualIntent") == "process_timeline":
        if len(steps) < 2:
            return None, "missing_ordered_labels"
        kept["steps"] = steps
    kept["lifecycle"] = {
        "evidence_start": evidence_start,
        "evidence_end": evidence_end,
        "display_start": display_start,
        "display_end": display_end,
        "source_segment_ids": _segment_ids(payload),
    }
    return kept, None
