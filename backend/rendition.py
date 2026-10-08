"""One project, three spoken renditions. The existing voice list is the only provider map."""
from __future__ import annotations

import hashlib
import json
import re

from .language import (
    LANGUAGE_CONFIG,
    LanguageError,
    detect_source_locale,
    language_leak,
    resolve_locale,
    voice_for,
)

STATUSES = ("not_generated", "script_ready", "audio_ready", "aligned", "ready", "rendered", "error", "voice_error")
GAP = 0.12

PREVIEW_LINE = {
    "en-US": "Location matters more than most buyers think.",
    "ru-RU": "Расположение влияет на покупку сильнее, чем думают многие.",
    "zh-CN": "地段的重要性，往往比很多买家想象的更高。",
}

SPOKEN_MONEY = {
    "en-US": "baht",
    "ru-RU": "бат",
    "zh-CN": "泰铢",
}


def speaker_profile(locale):
    """The mapped voice for this locale. There is no clone and no random fallback."""
    locale = resolve_locale(locale)
    voice_id = voice_for(locale)
    from .dubbing_audio import VOICES
    voice = VOICES[voice_id]
    return {
        "id": "main-presenter",
        "voices": {
            locale: {
                "provider": "openrouter",
                "voiceId": voice_id,
                "providerVoice": voice["voice"],
                "name": voice["name"],
                "mode": "tts",
            }
        },
    }


def validate_voice(locale, *, need_provider=False):
    locale = resolve_locale(locale)
    profile = speaker_profile(locale)["voices"][locale]
    if need_provider:
        from .config import settings
        if not settings.openrouter_api_key:
            raise LanguageError("provider_not_configured", locale)
    return profile


def translations_from_rows(rows, locale):
    """Use a translation that is already stored on the phrase. Do not invent one."""
    from .language import short_code
    code = short_code(resolve_locale(locale))
    found = {}
    index = 1
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        original = (row.get("original") or "").strip()
        if not original:
            continue
        text = (row.get(code) or "").strip()
        if text:
            found[f"segment_{index:03d}"] = text
        index += 1
    segments = semantic_segments(rows)
    if len(found) != len(segments):
        return None
    return found


def semantic_segments(rows):
    """Stable ids from the source transcript. Word position is not the link."""
    segments = []
    index = 1
    for row in rows or []:
        if not isinstance(row, dict):
            row = {"original": getattr(row, "original", "") or "", "start": getattr(row, "start", 0), "end": getattr(row, "end", 0)}
        text = (row.get("original") or row.get("en") or row.get("ru") or row.get("zh") or "").strip()
        if not text:
            continue
        segments.append({
            "id": f"segment_{index:03d}",
            "text": text,
            "start": float(row.get("start") or 0),
            "end": float(row.get("end") or 0),
        })
        index += 1
    return segments


def source_record(rows):
    segments = semantic_segments(rows)
    text = " ".join(segment["text"] for segment in segments)
    return {
        "sourceLanguage": detect_source_locale(text),
        "text": text,
        "segments": segments,
    }


def speak_money(amount, locale, currency="THB"):
    """The same number, spoken. The picture keeps its own formatting."""
    locale = resolve_locale(locale)
    if currency != "THB":
        raise LanguageError("unsupported_currency", currency)
    unit = SPOKEN_MONEY[locale]
    millions = amount / 1_000_000
    if locale == "zh-CN":
        if amount % 10000 == 0:
            wan = int(amount / 10000)
            return f"{_chinese_int(wan)}万{unit}"
        return f"{_chinese_int(int(amount))}{unit}"
    if locale == "ru-RU" and abs(millions * 2 - round(millions * 2)) < 1e-6 and millions >= 1:
        whole = int(millions)
        half = abs(millions - whole - 0.5) < 1e-6
        if half:
            return f"{_russian_under_ten(whole)} с половиной миллионов {unit}"
        if millions == int(millions):
            return f"{_russian_under_ten(int(millions))} миллионов {unit}"
    if locale == "en-US":
        if abs(millions - round(millions, 1)) < 1e-6 and millions >= 1:
            shown = f"{millions:.1f}".rstrip("0").rstrip(".")
            words = _english_million(shown)
            return f"{words} million {unit}"
    return f"{amount:g} {unit}"


