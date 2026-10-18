"""The one project-language setting. Short codes stay at the edges that already speak ru/en/zh."""
from __future__ import annotations

import re

LOCALES = ("en-US", "ru-RU", "zh-CN")

LANGUAGE_CONFIG = {
    "en-US": {
        "label": "English",
        "promptName": "English",
        "script": "latin",
        "direction": "ltr",
        "typographyProfile": "latin",
        "voiceLocale": "en-US",
        "voice": "en-male",
        "code": "en",
    },
    "ru-RU": {
        "label": "Русский",
        "promptName": "Russian",
        "script": "cyrillic",
        "direction": "ltr",
        "typographyProfile": "cyrillic",
        "voiceLocale": "ru-RU",
        "voice": "ru-male",
        "code": "ru",
    },
    "zh-CN": {
        "label": "中文",
        "promptName": "Simplified Chinese",
        "script": "han",
        "direction": "ltr",
        "typographyProfile": "cjk",
        "voiceLocale": "zh-CN",
        "voice": "zh-male",
        "code": "zh",
    },
}

_CODES = {"en": "en-US", "ru": "ru-RU", "zh": "zh-CN", "en-us": "en-US", "ru-ru": "ru-RU", "zh-cn": "zh-CN"}

# Structural labels that must not leak into the wrong language. Brands and place names stay out.
_LEAKS = {
    "en-US": ("Стоимость недвижимости", "Доходность аренды", "租金回报率", "地段"),
    "ru-RU": ("Property Price", "Rental Yield", "租金回报率"),
    "zh-CN": ("Property Price", "Rental Yield", "Стоимость недвижимости", "Доходность аренды"),
}
_ALLOWED = {"Bangkok", "Бангкок", "曼谷", "BTS", "ROI", "THB", "HK Immigration"}

_DIRECTIVES = {
    "en-US": """--- PROJECT LANGUAGE ---

Target video language: English (en-US).

ALL viewer-facing language in this video must be natural English.

This includes:

- spoken script
- hooks
- captions
- headlines
- kinetic typography
- card text
- labels
- process steps
- comparison labels
- timeline labels
- CTA
- supporting copy

Use natural spoken English suitable for short-form social video.

Do not mix Russian or Chinese into viewer-facing content unless it is an intentional proper noun, brand name, official title, or source quotation.

All SceneDefinition objects must use:

"locale": "en-US"

Use English-compatible cards, typography and text segmentation.

--- END PROJECT LANGUAGE ---""",
    "ru-RU": """--- PROJECT LANGUAGE ---

Целевой язык видео: русский (ru-RU).

ВЕСЬ текст и речь, которые увидит или услышит зритель,
должны быть на естественном современном русском языке.

Это относится ко всему:

- речь ведущего
- hook
- субтитры
- заголовки
- kinetic typography
- карточки
- подписи
- этапы процессов
- сравнения
- timeline
- CTA
- поясняющий текст

Не делай буквальный перевод с английского.

Формулируй текст так, как его естественно сказал бы русскоязычный ведущий
в современном коротком видео.

Экранный текст должен быть коротким и хорошо читаться на телефоне.

Не смешивай английский или китайский с русским без необходимости.

Исключения:

- бренды
- имена
- официальные названия
- международные аббревиатуры
- термины, которые намеренно должны остаться в оригинале

Все SceneDefinition должны использовать:

"locale": "ru-RU"

Используй русские версии карточек,
Cyrillic typography profile
и русские правила сегментации текста.

--- END PROJECT LANGUAGE ---""",
    "zh-CN": """--- PROJECT LANGUAGE ---

目标视频语言：简体中文（zh-CN）。

所有观众能够看到或听到的语言内容都必须使用自然、流畅的简体中文。

包括：

- 主播语音
- 开场钩子
- 字幕
- 标题
- 动态文字
- 信息卡片
- 标签
- 流程步骤
- 对比内容
- 时间线
- CTA
- 辅助说明

不要逐字翻译英文。

使用适合短视频和社交媒体的自然中文表达。

屏幕文字应简洁、清晰，并适合手机阅读。

除品牌名、人名、官方名称、国际缩写或必须保留的原始术语外，
不要混入英文或俄文。

所有 SceneDefinition 必须使用：

"locale": "zh-CN"

使用中文卡片、
CJK typography profile
以及适合中文的文本分段和换行规则。

--- END PROJECT LANGUAGE ---""",
}

