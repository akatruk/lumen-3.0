"""Motion design V18.

MOTION_DESIGN_V18_ENABLED defaults off. When on, a graphic is kept only when
the scene's own quote supports it. A country name is not an ownership diagram.
Talking-head is the correct picture when nothing in the speech matches a
component. Layout still comes from the V16 composer. This pass does not add
components and does not draw a second renderer.
"""
from __future__ import annotations

import os
import re
from typing import Any

from .director_v14 import _windows
from .scene_composer_v16 import CANVAS, _overlap

_EQUITY = re.compile(
    r"shareholder|ownership|equity|акционер|владен|доль|"
    r"股东|股权|注册资本|资本投入|控制权|外资比例|"
    r"capital investment|company structure|limited company|有限公司",
    re.I,
)
_BUSINESS = {
    "shareholder_structure",
    "equity_distribution",
    "capital_investment",
    "capital_flow",
    "company_ownership",
    "investment_flow",
    "company_control",
    "financial_comparison",
    "business_process",
}
_PACK_TITLES = {
    "资本", "股东", "控制权", "结构", "股权结构",
    "Capital", "Shareholders", "Control", "Structure", "Ownership structure",
    "Капитал", "Акционеры", "Контроль", "Структура", "Структура владения",
}
_PACK_STEPS = {
    "资本", "结构", "控制权",
    "Capital", "Structure", "Control",
    "Капитал", "Структура", "Контроль",
}
_PACK_STEP_TITLES = {"设立路径", "Formation path", "Путь создания"}
_SKYLINE = re.compile(r"bangkok business district skyline|skyline", re.I)
_QUERIES = (
    (re.compile(r"翻译|口译|translator|interpreter|перевод", re.I), "office conversation professionals window"),
    (re.compile(r"陪同|出差|旅行|travel|airport|сопровожд", re.I), "airport lounge departure daytime"),
    (re.compile(r"谈判|生意|negotiation|meeting|бизнес", re.I), "business meeting corporate office"),
    (re.compile(r"工资|月薪|薪酬|每天|人民币|泰铢|泰诸|salary|оклад|万", re.I), "office conversation desk daylight"),
)


