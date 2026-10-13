"""Director V14 — semantic motion selection.

Flag SEMANTIC_MOTION_V14_ENABLED defaults off. When off, the plan is unchanged.
When on, a scene gets one evidence-backed component. Text-card stacks and
V11 BusinessMotion panels are removed on that scene so the diagram is the
explanation. Talking-head footage stays when nothing in the window is supported.

Does not invent percentages, shareholder counts, comparison sides, or steps.
"""
from __future__ import annotations

import os
import re
from typing import Any

from .director_v11_1 import extract_spoken_facts, shareholder_count_from_text
from .locale_consistency import locale_bucket

_CONTRAST = re.compile(
    r"different|differs|difference|versus|≠|不同|差异|отлич|则要求",
    re.I,
)
_AT_MOST = re.compile(r"less than|at most|不超过|не более|менее|通常不超过|generally less", re.I)
_AT_LEAST = re.compile(r"at least|至少|не менее|минимум", re.I)
_SPECIFICITY = {
    "ownership_split": 5,
    "shareholder_network": 4,
    "business_comparison": 3,
    "process_timeline": 2,
    "capital_flow": 1,
}
_INVESTOR = re.compile(r"investor|инвестор|投资人|投资者", re.I)
_LIST_EN = re.compile(
    r"([A-Z][^,.]{2,32}),\s+([^,.]{2,32})\s+and\s+([A-Za-z][^,.]{2,32}?)(?:\s+all\b|\s+watch\b|\s+would\b|,|\.|$)",
    re.I,
)
_ZH_KNOWN = ("银行开户", "工作证", "签证申请")
_PARTIES = (
    (("中国", "泰国"), ("China", "Thailand"), ("Китай", "Таиланд")),
)


