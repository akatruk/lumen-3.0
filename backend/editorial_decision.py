"""Editorial decisions that run after the heuristic plan and before staging.

Full-frame speaker is the safe picture. A split, a picture-in-picture, or a
graphic stays only when this scene's own quote supports it. Template queries
and generic office/house/meeting stock do not.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .visual_review import picture_supports, select_reviewed

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


def _rows_in_window(transcript, start: float, end: float) -> list:
    rows = []
    for row in transcript or []:
        if not isinstance(row, dict):
            continue
        a = float(row.get("start") or 0)
        b = float(row.get("end") or a)
        if b <= start or a >= end:
            continue
        rows.append(row)
    return rows


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
    """Token overlap only. A query sitting inside the quote is not a picture match."""
    spoken = quote or ""
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


def assign_passage_queries(plan: dict, transcript, locale: str | None) -> dict:
    """Search each beat with its own spoken words. Drop a template plate first."""
    out = dict(plan or {})
    scenes = [dict(scene) for scene in out.get("scenes") or []]
    target = float(out.get("durationSeconds") or 0)
    if target <= 0 or not scenes:
        return out
    rhythm, _source = speech_weights(transcript, target, len(scenes))
    weights = rhythm or list(out.get("beatWeights") or [])
    if len(weights) != len(scenes):
        weights = [1] * len(scenes)
    windows = _windows(weights, target)
    for scene, (start, end) in zip(scenes, windows):
        quote = quote_for_window(transcript, start, end, locale)
        scene["passage"] = quote
        if not quote or quote.strip().startswith("[segment"):
            continue
        scene["query"] = quote
        background = dict(scene.get("background") or {})
        for key in ("assetId", "file", "staged", "conceptId"):
            background.pop(key, None)
        scene["background"] = background
    out["scenes"] = scenes
    return out


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


def _ordinal_lines(transcript, start: float, end: float, locale: str | None) -> list[str]:
    """Verbatim lines that open with a spoken ordinal and whose midpoint is in this beat."""
    found = []
    for row in _rows_in_window(transcript, start, end):
        text = _text(row, locale).strip()
        mid = (float(row.get("start") or 0) + float(row.get("end") or 0)) / 2
        if mid < start or mid >= end or not _ORDINAL.match(text):
            continue
        body = _ORDINAL.sub("", text).lstrip("、,，:：. ").strip()
        if len(body) < 4 or body in PACK_LABELS or text in PACK_LABELS:
            continue
        found.append(text)
    return found[:3]


def _stamp_spoken_split(scene: dict, steps: list[str]) -> None:
    _clear_media(scene)
    speaker = dict(scene.get("speaker") or {})
    speaker["layout"] = "speaker_split_right"
    speaker["treatment"] = "speaker_split_right"
    speaker["framing"] = "split"
    speaker["visibility"] = "primary"
    scene["speaker"] = speaker
    typography = dict(scene.get("typography") or {})
    typography["steps"] = list(steps)
    typography["stepsTitle"] = ""
    typography["cardMode"] = "none"
    typography.pop("cards", None)
    scene["typography"] = typography
    scene["steps"] = list(steps)
    scene["stepsTitle"] = ""
    scene["criteriaCards"] = []
    execution = dict(scene.get("execution") or {})
    execution["headline"] = ""
    execution["speakerFraming"] = "split"
    execution["mediaRole"] = "none"
    scene["execution"] = execution
    composition = dict(scene.get("sceneComposition") or {})
    composition["speakerPresentation"] = "split"
    composition["editorial"] = "spoken-split"
    scene["sceneComposition"] = composition
    scene["representation"] = "presenter"


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


_NUMBER = re.compile(r"\d[\d,.\-–~]*(?:[万亿%％元块])?")
# A line that opens with a spoken ordinal. Not a price, not a pack label.
_ORDINAL = re.compile(r"^(?:第[一二三四五六七八九十]|First|Second|Third)(?=[\s,，、:：.]|$)")

# Spoken spans worth a title. Longer and sharper first. A span is used only
# when it is already inside one transcript segment. This list does not add words.
_PHRASES = (
    "甜美的陷阱",
    "硬核问题",
    "买房送身份",
    "买房移民",
    "挂牌价",
    "占便宜",
    "翻译费用",
    "绿卡",
    "护照",
    "工资",
    "税费",
    "股东",
    "身份",
    "移民",
    "刷卡",
    "陷阱",
)


def emphasis_phrase(quote: str) -> str | None:
    """A short span already inside the quote. Not the whole caption, not a new claim."""
    text = " ".join((quote or "").split())
    if len(text) < 6:
        return None
    for match in _NUMBER.finditer(text):
        token = match.group(0)
        if len(token) >= 2 and token != text and token in text:
            return token
    return _best_phrase(text)


def _best_phrase(text: str) -> str | None:
    """Best verbatim title inside one segment. None when the line has no listed span."""
    folded = text or ""
    for phrase in _PHRASES:
        if phrase in PACK_LABELS:
            continue
        if phrase in folded and phrase != folded:
            return phrase
    return None


def _row_id(row: dict) -> str | None:
    ident = row.get("id") or row.get("segmentId") or row.get("segment_id")
    return str(ident) if ident else None


_EMPHASIS_GAP = 15.0
_EMPHASIS_LIMIT = 2


def _number_token(text: str) -> str | None:
    """A spoken quantity already in the line. Bare single digits are not titles."""
    if len(text) < 6:
        return None
    for match in _NUMBER.finditer(text):
        token = match.group(0)
        if len(token) < 2 or token == text or token not in text:
            continue
        digits = re.sub(r"\D", "", token)
        if len(digits) >= 2 or any(unit in token for unit in "万亿%％元块"):
            return token
    return None


def _row_candidates(row: dict, locale: str | None) -> list[tuple[int, str]]:
    text = _text(row, locale)
    found: list[tuple[int, str]] = []
    number = _number_token(text)
    if number:
        found.append((-1, number))
    for rank, phrase in enumerate(_PHRASES):
        if phrase in PACK_LABELS:
            continue
        if phrase in text and phrase != text:
            found.append((rank, phrase))
    return found


def emphasis_for_rows(rows: list, locale: str | None, used: set[str]) -> tuple[str | None, str | None]:
    """Number first, then the sharpest unused phrase. Both must sit in that row."""
    ranked: list[tuple[int, str, str | None]] = []
    for row in rows:
        for rank, phrase in _row_candidates(row, locale):
            if phrase not in used:
                ranked.append((rank, phrase, _row_id(row)))
    if not ranked:
        return None, None
    ranked.sort()
    return ranked[0][1], ranked[0][2]


def _scene_for_time(windows: list[tuple[float, float]], when: float) -> int | None:
    for index, (start, end) in enumerate(windows):
        last = index == len(windows) - 1
        if start <= when < end or (last and when <= end):
            return index
    return None


def _select_emphasis(transcript, windows, locale, blocked: set[int]) -> list[dict]:
    """Best phrases on the whole timeline. At most two, about 15s apart.

    Rank decides. Clock order does not. A later sharper line beats an earlier
    weak one. One useful line stays one line.
    """
    pool: dict[str, dict] = {}
    for row in transcript or []:
        if not isinstance(row, dict):
            continue
        start = float(row.get("start") or 0)
        end = float(row.get("end") or start)
        anchor = (start + end) / 2
        scene_index = _scene_for_time(windows, anchor)
        if scene_index is None or scene_index in blocked:
            continue
        for rank, phrase in _row_candidates(row, locale):
            current = pool.get(phrase)
            if current is not None and current["rank"] <= rank:
                continue
            pool[phrase] = {
                "rank": rank,
                "phrase": phrase,
                "segmentId": _row_id(row),
                "anchor": anchor,
                "start": start,
                "end": end,
                "scene": scene_index,
            }
    ordered = sorted(pool.values(), key=lambda item: (item["rank"], -len(item["phrase"])))
    chosen: list[dict] = []
    for item in ordered:
        if any(abs(item["anchor"] - kept["anchor"]) < _EMPHASIS_GAP for kept in chosen):
            continue
        if any(item["scene"] == kept["scene"] for kept in chosen):
            continue
        chosen.append(item)
        if len(chosen) == _EMPHASIS_LIMIT:
            break
    return chosen


def _segment_id(transcript, start: float, end: float) -> str | None:
    for row in transcript or []:
        if not isinstance(row, dict):
            continue
        a = float(row.get("start") or 0)
        b = float(row.get("end") or a)
        if b <= start or a >= end:
            continue
        ident = row.get("id") or row.get("segmentId") or row.get("segment_id")
        if ident:
            return str(ident)
    return None


def _stamp_emphasis(scene: dict, phrase: str, speech: tuple[float, float] | None = None) -> None:
    _clear_media(scene)
    scene["headline"] = phrase
    typography = dict(scene.get("typography") or {})
    typography["headline"] = phrase
    typography["cardMode"] = "none"
    scene["typography"] = typography
    execution = dict(scene.get("execution") or {})
    execution["headline"] = phrase
    execution["speakerFraming"] = "fullscreen"
    execution["mediaRole"] = "none"
    scene["execution"] = execution
    speaker = dict(scene.get("speaker") or {})
    # Mild existing zoom. The title sits below the face band, so the face stays clear.
    speaker["layout"] = "speaker_medium"
    speaker["framing"] = "fullscreen"
    speaker["visibility"] = "primary"
    scene["speaker"] = speaker
    composition = dict(scene.get("composition") or {})
    composition["floatObject"] = None
    scene["composition"] = composition
    look = dict(scene.get("sceneComposition") or {})
    look["speakerPresentation"] = "emphasis"
    look["editorial"] = "emphasis"
    scene["sceneComposition"] = look
    scene["representation"] = "presenter"
    if speech is not None:
        # The title follows this spoken line. The beat may start earlier.
        scene["emphasisRange"] = [round(speech[0], 3), round(speech[1], 3)]


_SAFE_SPEAKER = {"speaker_fullscreen", "speaker_medium"}


def _float_supported(flo: dict, quote: str) -> bool:
    """Same evidence rule as a plate. A global keyword is not this scene's quote."""
    if not isinstance(flo, dict) or not flo.get("file"):
        return False
    blob = " ".join(str(flo.get(key) or "") for key in ("keyword", "concept", "assetId", "silhouette"))
    if relevance(quote, blob, str(flo.get("assetId") or "")) >= THRESHOLD:
        return True
    spoken = quote or ""
    for key in ("keyword", "concept"):
        token = str(flo.get(key) or "").strip()
        if token and (token in spoken or token.lower() in spoken.lower()):
            return True
    return False