# Every current card supports all three locales. The Director must not invent an English-only card.
CARD_LOCALES = {locale: LOCALES for locale in (
    "kinetic_hook", "big_number", "property_price", "rental_yield", "roi", "cash_flow",
    "property_comparison", "buy_vs_rent", "progress_steps", "document_check", "property_features",
    "location", "amenities", "timeline", "before_after", "checklist", "stat_reveal", "quote",
    "cta", "caption_card", "property_listing", "investment_card", "location_card", "legal_card",
    "key_takeaway",
)}


class LanguageError(ValueError):
    def __init__(self, code, locale=None):
        self.code = code
        self.locale = locale
        super().__init__(code if not locale else f"{code}:{locale}")


def resolve_locale(value):
    """Accept a locale or the existing ru/en/zh code. None stays unset."""
    if value is None or value == "":
        return None
    text = str(value).strip()
    if text in LANGUAGE_CONFIG:
        return text
    mapped = _CODES.get(text.lower())
    if mapped:
        return mapped
    raise LanguageError("unsupported_language", text)


def short_code(locale):
    return LANGUAGE_CONFIG[locale]["code"]


def config_for(locale):
    return LANGUAGE_CONFIG[locale]


def build_language_directive(locale):
    locale = resolve_locale(locale)
    if not locale:
        raise LanguageError("unsupported_language")
    return _DIRECTIVES[locale]


def detect_source_locale(text):
    """The speech already in the source. Empty text is not a guess."""
    sample = text or ""
    if re.search(r"[\u4e00-\u9fff]", sample):
        return "zh-CN"
    if re.search(r"[\u0400-\u04ff]", sample):
        return "ru-RU"
    if re.search(r"[A-Za-z]", sample):
        return "en-US"
    return None


def default_locale(stored=None, transcript=""):
    """Existing short codes and a clear transcript win. Otherwise English."""
    try:
        chosen = resolve_locale(stored)
    except LanguageError:
        chosen = None
    if chosen:
        return chosen
    return detect_source_locale(transcript) or "en-US"


def voice_for(locale):
    from .dubbing_audio import VOICES
    locale = resolve_locale(locale)
    voice_id = LANGUAGE_CONFIG[locale]["voice"]
    voice = VOICES.get(voice_id)
    if not voice or voice["language"] != short_code(locale):
        raise LanguageError("MISSING_TARGET_LANGUAGE_VOICE", locale)
    return voice_id


# Qwen3-TTS on lumen-web-gpu can clone from a reference clip. This app does not.
CLONE_SUPPORTED = False


def resolve_voice(*, speaker=None, source_language=None, target_language=None, voice=None):
    """The voice for project.language. A different source language is a dub, not an error.

    Speech is recorded on the RunPod pod lumen-web-gpu with Qwen3-TTS CustomVoice.
    The speaker names are Ryan, Serena, Uncle_Fu and Vivian. A voice id belongs to
    one language. Nothing here clones the source speaker or calls OpenRouter for audio.
    """
    from .dubbing_audio import VOICES
    target = resolve_locale(target_language)
    if not target:
        raise LanguageError("unsupported_language", target_language)
    try:
        source = resolve_locale(source_language) if source_language else None
    except LanguageError:
        source = None
    if source == target or not source:
        return {
            "status": "resolved",
            "mode": "original",
            "path": "original",
            "voiceId": None,
            "providerVoice": None,
            "label": "Original speaker",
            "cloned": False,
        }
    code = short_code(target)

    def usable(voice_id):
        item = VOICES.get(voice_id)
        return bool(item and item["language"] == code)

    chosen = None
    path = None
    mapped = ((speaker or {}).get("voices") or {}).get(target) or {}
    explicit = voice or mapped.get("voiceId")
    if usable(explicit):
        chosen, path = explicit, "explicit"
    elif CLONE_SUPPORTED and usable(((speaker or {}).get("clone") or {}).get(target)):
        chosen, path = speaker["clone"][target], "clone"
    elif usable(LANGUAGE_CONFIG[target]["voice"]):
        chosen, path = LANGUAGE_CONFIG[target]["voice"], "project_default"
    else:
        for voice_id, item in VOICES.items():
            if item["language"] == code:
                chosen, path = voice_id, "application_default"
                break
    if not chosen:
        return {
            "status": "VOICE_SETUP_REQUIRED",
            "mode": "dubbed",
            "path": "VOICE_SETUP_REQUIRED",
            "voiceId": None,
            "providerVoice": None,
            "label": None,
            "cloned": False,
        }
    item = VOICES[chosen]
    return {
        "status": "resolved",
        "mode": "dubbed",
        "path": path,
        "voiceId": chosen,
        "providerVoice": item["voice"],
        "label": item["name"],
        "cloned": path == "clone",
    }


