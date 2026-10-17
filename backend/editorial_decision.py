"""Editorial decisions that run after the heuristic plan and before staging.

Full-frame speaker is the safe picture. A split, a picture-in-picture, or a
graphic stays only when this scene's own quote supports it. Template queries
and generic office/house/meeting stock do not.
"""
from __future__ import annotations

import re

GENERIC = {
    "business", "company", "money", "people", "person", "office", "house",
    "home", "meeting", "real", "estate", "property", "family", "work",
    "video", "photo", "clip", "stock", "advisor", "client", "room",
}
# English query token → evidence that must appear in the quote.
ALIASES = {
    "passport": ("护照", "passport"),
    "visa": ("签证", "visa"),
    "relocation": ("搬家", "relocation", "переезд"),
    "doorway": ("门口", "doorway"),
    "consult": ("咨询", "консультац"),
    "consultation": ("咨询", "консультац"),
    "shareholder": ("股东", "акционер", "shareholder"),
    "salary": ("工资", "зарплат", "salary"),
    "translation": ("翻译", "перевод", "translation"),
    "contract": ("合同", "договор", "contract"),
    "permit": ("许可", "внж", "permit"),
    "capital": ("资本", "уставн", "capital"),
}
THRESHOLD = 0.5
# Locale packs painted when a scene has no spoken labels.
PACK_LABELS = {
    "全程陪同", "咨询", "方案", "文件", "目标", "家庭", "预算",
    "guided process", "consult", "program", "documents", "goals", "family", "budget",
    "сопровождение", "консультация", "программа", "документы", "цели", "семья", "бюджет",
}


def _text(row: dict, locale: str | None) -> str:
    bucket = (locale or "").lower()
    if bucket.startswith("zh"):
        keys = ("zh", "original", "text")
    elif bucket.startswith("ru"):
        keys = ("ru", "original", "text")
    else:
        keys = ("en", "original", "text")
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def quote_for_window(transcript, start: float, end: float, locale: str | None) -> str:
    parts = []
    for row in transcript or []:
        if not isinstance(row, dict):
            continue
        a = float(row.get("start") or 0)
        b = float(row.get("end") or a)
        if b <= start or a >= end:
            continue
        text = _text(row, locale)
        if text:
            parts.append(text)
    return " ".join(parts)


def _specific_words(query: str, asset_id: str) -> list[str]:
    raw = f"{query or ''} {asset_id or ''}".lower().replace("_", " ").replace("-", " ")
    words = re.findall(r"[a-z]{3,}", raw)
    return [word for word in words if word not in GENERIC]


def relevance(quote: str, query: str | None, asset_id: str | None) -> float:
    """1 when a specific token is in this quote. 0 for generic stock."""
    spoken = quote or ""
    if query and query.strip() and query.strip() in spoken:
        return 1.0
    specific = _specific_words(query or "", asset_id or "")
    if not specific:
        return 0.0
    hits = 0
    folded = spoken.lower()
    for word in specific:
        if word in folded:
            hits += 1
            continue
        aliases = ALIASES.get(word) or ()
        if any(alias.lower() in folded for alias in aliases):
            hits += 1
    return hits / len(specific)


def _labels(value) -> list[str]:
    labels = []
    for item in value or []:
        if isinstance(item, str):
            labels.append(item.strip())
        elif isinstance(item, dict):
            for key in ("title", "label", "text", "explanation"):
                piece = item.get(key)
                if isinstance(piece, str) and piece.strip():
                    labels.append(piece.strip())
    return [label for label in labels if label]


def labels_supported(labels: list[str], quote: str) -> bool:
    if not labels:
        return False
    spoken = quote or ""
    folded = spoken.lower()
    for label in labels:
        if label.lower() in PACK_LABELS and label not in spoken and label.lower() not in folded:
            return False
        if label not in spoken and label.lower() not in folded:
            return False
    return True


def _windows(weights: list, target: float) -> list[tuple[float, float]]:
    total = sum(float(w) for w in weights) or 1.0
    cursor = 0.0
    spans = []
    for weight in weights:
        dur = target * (float(weight) / total)
        spans.append((cursor, cursor + dur))
        cursor += dur
    return spans


def speech_weights(transcript, target: float, count: int, fps: int = 30) -> tuple[list[int], str]:
    """Bucket weights follow where speech sits. Empty plans stay even."""
    if count < 1:
        return [], "even_fallback"
    buckets = [0.0] * count
    spoken = 0.0
    for row in transcript or []:
        if not isinstance(row, dict):
            continue
        start = max(0.0, float(row.get("start") or 0))
        end = min(float(target), float(row.get("end") or 0))
        if end <= start:
            continue
        mid = (max(0.0, float(row.get("start") or 0)) + float(row.get("end") or 0)) / 2
        if mid < 0 or mid > target:
            continue
        index = min(count - 1, int(mid / target * count)) if target else 0
        buckets[index] += end - start
        spoken += end - start
    frames = max(count, int(round(float(target) * fps)))
    if spoken <= 0:
        share = frames // count
        weights = [share] * count
        weights[-1] += frames - sum(weights)
        return weights, "even_fallback"
    # A silent bucket stays short (0.15 of a spoken share) so it does not
    # inherit the long60 template.
    floor = spoken / count * 0.15
    raw = [value if value > 0 else floor for value in buckets]
    total = sum(raw) or 1.0
    weights = [max(1, int(round(frames * (value / total)))) for value in raw]
    drift = frames - sum(weights)
    weights[-1] = max(1, weights[-1] + drift)
    return weights, "transcript_midpoint"


