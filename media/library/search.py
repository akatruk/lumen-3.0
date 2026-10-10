"""Find a library asset from a meaning, not a filename."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "out"
MANIFEST = ROOT / "manifest.json"


# Meaning in Russian or Chinese points at the same English-tagged asset. Files stay language-neutral.
_QUERY_ALIASES = (
    ("семья покупает квартиру", "family buyer apartment"),
    ("家庭购买公寓", "family purchase apartment"),
    ("недвижимость", "property real estate"),
    ("квартир", "apartment"),
    ("семья", "family"),
    ("покупа", "buyer purchase"),
    ("локац", "location"),
    ("расположен", "location"),
    ("доходность", "yield"),
    ("аренда", "rental"),
    ("документы", "documents"),
    ("инвест", "investor investment"),
    ("переезд", "relocation"),
    ("планир", "planning"),
    ("неуверен", "uncertainty decision"),
    ("одобрен", "approval success"),
    ("чемодан", "suitcase packing"),
    ("город", "city"),
    ("计划", "planning"),
    ("国际", "international"),
    ("второй паспорт", "second passport citizenship"),
    ("второе гражданство", "second citizenship passport"),
    ("иммиграц", "immigration"),
    ("консультац", "consultation"),
    ("эмиграц", "emigration relocation"),
    ("гражданств", "citizenship"),
    ("резидент", "residency residence"),
    ("внж", "residence permit"),
    ("пмж", "permanent residence"),
    ("виз", "visa"),
    ("паспорт", "passport"),
    ("релокац", "relocation"),
    ("номад", "digital nomad"),
    ("налогов", "tax residency"),
    ("第二护照", "second passport"),
    ("移民", "immigration relocation"),
    ("海外移居", "overseas immigration relocation"),
    ("海外移民", "overseas immigration relocation"),
    ("移居", "relocation immigration"),
    ("居留", "residence permit"),
    ("公民", "citizenship"),
    ("签证", "visa"),
    ("护照", "passport"),
    ("搬家", "relocation moving"),
    ("税务", "tax residency"),
    ("公寓", "apartment"),
    ("家庭", "family"),
    ("购买", "purchase"),
    ("地段", "location"),
    ("租金", "rental"),
    ("回报", "yield"),
    ("房产", "property"),
    ("顾问咨询会议", "consultation meeting advisor"),
    ("顾问客户文件", "advisor client documents"),
    ("顾问", "advisor consultation"),
    ("咨询", "consultation"),
    ("电话咨询", "phone consultation"),
    ("电话咨询办公室", "phone consultation office"),
    ("抵达新城市", "city arrival"),
    ("新城市", "city"),
    ("文件审核桌面", "document review desk"),
    ("文件审核", "document review"),
    ("不确定的决定", "uncertainty decision"),
    ("不确定", "uncertainty"),
    ("проверка документов", "document review"),
    ("на столе", "desk"),
    ("заявление на внж", "residency application residence permit"),
)


def normalize_query(text):
    query = text or ""
    try:
        from concepts import PHRASES
    except ImportError:
        from media.library.concepts import PHRASES
    # Case-fold Latin/Cyrillic so «ВНЖ» still hits the «внж» phrase.
    folded = query.casefold()
    for source, english in list(PHRASES) + list(_QUERY_ALIASES):
        needle = source.casefold()
        start = 0
        while True:
            at = folded.find(needle, start)
            if at < 0:
                break
            query = query[:at] + f" {english} " + query[at + len(source):]
            folded = query.casefold()
            start = at + len(english) + 2
    return query


_STOP = frozenset({
    "a", "an", "the", "in", "on", "of", "for", "to", "and", "or", "with",
    "before", "into", "from", "at", "by", "is", "are",
})

# A spoken form should still find the tag the library already uses.
_EXPAND = {
    "arriving": ("arrival",),
    "arrive": ("arrival",),
    "considering": ("planning", "decision"),
    "choosing": ("comparison", "decision"),
    "successful": ("approval", "success"),
    "preparation": ("documents", "application"),
    "abroad": ("international", "relocation"),
    "owner": ("business", "entrepreneur"),
    "uncertainty": ("uncertainty", "decision"),
}

_SCENE = frozenset({
    "family", "couple", "planning", "packing", "arrival", "apartment", "viewing",
    "consultation", "city", "travel", "luggage", "advisor", "buyer", "home",
    "suitcase", "departure", "uncertainty", "decision", "document", "documents",
    "property", "investment", "business", "approval", "passport", "route",
})


def _tokens(text):
    return [part for part in re.split(r"[^a-z0-9]+", normalize_query(text).lower()) if part]


def _query_words(query):
    words = []
    for part in _tokens(query):
        if part in _STOP or len(part) < 2:
            continue
        words.append(part)
        words.extend(_EXPAND.get(part, ()))
    return list(dict.fromkeys(words))


def load(path=None):
    file = Path(path) if path else MANIFEST
    data = json.loads(file.read_text())
    return data["assets"] if isinstance(data, dict) else data


def _joined(value):
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value or "")


def _localized(value):
    if isinstance(value, dict):
        return " ".join(str(item) for item in value.values())
    return _joined(value)


def _hay(asset):
    parts = [
        asset.get("id", ""),
        asset.get("conceptId", ""),
        _localized(asset.get("description")),
        _joined(asset.get("domain")),
        asset.get("visualFamily", ""),
        asset.get("action", ""),
        asset.get("environment", ""),
        asset.get("region", ""),
        asset.get("energy", ""),
        asset.get("motionPotential", ""),
        _localized(asset.get("tags")),
        " ".join(asset.get("subjects") or []),
        " ".join(asset.get("mood") or []),
        " ".join(asset.get("emotion") or []),
        " ".join(asset.get("sceneRoles") or []),
        " ".join(asset.get("recommendedTreatments") or []),
        " ".join(asset.get("propertyType") or []),
        " ".join(asset.get("textSafeAreas") or []),
    ]
    blob = re.sub(r"\b(?:four|one|two|three|\d+)[\s-]seconds?\b", "duration", " ".join(parts), flags=re.I)
    return _tokens(blob)


def _same_domain(asset, domain):
    value = asset.get("domain")
    if isinstance(value, list):
        return domain in value
    return value == domain


def _rank_score(asset, words, text_safe, preferred_scene_role, preferred_energy, preferred_composition=None, recent_ids=()):
    hay = _hay(asset)
    overlap = sum(1 for word in words if word in hay)
    if overlap == 0:
        return None
    score = overlap * 2 + (asset.get("qualityScore") or 0)
    family = asset.get("visualFamily") or ""
    category = asset.get("category") or ""
    if family == "deterministic_motion":
        score += 0.45
    elif family == "generative_motion":
        score += 0.35
    elif family == "photography":
        score += 0.25
    elif category == "icons":
        score -= 0.25
    matched_scene = [word for word in words if word in _SCENE and word in hay]
    decorative = category == "decorative"
    asks_mark = any(word in words for word in ("arrow", "mark", "overlay", "transition", "wipe"))
    if matched_scene:
        if family == "photography":
            score += 2.4
        elif family == "generative_motion":
            score += 2.1
        elif family == "editorial_object":
            score += 0.8
        elif family == "deterministic_motion":
            score += 1.2
        elif decorative:
            score -= 3
        elif family in ("line", "") and category in ("icons", "immigration", "decorative"):
            score -= 0.6
    elif decorative and not asks_mark:
        score -= 1.5
    roles = asset.get("sceneRoles") or []
    if preferred_scene_role and preferred_scene_role in roles:
        score += 1.8
    if preferred_energy and asset.get("energy") == preferred_energy:
        score += 0.8
    if text_safe and text_safe in (asset.get("textSafeAreas") or []):
        score += 1.5
    if preferred_composition and asset.get("composition") == preferred_composition:
        score += 1.6
    if asset.get("id") in set(recent_ids or ()):
        score -= 2.2
    return score


def search_assets(
    query, type=None, category=None, aspect_ratio=None, composition=None, limit=5,
    path=None, text_safe=None, domain=None, exclude_ids=(), preferred_scene_role=None,
    preferred_energy=None, locale=None, preferred_composition=None, recent_ids=(),
    scene_role=None, text_position=None, excluded_asset_ids=(),
):
    """Rank assets by meaning, quality, role, and whether type can sit on them.

    text_safe prefers assets whose textSafeAreas include that side, without
    dropping a strong semantic match that has no composition note yet.
    exclude_ids drops files already used in the current video.
    """
    words = _query_words(query)
    if (query or "").strip() and not words:
        return []
    skipped = set(exclude_ids or ()) | set(excluded_asset_ids or ())
    role = preferred_scene_role or scene_role
    safe = text_safe or text_position
    found = []
    del locale
    for asset in load(path):
        if asset.get("id") in skipped:
            continue
        if type and asset.get("type") != type:
            continue
        if category and asset.get("category") != category:
            continue
        if aspect_ratio and asset.get("aspectRatio") != aspect_ratio:
            continue
        if composition and asset.get("composition") != composition:
            continue
        if domain and not _same_domain(asset, domain):
            continue
        if not words:
            score = asset.get("qualityScore") or 0
        else:
            score = _rank_score(
                asset, words, safe, role, preferred_energy,
                preferred_composition or composition, recent_ids,
            )
            if score is None:
                continue
            if composition and asset.get("composition") == composition:
                score += 1.2
        found.append((score, asset.get("qualityScore") or 0, asset))
    found.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [asset for _, _, asset in found[:limit]]