def _gate_float(scene: dict, quote: str) -> str | None:
    comp = dict(scene.get("composition") or {})
    flo = comp.get("floatObject") or {}
    if not isinstance(flo, dict) or not flo.get("file"):
        return None
    if _float_supported(flo, quote):
        return None
    comp["floatObject"] = None
    scene["composition"] = comp
    foreground = dict(scene.get("foreground") or {})
    if foreground.get("file") == flo.get("file") or (
        flo.get("assetId") and foreground.get("assetId") == flo.get("assetId")
    ):
        foreground["assetId"] = None
        foreground["file"] = None
        foreground["staged"] = None
        scene["foreground"] = foreground
    return "unsupported-float"


def _safe_layout(scene: dict) -> str:
    speaker = scene.get("speaker") or {}
    shot = scene.get("shotPlan") or {}
    for candidate in (shot.get("speakerLayout"), speaker.get("layout")):
        if candidate in _SAFE_SPEAKER:
            return candidate
    return "speaker_fullscreen"


def _speaker_full(scene: dict) -> None:
    scene.pop("headline", None)
    typography = dict(scene.get("typography") or {})
    typography.pop("headline", None)
    scene["typography"] = typography
    layout = _safe_layout(scene)
    speaker = dict(scene.get("speaker") or {})
    speaker["layout"] = layout
    speaker["treatment"] = layout
    speaker["framing"] = "fullscreen"
    speaker["visibility"] = "primary"
    scene["speaker"] = speaker
    composition = dict(scene.get("sceneComposition") or {})
    composition["speakerPresentation"] = "fullscreen"
    composition["editorial"] = "speaker"
    scene["sceneComposition"] = composition
    scene["representation"] = "presenter"
    execution = dict(scene.get("execution") or {})
    execution["headline"] = ""
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
    rhythm, rhythm_source = speech_weights(transcript, target, len(scenes))
    weights = rhythm or list(out.get("beatWeights") or [])
    if len(weights) != len(scenes):
        weights = [1] * max(1, len(scenes))
    windows = _windows(weights, target) if scenes else []
    seen: set[str] = set()
    audit = []
    repaired = []
    blocked: set[int] = set()
    decisions: list[tuple[str, float, bool]] = []
    for index, (scene, (start, end)) in enumerate(zip(scenes, windows)):
        quote = quote_for_window(transcript, start, end, locale)
        background = scene.get("background") or {}
        asset = background.get("assetId") or background.get("file")
        query = scene.get("query")
        score = relevance(quote, query if isinstance(query, str) else None, asset if isinstance(asset, str) else None)
        repeated = bool(asset) and str(asset) in seen
        if repeated:
            score = 0.0
        picture = picture_supports(asset if isinstance(asset, str) else None, quote)
        replacement = select_reviewed(quote, seen) if asset and not picture else None
        media_ok = (picture or replacement is not None) and not repeated and bool(asset or replacement)
        if media_ok and replacement is not None:
            background = dict(replacement)
            scene["background"] = background
            asset = background.get("assetId")
            score = 1.0
        graphic_ok = _drop_graphics(scene, quote)
        spoken_steps = _ordinal_lines(transcript, start, end, locale)
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
            blocked.add(index)
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
            blocked.add(index)
        elif spoken_steps:
            _stamp_spoken_split(scene, spoken_steps)
            purpose = "spoken-split"
            blocked.add(index)
        else:
            purpose = "pending"
        decisions.append((purpose, score, repeated))
        scene["_window"] = (start, end)
        repaired.append(scene)
    chosen = _select_emphasis(transcript, windows, locale, blocked)
    by_scene = {item["scene"]: item for item in chosen}
    scenes = repaired
    repaired = []
    for index, scene in enumerate(scenes):
        start, end = scene.pop("_window")
        purpose, score, repeated = decisions[index]
        quote = quote_for_window(transcript, start, end, locale)
        float_rejection = _gate_float(scene, quote)
        if purpose == "pending":
            item = by_scene.get(index)
            phrase = item["phrase"] if item else None
            if phrase and phrase in quote_for_window(transcript, start, end, locale):
                _stamp_emphasis(scene, phrase, (item["start"], item["end"]))
                scene["_emphasisSegmentId"] = item["segmentId"]
                purpose = "semantic-emphasis"
            else:
                _clear_media(scene)
                _speaker_full(scene)
                purpose = "speaker-full"
        scene["editorial"] = {
            "purpose": purpose,
            "relevance": round(score, 3),
            "quoteSeconds": [round(start, 3), round(end, 3)],
            "displaySeconds": list(scene.get("emphasisRange") or []),
            "segmentId": scene.pop("_emphasisSegmentId", None) or _segment_id(transcript, start, end),
            "phrase": scene.get("headline") or "",
            "component": (
                "KineticHeadline" if purpose == "semantic-emphasis"
                else "SpokenSplit" if purpose == "spoken-split"
                else ""
            ),
            "reason": float_rejection if purpose == "speaker-full" and float_rejection else purpose,
            "repeated": repeated,
            "rejected": purpose == "speaker-full",
        }
        audit.append(scene["editorial"])
        repaired.append(scene)
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