def enabled() -> bool:
    raw = os.environ.get("SEMANTIC_MOTION_V14_ENABLED", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _labels(bucket: str) -> dict[str, dict[str, str]]:
    return {
        "en": {
            "capital": "Capital",
            "company": "Company",
            "investor": "Investor",
            "shareholder": "Shareholder",
            "shareholders": "Shareholders",
            "foreign": "Foreign capital",
        },
        "ru": {
            "capital": "Капитал",
            "company": "Компания",
            "investor": "Инвестор",
            "shareholder": "Акционер",
            "shareholders": "Акционеры",
            "foreign": "Иностранный капитал",
        },
        "zh": {
            "capital": "资本",
            "company": "公司",
            "investor": "投资人",
            "shareholder": "股东",
            "shareholders": "股东",
            "foreign": "外资",
        },
    }[bucket if bucket in {"en", "ru", "zh"} else "en"]


def _party_pair(text: str, bucket: str) -> tuple[str, str] | None:
    for zh, en, ru in _PARTIES:
        if all(name in text for name in zh) or all(name.lower() in text.lower() for name in en):
            if bucket == "zh":
                return zh
            if bucket == "ru":
                return ru
            return en
    return None


def _steps_from_quote(text: str, bucket: str) -> list[str] | None:
    match = _LIST_EN.search(text or "")
    en_steps = None
    if match:
        steps = [part.strip(" .") for part in match.groups()]
        if len(steps) >= 3 and all(len(s.split()) <= 6 for s in steps):
            en_steps = [s[:1].upper() + s[1:] if s else s for s in steps]
    zh_steps = list(_ZH_KNOWN) if text and all(p in text for p in _ZH_KNOWN) else None
    if bucket == "zh":
        return zh_steps or en_steps
    if bucket == "en":
        return en_steps or None
    return en_steps or zh_steps


def _evidence(segment: dict[str, Any], quote: str) -> dict[str, Any]:
    start = segment.get("start")
    end = segment.get("end")
    stamp: list[float] | None = None
    if start is not None and end is not None:
        stamp = [float(start), float(end)]
    return {
        "segmentId": segment.get("id"),
        "sourceTimestamp": stamp,
        "sourceQuote": quote,
        "factClass": "source_stated",
    }


def classify_quote(text: str, segment: dict[str, Any], *, locale: str) -> list[dict[str, Any]]:
    """Return zero or more payloads justified by this quote, best first."""
    if not text or not text.strip():
        return []
    bucket = locale_bucket(locale) or "en"
    labels = _labels(bucket)
    evidence = _evidence(segment, text)
    out: list[dict[str, Any]] = []

    facts = extract_spoken_facts(text)
    percents = [p for p in facts.get("percentages") or [] if 0 < p <= 100]
    if percents and re.search(r"capital|ownership|ratio|доля|比例|外资|капитал", text, re.I):
        qualifier = "exact"
        if _AT_MOST.search(text):
            qualifier = "at_most"
        elif _AT_LEAST.search(text):
            qualifier = "at_least"
        # One number per spoken percentage. Never add 100 - p.
        values = []
        seen: set[float] = set()
        for value in percents:
            if value in seen:
                continue
            seen.add(value)
            values.append({
                "value": value,
                "label": labels["foreign"],
                "unit": "%",
                "qualifier": qualifier,
            })
        out.append({
            "componentId": "motion.ownership_split.v1",
            "version": "v14.1",
            "visualIntent": "ownership_split",
            "locale": locale,
            "values": values,
            "labels": {},
            "evidence": evidence,
        })

    count = shareholder_count_from_text(text)
    structure = re.search(r"shareholder|акционер|股东", text, re.I)
    if count and structure:
        prefix = "≥" if _AT_LEAST.search(text) else ""
        out.append({
            "componentId": "motion.shareholder_network.v1",
            "version": "v14.1",
            "visualIntent": "shareholder_network",
            "locale": locale,
            "company": labels["company"],
            "showCount": True,
            "nodeCount": int(count),
            "countPrefix": prefix,
            "labels": {"node": labels["shareholder"], "company": labels["company"]},
            "evidence": evidence,
        })
    elif structure and re.search(r"structure|структур|结构", text, re.I):
        out.append({
            "componentId": "motion.shareholder_network.v1",
            "version": "v14.1",
            "visualIntent": "shareholder_network",
            "locale": locale,
            "company": labels["company"],
            "showCount": False,
            "labels": {"group": labels["shareholders"], "company": labels["company"]},
            "shareholders": [labels["shareholders"]],
            "evidence": evidence,
        })

    pair = _party_pair(text, bucket)
    if pair and _CONTRAST.search(text):
        out.append({
            "componentId": "motion.business_comparison.v1",
            "version": "v14.1",
            "visualIntent": "business_comparison",
            "locale": locale,
            "left": pair[0],
            "right": pair[1],
            "operator": "≠",
            "evidence": evidence,
        })

    steps = _steps_from_quote(text, bucket)
    if steps and len(steps) >= 3:
        out.append({
            "componentId": "motion.process_timeline.v1",
            "version": "v14.1",
            "visualIntent": "process_timeline",
            "locale": locale,
            "steps": [{"label": step, "evidence": text} for step in steps],
            "evidence": evidence,
        })

    capital = re.search(r"capital|注册资本|капитал|出资|投资", text, re.I)
    if capital and not percents:
        entities = []
        connections = []
        if _INVESTOR.search(text):
            entities.append({"id": "investor", "label": labels["investor"]})
        entities.append({"id": "capital", "label": labels["capital"]})
        entities.append({"id": "company", "label": labels["company"]})
        for a, b in zip(entities, entities[1:]):
            connections.append({"from": a["id"], "to": b["id"]})
        out.append({
            "componentId": "motion.capital_flow.v1",
            "version": "v14.1",
            "visualIntent": "capital_flow",
            "locale": locale,
            "entities": entities,
            "connections": connections,
            "evidence": evidence,
        })
    return out


def _windows(plan: dict, transcript: list[dict]) -> list[tuple[float, float]]:
    scenes = plan.get("scenes") or []
    weights = list(plan.get("beatWeights") or [])
    if len(weights) != len(scenes):
        weights = [1.0] * len(scenes)
    total = sum(weights) or 1.0
    horizon = 0.0
    for row in transcript:
        try:
            horizon = max(horizon, float(row.get("end") or 0))
        except (TypeError, ValueError):
            continue
    horizon = max(horizon, float(plan.get("durationSeconds") or 0) or 0, 1.0)
    cursor = 0.0
    spans = []
    for weight in weights:
        dur = horizon * (weight / total)
        spans.append((cursor, cursor + dur))
        cursor += dur
    return spans


def _choose_layout(scene: dict) -> tuple[str, str]:
    speaker = str((scene.get("speaker") or {}).get("layout") or "")
    if "split" in speaker:
        if "left" in speaker:
            return "speaker_visual", "right"
        return "speaker_visual", "left"
    # Full-bleed speaker: overlay stays under the face. Full frame is opt-in
    # only when the speaker is already a PIP / cutaway.
    if "pip" in speaker or "cutaway" in speaker:
        return "full_frame", "left"
    return "overlay", "left"


def _suppress_text_cards(scene: dict) -> dict:
    scene = dict(scene)
    typ = dict(scene.get("typography") or {})
    typ["cards"] = []
    typ["cardMode"] = "none"
    typ.pop("steps", None)
    typ.pop("stepsTitle", None)
    scene["typography"] = typ
    scene.pop("businessMotion", None)
    scene.pop("stepsTitle", None)
    scene.pop("steps", None)
    scene["criteriaCards"] = []
    motion = dict(scene.get("semanticMotion") or {})
    motion["display"] = "omit"
    scene["semanticMotion"] = motion
    comp = dict(scene.get("composition") or {})
    comp["floatObject"] = None
    comp["suppressConcepts"] = True
    comp["suppressHeadline"] = True
    scene["composition"] = comp
    return scene


def apply_semantic_motion(
    plan: dict,
    transcript: list | None = None,
    *,
    locale: str | None = None,
    force: bool = False,
) -> dict:
    out = dict(plan)
    if not enabled() and not force:
        out["semanticMotionV14Enabled"] = False
        return out
    locale = locale or out.get("language") or "en-US"
    rows = []
    for row in transcript or out.get("transcript") or []:
        if hasattr(row, "model_dump"):
            row = row.model_dump()
        if isinstance(row, dict):
            rows.append(row)
    spans = _windows(out, rows)
    proposals: list[tuple[int, int, dict[str, Any]]] = []
    for row in rows:
        try:
            seg_start = float(row.get("start") or 0)
            seg_end = float(row.get("end") or 0)
        except (TypeError, ValueError):
            continue
        mid = (seg_start + seg_end) / 2
        index = 0
        for i, (start, end) in enumerate(spans):
            if start <= mid < end or i == len(spans) - 1:
                index = i
                if start <= mid < end:
                    break
        quote = str(row.get("original") or row.get("text") or "")
        blob = " ".join(str(row.get(key) or "") for key in ("original", "text", "en", "zh", "ru"))
        found = classify_quote(blob, {**row, "id": row.get("id")}, locale=locale)
        if not found:
            continue
        payload = found[0]
        payload["evidence"] = {
            **payload["evidence"],
            "sourceQuote": quote or payload["evidence"].get("sourceQuote"),
        }
        spec = _SPECIFICITY.get(payload["visualIntent"], 0)
        if payload["visualIntent"] == "shareholder_network" and payload.get("showCount"):
            spec = 6
        proposals.append((spec, index, payload))
    proposals.sort(key=lambda item: (-item[0], item[1]))
    assigned: dict[int, dict[str, Any]] = {}
    used: set[str] = set()
    scene_count = len(out.get("scenes") or [])
    for _spec, index, payload in proposals:
        intent = payload["visualIntent"]
        if intent in used:
            continue
        target = index if index not in assigned else None
        if target is None:
            for delta in (1, -1, 2, -2):
                j = index + delta
                if 0 <= j < scene_count and j not in assigned:
                    target = j
                    break
        if target is None:
            continue
        assigned[target] = payload
        used.add(intent)
    scenes_out = []
    usage = []
    for index, scene in enumerate(out.get("scenes") or []):
        scene = dict(scene)
        best = assigned.get(index)
        if best:
            layout, side = _choose_layout(scene)
            if best.get("visualIntent") == "ownership_split" and layout == "overlay":
                layout = "full_frame"
            theme = None
            bm = scene.get("businessMotion") or {}
            if isinstance(bm, dict):
                theme = bm.get("sceneTheme")
                side = bm.get("mediaSide") or side
            best["layout"] = layout
            best["mediaSide"] = side
            if theme:
                best["sceneTheme"] = theme
            scene = _suppress_text_cards(scene)
            scene["semanticMotionV14"] = best
            used.add(best["visualIntent"])
            usage.append({
                "sceneId": scene.get("sceneId"),
                "componentId": best["componentId"],
                "visualIntent": best["visualIntent"],
                "layout": layout,
                "segmentId": (best.get("evidence") or {}).get("segmentId"),
                "sourceQuote": (best.get("evidence") or {}).get("sourceQuote"),
                "factClass": "source_stated",
            })
        scenes_out.append(scene)
    out["scenes"] = scenes_out
    out["semanticMotionV14Enabled"] = True
    out["semanticMotionV14Usage"] = usage
    out["semanticMotionV14Version"] = "v14.1"
    return out