def apply_pronunciation(text, locale):
    """Say a baht amount. Leave place names and brands as written."""
    locale = resolve_locale(locale)

    def money(match):
        digits = re.sub(r"\D", "", match.group(1))
        if not digits:
            return match.group(0)
        return speak_money(int(digits), locale)

    spoken = re.sub(r"\bTHB\s*([\d][\d\s,]*)", money, text)
    if spoken == text:
        spoken = re.sub(r"\bTHB\b", SPOKEN_MONEY[locale], text)
    return spoken


def localize_script(segments, locale, source_locale, translations=None):
    """Same language keeps the speaker's words. A translation must arrive by segment id."""
    locale = resolve_locale(locale)
    source_locale = resolve_locale(source_locale) if source_locale else None
    spoken = []
    for segment in segments:
        if source_locale == locale or not source_locale:
            text = segment["text"]
        else:
            if not translations or segment["id"] not in translations:
                raise LanguageError("localized_script_missing", segment["id"])
            text = translations[segment["id"]].strip()
            if not text:
                raise LanguageError("localized_script_missing", segment["id"])
            leak = language_leak(text, locale)
            if leak:
                raise LanguageError("language_leak", leak)
        spoken.append({
            "id": segment["id"],
            "text": apply_pronunciation(text, locale),
            "sourceText": segment["text"],
        })
    return spoken


def caption_groups(text, locale):
    locale = resolve_locale(locale)
    if locale == "zh-CN":
        parts = [part.strip() for part in re.split(r"(?<=[，。！？、])", text) if part.strip()]
        groups = []
        for part in parts or [text]:
            if len(part) <= 12:
                groups.append(part)
            else:
                groups.extend(_chunks(part, 12))
        return groups
    words = text.split()
    limit = 6 if locale == "en-US" else 5
    groups = []
    bucket = []
    for word in words:
        if len(bucket) >= limit:
            groups.append(" ".join(bucket))
            bucket = []
        bucket.append(word)
    if bucket:
        groups.append(" ".join(bucket))
    return groups


def align_segments(segments, durations, *, gap=GAP):
    """Phrase times come from the target audio. Source word times are not reused."""
    cursor = 0.0
    aligned = []
    for segment, duration in zip(segments, durations):
        duration = float(duration)
        if duration <= 0:
            raise LanguageError("alignment_invalid", segment["id"])
        start = round(cursor, 3)
        end = round(cursor + duration, 3)
        aligned.append({
            "id": segment["id"],
            "text": segment["text"],
            "start": start,
            "end": end,
            "timing": "measured-duration",
            "tokens": _token_spans(segment["text"], start, end),
        })
        cursor = end + gap
    return {"duration": round(max(0.0, cursor - gap), 3), "segments": aligned}


def original_alignment(segments):
    """The upload already contains this language, so its own timestamps stay."""
    aligned = []
    for segment in segments:
        aligned.append({
            "id": segment["id"],
            "text": segment["text"],
            "start": round(float(segment["start"]), 3),
            "end": round(float(segment["end"]), 3),
            "timing": "source",
            "tokens": _token_spans(segment["text"], float(segment["start"]), float(segment["end"])),
        })
    end = max((row["end"] for row in aligned), default=0.0)
    return {"duration": round(end, 3), "segments": aligned}


