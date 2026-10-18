"""Language-neutral asset ids. EN/RU/ZH labels come from existing tags only.

Does not invent visual concepts that are not already on the asset.
Does not overwrite tags_ru / tags_zh / localized when they are already set.
"""
from __future__ import annotations

LOCALES = ("en-US", "ru-RU", "zh-CN")

# English library tokens → (ru, zh). Only terms already used as tags.
GLOSSARY = {
    "family": ("семья", "家庭"),
    "couple": ("пара", "情侣"),
    "apartment": ("квартира", "公寓"),
    "home": ("дом", "家"),
    "meeting": ("встреча", "会议"),
    "business": ("бизнес", "商务"),
    "investment": ("инвестиции", "投资"),
    "investor": ("инвестор", "投资者"),
    "consultation": ("консультация", "咨询"),
    "office": ("офис", "办公室"),
    "city": ("город", "城市"),
    "skyline": ("скайлайн", "天际线"),
    "relocation": ("переезд", "移居"),
    "immigration": ("иммиграция", "移民"),
    "passport": ("паспорт", "护照"),
    "citizenship": ("гражданство", "公民身份"),
    "residency": ("резидентство", "居留"),
    "documents": ("документы", "文件"),
    "document": ("документ", "文件"),
    "property": ("недвижимость", "房产"),
    "real": ("", ""),
    "estate": ("недвижимость", "房产"),
    "balcony": ("балкон", "阳台"),
    "interior": ("интерьер", "室内"),
    "background": ("фон", "背景"),
    "cinematic": ("кинематографичный", "电影"),
    "premium": ("премиум", "高端"),
    "financial": ("финансовый", "金融"),
    "district": ("район", "区"),
    "packing": ("сборы", "收拾行李"),
    "suitcase": ("чемодан", "行李箱"),
    "arrival": ("прибытие", "抵达"),
    "travel": ("путешествие", "旅行"),
    "advisor": ("советник", "顾问"),
    "shareholder": ("акционер", "股东"),
    "capital": ("капитал", "资本"),
    "boardroom": ("переговорная", "会议室"),
    "condominium": ("кондоминиум", "公寓"),
    "lobby": ("лобби", "大堂"),
    "kitchen": ("кухня", "厨房"),
    "night": ("ночь", "夜景"),
}


def _tags(asset):
    raw = asset.get("tags") or []
    if isinstance(raw, dict):
        raw = raw.get("en-US") or raw.get("en") or []
    return [str(item).lower() for item in raw]


def _translate(tags, index):
    out = []
    for tag in tags:
        pair = GLOSSARY.get(tag)
        if not pair:
            continue
        word = pair[index]
        if word and word not in out:
            out.append(word)
    return out


def ensure_locales(asset: dict) -> dict:
    """Fill missing locale fields. Returns the same dict."""
    tags = _tags(asset)
    if not asset.get("tags_ru"):
        ru = _translate(tags, 0)
        if ru:
            asset["tags_ru"] = ru
    if not asset.get("tags_zh"):
        zh = _translate(tags, 1)
        if zh:
            asset["tags_zh"] = zh
    localized = asset.get("localized")
    if not isinstance(localized, dict):
        localized = {}
    title_en = (asset.get("description") if isinstance(asset.get("description"), str) else None) or " ".join(tags[:6])
    defaults = {
        "en-US": {"title": title_en, "description": title_en, "terms": tags[:12]},
        "ru-RU": {
            "title": " ".join(asset.get("tags_ru") or []) or title_en,
            "description": " ".join(asset.get("tags_ru") or []) or title_en,
            "terms": list(asset.get("tags_ru") or []),
        },
        "zh-CN": {
            "title": " ".join(asset.get("tags_zh") or []) or title_en,
            "description": " ".join(asset.get("tags_zh") or []) or title_en,
            "terms": list(asset.get("tags_zh") or []),
        },
    }
    for locale, block in defaults.items():
        if locale not in localized and (block.get("terms") or locale == "en-US"):
            localized[locale] = block
    if localized:
        asset["localized"] = localized
    if not asset.get("conceptId") and tags:
        asset["conceptId"] = ".".join(tags[:2])
    return asset


def locale_complete(asset: dict) -> bool:
    loc = asset.get("localized") or {}
    return all(locale in loc for locale in LOCALES) and bool(asset.get("tags_ru")) and bool(asset.get("tags_zh"))