MOTION_IDS = (
    "kinetic_hook", "big_number", "progress_steps", "speaker_focus", "broll_caption",
    "timeline", "comparison", "split_screen", "checklist", "stat_reveal",
)


def available_card_ids(locale):
    locale = resolve_locale(locale)
    if not locale:
        raise LanguageError("unsupported_language")
    return [card_id for card_id, locales in CARD_LOCALES.items() if locale in locales]


def cards_block(locale):
    """The cards the director may choose. Structural labels stay in the dictionary."""
    locale = resolve_locale(locale)
    ids = available_card_ids(locale)
    profile = LANGUAGE_CONFIG[locale]["typographyProfile"]
    return (
        "--- AVAILABLE CARDS ---\n"
        f"locale: {locale}\n"
        f"typographyProfile: {profile}\n"
        f"count: {len(ids)}\n"
        f"ids: {', '.join(ids)}\n"
        "Use only these card ids. Structural labels resolve from this locale. "
        "Write creative copy in this locale only.\n"
        "--- END AVAILABLE CARDS ---"
    )


def director_context_blocks(locale):
    locale = resolve_locale(locale)
    motion = (
        "--- MOTION REGISTRY ---\n"
        + ", ".join(MOTION_IDS)
        + "\nThe director chooses a type and a variant. Typography follows the project language.\n"
        "--- END MOTION REGISTRY ---"
    )
    media = (
        "--- MEDIA LIBRARY ---\n"
        "Assets are language-neutral. Search by meaning in the project language. "
        "Do not ask for a separate file per language.\n"
        "--- END MEDIA LIBRARY ---"
    )
    context = (
        "--- PROJECT CONTEXT ---\n"
        "The user's original video is the video. The library enhances it. "
        f"Viewer-facing copy uses {locale}. The source transcript stays untouched.\n"
        "--- END PROJECT CONTEXT ---"
    )
    return cards_block(locale), motion, media, context


def card_supports(card_id, locale):
    locale = resolve_locale(locale)
    supported = CARD_LOCALES.get(card_id)
    return bool(supported) and locale in supported


def validate_scene(scene, locale):
    locale = resolve_locale(locale)
    if scene.get("locale") != locale:
        raise LanguageError("scene_locale_mismatch", scene.get("locale"))
    card = scene.get("type")
    if card and not card_supports(card, locale):
        raise LanguageError("card_locale_unsupported", card)
    profile = scene.get("typographyProfile")
    if profile and profile != LANGUAGE_CONFIG[locale]["typographyProfile"]:
        raise LanguageError("typography_profile_mismatch", profile)
    leak = language_leak(scene.get("text") or "", locale)
    if leak:
        raise LanguageError("language_leak", leak)
    return True


def language_leak(text, locale):
    locale = resolve_locale(locale)
    cleaned = text
    for allowed in _ALLOWED:
        cleaned = cleaned.replace(allowed, " ")
    for phrase in _LEAKS[locale]:
        if phrase in cleaned:
            return phrase
    return None


def _caption_text(manual):
    rows = manual.get("captions") if isinstance(manual, dict) else None
    if not rows and hasattr(manual, "captions"):
        rows = manual.captions
    parts = []
    for row in rows or []:
        if isinstance(row, dict):
            parts.append(row.get("original") or "")
        else:
            parts.append(getattr(row, "original", "") or "")
    return " ".join(parts)


def audio_instruction(manual, locale):
    """Say whether the original voice stays. Callers do not append this themselves."""
    locale = resolve_locale(locale)
    source = detect_source_locale(_caption_text(manual))
    if not source or source == locale:
        return f"Source speech matches the project language ({locale}). Keep the original speaker audio."
    voice = LANGUAGE_CONFIG[locale]["voice"]
    return (
        f"Source speech language: {LANGUAGE_CONFIG[source]['promptName']} ({source}). "
        f"Target speech language: {LANGUAGE_CONFIG[locale]['promptName']} ({locale}). "
        f"Use voice {voice}. Do not keep the source-language audio. "
        "Do not reuse source-language word timestamps. "
        "Align captions and motion to the target-language voice. "
        "Do not invent lip sync. Favor cards and B-roll over a long close-up of the mouth."
    )


def keep_source_audio(manual):
    """A different project language must not publish the source recording as its voice."""
    data = manual if isinstance(manual, dict) else {}
    target = data.get("language")
    if not target:
        return True
    try:
        locale = resolve_locale(target)
    except LanguageError:
        return True
    source = detect_source_locale(_caption_text(data))
    if not source:
        return True
    return source == locale


def rendition_dir(data_dir, project_id, locale):
    locale = resolve_locale(locale)
    return data_dir / project_id / "localization" / locale