def captions_from_alignment(alignment, locale):
    locale = resolve_locale(locale)
    captions = []
    for segment in alignment["segments"]:
        groups = caption_groups(segment["text"], locale)
        span = segment["end"] - segment["start"]
        cursor = segment["start"]
        for index, group in enumerate(groups):
            share = span * (len(group) / max(1, sum(len(item) for item in groups)))
            start = round(cursor, 3)
            end = round(segment["end"] if index == len(groups) - 1 else cursor + share, 3)
            captions.append({
                "id": f"{segment['id']}-c{index + 1}",
                "segmentId": segment["id"],
                "text": group,
                "start": start,
                "end": end,
                "locale": locale,
                "typographyProfile": LANGUAGE_CONFIG[locale]["typographyProfile"],
            })
            cursor = end
    return captions


def resolve_timeline(locale, alignment, *, source_locale, source_spans=None, scene_type="speaker_focus"):
    """Pass 2. Scene length follows the spoken rendition, not the other language."""
    locale = resolve_locale(locale)
    dubbed = bool(source_locale) and resolve_locale(source_locale) != locale
    source_spans = source_spans or {}
    scenes = []
    for segment in alignment["segments"]:
        audio_span = segment["end"] - segment["start"]
        source_span = source_spans.get(segment["id"])
        stretch = round(audio_span / source_span, 3) if source_span else 1
        scenes.append({
            "id": f"scene_{segment['id']}",
            "semanticSegmentIds": [segment["id"]],
            "locale": locale,
            "start": segment["start"],
            "end": segment["end"],
            "treatment": "editorial_dub" if dubbed else scene_type,
            "audio": {"start": segment["start"], "end": segment["end"]},
            "captionIds": [f"{segment['id']}-c1"],
            "motionTiming": {"tokens": segment["tokens"]},
            "broll": {"maxStretch": 1.25, "stretch": stretch},
            "lipSync": None,
        })
    return {
        "locale": locale,
        "duration": alignment["duration"],
        "sourceLanguage": source_locale,
        "lipSync": False,
        "scenes": scenes,
    }