def _clear_media(scene: dict) -> None:
    background = dict(scene.get("background") or {})
    foreground = dict(scene.get("foreground") or {})
    for bucket in (background, foreground):
        bucket["assetId"] = None
        bucket["file"] = None
        bucket["staged"] = None
    scene["background"] = background
    scene["foreground"] = foreground
    scene["query"] = None


def _drop_graphics(scene: dict, quote: str) -> bool:
    typography = dict(scene.get("typography") or {})
    card_labels = _labels(typography.get("cards")) + _labels(scene.get("criteriaCards"))
    step_labels = _labels(typography.get("steps")) + _labels(scene.get("steps"))
    title = typography.get("stepsTitle") or scene.get("stepsTitle") or ""
    if isinstance(title, str) and title.strip():
        step_labels = [title.strip(), *step_labels]
    kept = False
    if card_labels and labels_supported(card_labels, quote):
        kept = True
    else:
        typography.pop("cards", None)
        typography["cardMode"] = "none"
        scene["criteriaCards"] = []
    if step_labels and labels_supported(step_labels, quote):
        kept = True
    else:
        typography.pop("steps", None)
        typography.pop("stepsTitle", None)
        scene["steps"] = []
        scene["stepsTitle"] = ""
    scene["typography"] = typography
    motion = scene.get("businessMotion") or {}
    if isinstance(motion, dict) and motion.get("component"):
        blob = " ".join(str(motion.get(key) or "") for key in ("component", "title", "value"))
        if blob.strip() and blob.strip() not in quote and not labels_supported(_labels([blob]), quote):
            scene["businessMotion"] = None
        else:
            kept = True
    return kept


def _speaker_full(scene: dict) -> None:
    speaker = dict(scene.get("speaker") or {})
    speaker["layout"] = "speaker_fullscreen"
    speaker["treatment"] = "speaker_fullscreen"
    speaker["framing"] = "fullscreen"
    speaker["visibility"] = "primary"
    scene["speaker"] = speaker
    composition = dict(scene.get("sceneComposition") or {})
    composition["speakerPresentation"] = "fullscreen"
    composition["editorial"] = "speaker"
    scene["sceneComposition"] = composition
    scene["representation"] = "presenter"
    execution = dict(scene.get("execution") or {})
    execution["speakerFraming"] = "fullscreen"
    execution["mediaRole"] = "none"
    scene["execution"] = execution


def apply_editorial_decision(
    plan: dict,
    transcript,
    *,
    locale: str | None,
    target_seconds: float,
    source_seconds: float,
    duration_mode: str,
) -> dict:
    out = dict(plan or {})
    scenes = [dict(scene) for scene in out.get("scenes") or []]
    target = float(target_seconds)
    weights = list(out.get("beatWeights") or [])
    if len(weights) != len(scenes):
        weights = [1] * max(1, len(scenes))
    windows = _windows(weights, target) if scenes else []
    seen: set[str] = set()
    audit = []
    repaired = []
    for scene, (start, end) in zip(scenes, windows):
        quote = quote_for_window(transcript, start, end, locale)
        background = scene.get("background") or {}
        asset = background.get("assetId") or background.get("file")
        query = scene.get("query")
        score = relevance(quote, query if isinstance(query, str) else None, asset if isinstance(asset, str) else None)
        repeated = bool(asset) and str(asset) in seen
        if repeated:
            score = 0.0
        media_ok = score >= THRESHOLD and not repeated and bool(asset)
        graphic_ok = _drop_graphics(scene, quote)
        if media_ok:
            seen.add(str(asset))
            speaker = dict(scene.get("speaker") or {})
            speaker["layout"] = "speaker_split_right"
            speaker["framing"] = "split"
            speaker["visibility"] = "primary"
            scene["speaker"] = speaker
            composition = dict(scene.get("sceneComposition") or {})
            composition["speakerPresentation"] = "split"
            composition["editorial"] = "support"
            composition["relevance"] = round(score, 3)
            scene["sceneComposition"] = composition
            purpose = "supporting-visual"
        elif graphic_ok:
            _clear_media(scene)
            speaker = dict(scene.get("speaker") or {})
            speaker["layout"] = "speaker_fullscreen"
            speaker["framing"] = "fullscreen"
            speaker["visibility"] = "primary"
            scene["speaker"] = speaker
            composition = dict(scene.get("sceneComposition") or {})
            composition["speakerPresentation"] = "graphic"
            composition["editorial"] = "graphic"
            scene["sceneComposition"] = composition
            purpose = "semantic-graphic"
        else:
            _clear_media(scene)
            _speaker_full(scene)
            purpose = "speaker-full"
        scene["editorial"] = {
            "purpose": purpose,
            "relevance": round(score, 3),
            "quoteSeconds": [round(start, 3), round(end, 3)],
            "repeated": repeated,
        }
        audit.append(scene["editorial"])
        repaired.append(scene)
    rhythm, rhythm_source = speech_weights(transcript, target, len(repaired))
    out["scenes"] = repaired
    if rhythm:
        out["beatWeights"] = rhythm
    out["editorialRhythm"] = rhythm_source
    out["editorialAudit"] = audit
    out["durationContract"] = {
        "mode": duration_mode,
        "sourceSeconds": float(source_seconds),
        "targetSeconds": target,
    }
    out["durationSeconds"] = target
    return out