def enabled() -> bool:
    raw = os.environ.get("MOTION_DESIGN_V18_ENABLED", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def supports_equity(text: str) -> bool:
    return bool(_EQUITY.search(text or ""))


def speech_query(text: str) -> str:
    for pattern, query in _QUERIES:
        if pattern.search(text or ""):
            return query
    return "office conversation professionals window"


def _rows(transcript: list | None, plan: dict) -> list[dict]:
    rows = []
    for row in transcript or plan.get("transcript") or []:
        if hasattr(row, "model_dump"):
            row = row.model_dump()
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _quote(rows: list[dict], span: tuple[float, float]) -> str:
    parts = []
    for row in rows:
        try:
            start = float(row.get("start") or 0)
            end = float(row.get("end") or 0)
        except (TypeError, ValueError):
            continue
        mid = (start + end) / 2
        if span[0] <= mid < span[1]:
            parts.append(str(row.get("original") or row.get("text") or ""))
    return " ".join(part for part in parts if part).strip()


def _guard(face: dict) -> dict:
    return {
        "left": max(0, int(face["left"]) - 36),
        "top": max(0, int(face["top"]) - 96),
        "width": int(face["width"]) + 72,
        "height": int(face["height"]) + 140,
    }


def _clear_template(scene: dict) -> None:
    typ = dict(scene.get("typography") or {})
    cards = []
    for card in typ.get("cards") or []:
        title = str((card or {}).get("title") or "")
        if title not in _PACK_TITLES:
            cards.append(card)
    typ["cards"] = cards
    if not cards:
        typ["cardMode"] = "none"
    steps = [step for step in (typ.get("steps") or []) if str(step) not in _PACK_STEPS]
    title = str(typ.get("stepsTitle") or "")
    if title in _PACK_STEP_TITLES or (steps and len(steps) != len(typ.get("steps") or [])):
        typ["steps"] = []
        typ["stepsTitle"] = ""
    else:
        typ["steps"] = steps
    headline = str(typ.get("headline") or "")
    if headline in _PACK_TITLES or headline in _PACK_STEP_TITLES:
        typ["headline"] = ""
    scene["typography"] = typ
    if str(scene.get("stepsTitle") or "") in _PACK_STEP_TITLES:
        scene["stepsTitle"] = ""
        scene["steps"] = []
    exe = dict(scene.get("execution") or {})
    if str(exe.get("headline") or "") in _PACK_TITLES | _PACK_STEP_TITLES:
        exe["headline"] = ""
    scene["execution"] = exe
    scene["criteriaCards"] = [
        card for card in (scene.get("criteriaCards") or [])
        if str((card or {}).get("title") or "") not in _PACK_TITLES
    ]


def _talking_head(scene: dict, why: str) -> None:
    scene.pop("businessMotion", None)
    scene.pop("semanticMotionV14", None)
    _clear_template(scene)
    comp = dict(scene.get("composition") or {})
    comp["floatObject"] = None
    comp["suppressConcepts"] = True
    comp["suppressHeadline"] = True
    scene["composition"] = comp
    scene["sceneComposition"] = {
        "layout": "speaker_fullscreen",
        "speakerPresentation": "fullscreen",
        "motionComponent": None,
        "mediaAsset": (scene.get("background") or {}).get("assetId"),
        "selectionExplanation": why,
    }


def _family(scene: dict) -> tuple | None:
    payload = scene.get("semanticMotionV14") or {}
    if isinstance(payload, dict) and payload.get("componentId"):
        return ("semantic", payload.get("visualIntent") or payload.get("componentId"), payload.get("layout"), payload.get("mediaSide"))
    motion = scene.get("businessMotion") or {}
    if isinstance(motion, dict) and motion.get("component"):
        return ("business", motion.get("component"), "shelf", None)
    return None


def _place(scene: dict) -> str | None:
    """Drop a diagram that still intersects hair, face, mouth, or the caption plate."""
    payload = scene.get("semanticMotionV14")
    if not isinstance(payload, dict):
        return None
    face = payload.get("faceRect")
    motion = payload.get("motionRect")
    caption = payload.get("captionRect")
    if not isinstance(face, dict) or not isinstance(motion, dict):
        payload["version"] = "v18"
        payload["columnScrim"] = False
        scene["semanticMotionV14"] = payload
        return None
    guard = _guard(face)
    rect = dict(motion)
    # Measured boxes often stop at the eyes. Keep the diagram on the chest,
    # below the chin, even when the detector returns a short face.
    floor = max(int(face["top"] + face["height"]) + 180, int(CANVAS[1] * 0.56))
    caption_top = int(caption["top"]) if isinstance(caption, dict) else CANVAS[1] - 360
    if int(rect.get("top") or 0) < floor:
        rect["top"] = floor
        rect["height"] = caption_top - 36 - floor
    if _overlap(rect, guard, 8):
        rect["top"] = guard["top"] + guard["height"] + 24
        rect["height"] = caption_top - 36 - int(rect["top"])
    if isinstance(caption, dict) and _overlap(rect, caption, 12):
        rect["height"] = int(caption["top"]) - 36 - int(rect["top"])
    if int(rect.get("height") or 0) < 180 or int(rect.get("width") or 0) < 180:
        return "diagram cleared the face by leaving the beat as talking-head"
    if _overlap(rect, guard, 4):
        return "diagram still crossed the measured face"
    payload = dict(payload)
    payload["motionRect"] = rect
    payload["version"] = "v18"
    payload["columnScrim"] = False
    payload["layout"] = "overlay"
    scene["semanticMotionV14"] = payload
    return None


def _retarget_media(scene: dict, quote: str) -> bool:
    query = str(scene.get("query") or "")
    asset = str((scene.get("background") or {}).get("assetId") or "")
    if not (_SKYLINE.search(query) or _SKYLINE.search(asset)):
        return False
    scene["query"] = speech_query(quote)
    bg = dict(scene.get("background") or {})
    for key in ("assetId", "file", "staged", "conceptId"):
        bg.pop(key, None)
    scene["background"] = bg
    return True


def apply_motion_design(
    plan: dict,
    transcript: list | None = None,
    *,
    locale: str | None = None,
    source=None,
) -> dict:
    del source  # speaker geometry is already on the V16 payload when that flag is on
    out = dict(plan)
    if not enabled():
        out["motionDesignV18Enabled"] = False
        return out
    rows = _rows(transcript, out)
    spans = _windows(out, rows)
    scenes = []
    recent: list[tuple | None] = []
    usage = []
    for index, scene in enumerate(out.get("scenes") or []):
        scene = dict(scene)
        span = spans[index] if index < len(spans) else (0.0, 0.0)
        quote = _quote(rows, span)
        equity = supports_equity(quote)
        motion = scene.get("businessMotion") if isinstance(scene.get("businessMotion"), dict) else None
        if motion and motion.get("component") in _BUSINESS and not equity:
            scene.pop("businessMotion", None)
            motion = None
        if not equity:
            _clear_template(scene)
        payload = scene.get("semanticMotionV14") if isinstance(scene.get("semanticMotionV14"), dict) else None
        if payload and payload.get("componentId"):
            payload = dict(payload)
            payload["version"] = "v18"
            payload["columnScrim"] = False
            scene["semanticMotionV14"] = payload
            blocked = _place(scene)
            if blocked:
                _talking_head(scene, blocked)
                if not equity:
                    _retarget_media(scene, quote)
        elif not motion:
            _talking_head(scene, "speech does not support a diagram on this beat")
            _retarget_media(scene, quote)
        family = _family(scene)
        quote_now = str(((scene.get("semanticMotionV14") or {}).get("evidence") or {}).get("sourceQuote") or "")
        previous_quote = ""
        if scenes:
            previous_quote = str((((scenes[-1].get("semanticMotionV14") or {}).get("evidence") or {}).get("sourceQuote")) or "")
        distinct_thought = bool(quote_now and previous_quote and quote_now != previous_quote)
        if family and not distinct_thought and len(recent) >= 1 and recent[-1] and recent[-1][1] == family[1]:
            if not equity:
                _talking_head(scene, "adjacent beat already used this diagram")
                family = None
            elif family[0] == "semantic":
                payload = dict(scene.get("semanticMotionV14") or {})
                payload["mediaSide"] = "right" if payload.get("mediaSide") != "right" else "left"
                payload["layout"] = "speaker_visual" if payload.get("layout") == "overlay" else "overlay"
                scene["semanticMotionV14"] = payload
                family = _family(scene)
        if family and not distinct_thought and len(recent) >= 2 and recent[-1] == family and recent[-2] == family:
            _talking_head(scene, "three identical compositions are refused")
            family = None
        recent.append(family)
        usage.append({
            "sceneId": scene.get("sceneId"),
            "quote": quote[:80],
            "equity": equity,
            "component": (family or (None,))[1] if family else None,
            "query": scene.get("query"),
            "speaker": (scene.get("sceneComposition") or {}).get("speakerPresentation"),
        })
        scenes.append(scene)
    out["scenes"] = scenes
    out["motionDesignV18Enabled"] = True
    out["motionDesignV18Usage"] = usage
    out["motionDesignV18Version"] = "v18.0"
    out["language"] = locale or out.get("language")
    return out