def script_hash(segments, voice_id):
    payload = json.dumps({"segments": segments, "voice": voice_id}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def cache_hit(saved, segments, voice_id):
    if not saved:
        return False
    return saved.get("scriptHash") == script_hash(segments, voice_id) and saved.get("status") in {"audio_ready", "aligned", "ready", "rendered"}


def invalidate(saved, reason):
    """Drop spoken artifacts for this locale only."""
    kept = {
        "locale": saved.get("locale"),
        "sourceLanguage": saved.get("sourceLanguage"),
        "status": "not_generated" if reason == "script" else "voice_error" if reason == "voice" else "error",
        "localizedScript": None if reason == "script" else saved.get("localizedScript"),
        "audio": None,
        "alignment": None,
        "captions": None,
        "timeline": None,
        "render": saved.get("render") if reason == "visual" else None,
    }
    if reason == "visual":
        kept.update({
            "status": saved.get("status"),
            "localizedScript": saved.get("localizedScript"),
            "audio": saved.get("audio"),
            "alignment": saved.get("alignment"),
            "captions": saved.get("captions"),
            "timeline": saved.get("timeline"),
            "render": None,
        })
    return kept


def prepare(rows, locale, translations=None, durations=None):
    """Build one rendition. Audio bytes are supplied as durations, never invented."""
    locale = resolve_locale(locale)
    source = source_record(rows)
    source_locale = source["sourceLanguage"]
    profile = validate_voice(locale)
    spans = {segment["id"]: max(0.0, segment["end"] - segment["start"]) for segment in source["segments"]}
    if source_locale == locale or not source_locale:
        spoken = localize_script(source["segments"], locale, source_locale)
        timed = []
        for segment, line in zip(source["segments"], spoken):
            timed.append({**segment, "text": line["text"]})
        alignment = original_alignment(timed)
        status = "ready"
        audio_mode = "original"
        voice_id = None
    else:
        spoken = localize_script(source["segments"], locale, source_locale, translations)
        if not durations:
            return {
                "locale": locale,
                "sourceLanguage": source_locale,
                "status": "script_ready",
                "audioMode": "tts",
                "voice": profile,
                "localizedScript": spoken,
                "audio": None,
                "alignment": None,
                "captions": None,
                "timeline": None,
                "render": None,
                "scriptHash": script_hash(spoken, profile["voiceId"]),
            }
        if len(durations) != len(spoken):
            raise LanguageError("alignment_invalid", locale)
        alignment = align_segments(spoken, durations)
        status = "aligned"
        audio_mode = "tts"
        voice_id = profile["voiceId"]
    captions = captions_from_alignment(alignment, locale)
    timeline = resolve_timeline(locale, alignment, source_locale=source_locale, source_spans=spans)
    return {
        "locale": locale,
        "sourceLanguage": source_locale,
        "status": status,
        "audioMode": audio_mode,
        "voice": None if audio_mode == "original" else profile,
        "voiceId": voice_id,
        "localizedScript": spoken,
        "audio": {"mode": audio_mode, "segments": [segment["id"] for segment in spoken]},
        "alignment": alignment,
        "captions": captions,
        "timeline": timeline,
        "render": None,
        "scriptHash": script_hash(spoken, voice_id),
        "lipSync": False,
    }


def preview_request(locale):
    locale = resolve_locale(locale)
    profile = validate_voice(locale, need_provider=True)
    return {"locale": locale, "text": PREVIEW_LINE[locale], "voice": profile}


def store_source(folder, rows):
    """Write the source transcript once. A language switch must not replace it."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "source-transcript.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    record = source_record(rows)
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return record


def store_rendition(folder, rendition):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "rendition.json"
    if path.is_file():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if cache_hit(saved, rendition.get("localizedScript") or [], rendition.get("voiceId")):
            return saved
    path.write_text(json.dumps(rendition, ensure_ascii=False), encoding="utf-8")
    return rendition


def lip_sync_available():
    return False


def lip_sync_video(audio_path, video_path):
    """A later provider can replace this. This phase does not invent mouth movement."""
    del audio_path, video_path
    raise LanguageError("lip_sync_unavailable")


def _token_spans(text, start, end):
    tokens = [token for token in re.split(r"\s+", text.strip()) if token] or [text]
    span = max(0.0, end - start)
    cursor = start
    rows = []
    for index, token in enumerate(tokens):
        share = span * (len(token) / max(1, sum(len(item) for item in tokens)))
        token_end = end if index == len(tokens) - 1 else cursor + share
        rows.append({"text": token, "start": round(cursor, 3), "end": round(token_end, 3)})
        cursor = token_end
    return rows


def _chunks(text, size):
    closers = "，。！？、"
    groups = []
    current = ""
    for char in text:
        current += char
        if len(current) >= size and char not in closers:
            groups.append(current)
            current = ""
    if current:
        if groups and current[0] in closers:
            groups[-1] += current
        else:
            groups.append(current)
    return groups


def _english_million(shown):
    words = {
        "1": "one", "2": "two", "3": "three", "4": "four", "5": "five",
        "6": "six", "7": "seven", "8": "eight", "9": "nine",
    }
    if "." not in shown:
        return words.get(shown, shown)
    whole, fraction = shown.split(".", 1)
    return f"{words.get(whole, whole)} point {words.get(fraction, fraction)}"


def _russian_under_ten(value):
    words = {
        1: "один", 2: "два", 3: "три", 4: "четыре", 5: "пять",
        6: "шесть", 7: "семь", 8: "восемь", 9: "девять",
    }
    return words.get(value, str(value))


def _chinese_int(value):
    digits = "零一二三四五六七八九"
    if value < 10:
        return digits[value]
    if value < 100:
        tens, rest = divmod(value, 10)
        head = "" if tens == 1 else digits[tens]
        return head + "十" + (digits[rest] if rest else "")
    if value < 1000:
        hundreds, rest = divmod(value, 100)
        tail = "" if rest == 0 else _chinese_int(rest)
        return digits[hundreds] + "百" + tail
    if value < 10000:
        thousands, rest = divmod(value, 1000)
        tail = "" if rest == 0 else _chinese_int(rest)
        return digits[thousands] + "千" + tail
    return str(value)
