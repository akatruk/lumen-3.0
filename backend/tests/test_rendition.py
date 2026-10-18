"""Spoken renditions follow project.language. Source speech is not overwritten."""
import json
from pathlib import Path

import pytest

from backend.language import LanguageError
from backend.rendition import (
    cache_hit,
    caption_groups,
    invalidate,
    lip_sync_available,
    lip_sync_video,
    prepare,
    preview_request,
    script_hash,
    speak_money,
    store_source,
    translations_from_rows,
)


ROWS = [
    {"start": 0.0, "end": 2.4, "original": "Location matters more than most buyers think.", "ru": "Расположение влияет на покупку сильнее, чем думают многие.", "zh": "地段的重要性，往往比很多买家想象的更高。", "en": "Location matters more than most buyers think."},
    {"start": 2.4, "end": 5.0, "original": "The price is THB 8500000.", "ru": "Цена — 8 500 000 бат.", "zh": "价格是八百五十万泰铢。", "en": "The price is THB 8500000."},
]


def test_same_language_keeps_the_original_timing():
    rendition = prepare(ROWS, "en-US")
    assert rendition["audioMode"] == "original"
    assert rendition["status"] == "ready"
    assert rendition["timeline"]["duration"] == 5.0
    assert rendition["alignment"]["segments"][0]["id"] == "segment_001"
    assert rendition["alignment"]["segments"][0]["end"] == 2.4
    assert rendition["lipSync"] is False
    assert "eight point five million baht" in rendition["localizedScript"][1]["text"]
    assert all(scene["treatment"] == "speaker_focus" for scene in rendition["timeline"]["scenes"])


def test_another_language_uses_its_own_duration_and_script():
    russian = prepare(ROWS, "ru-RU", translations_from_rows(ROWS, "ru-RU"), durations=[3.1, 2.4])
    chinese = prepare(ROWS, "zh-CN", translations_from_rows(ROWS, "zh-CN"), durations=[2.0, 1.8])
    assert russian["alignment"]["segments"][0]["id"] == chinese["alignment"]["segments"][0]["id"] == "segment_001"
    assert russian["timeline"]["duration"] != 5.0
    assert russian["alignment"]["segments"][0]["end"] == 3.1
    assert chinese["alignment"]["segments"][0]["end"] == 2.0
    assert "Расположение" in russian["localizedScript"][0]["text"]
    assert "地段" in chinese["localizedScript"][0]["text"]
    assert russian["timeline"]["scenes"][0]["treatment"] == "editorial_dub"
    assert russian["captions"][0]["locale"] == "ru-RU"
    assert russian["captions"][0]["typographyProfile"] == "cyrillic"
    assert chinese["captions"][0]["typographyProfile"] == "cjk"


def test_missing_translation_does_not_invent_speech():
    with pytest.raises(LanguageError) as caught:
        prepare([{"start": 0, "end": 1, "original": "Hello there friend today"}], "ru-RU")
    assert caught.value.code == "localized_script_missing"


def test_spoken_money_keeps_one_value():
    assert speak_money(8_500_000, "en-US") == "eight point five million baht"
    assert speak_money(8_500_000, "ru-RU") == "восемь с половиной миллионов бат"
    assert speak_money(8_500_000, "zh-CN") == "八百五十万泰铢"


def test_caption_groups_follow_the_language():
    english = caption_groups("one two three four five six", "en-US")
    russian = caption_groups("один два три четыре пять", "ru-RU")
    chinese = caption_groups("地段的重要性，往往比很多买家想象的更高。", "zh-CN")
    assert all(2 <= len(group.split()) <= 6 for group in english)
    assert all(len(group.split()) <= 5 for group in russian)
    assert all(" " not in group for group in chinese)
    assert "".join(chinese).startswith("地段")


def test_a_script_change_drops_only_that_locale_audio():
    ready = prepare(ROWS, "ru-RU", translations_from_rows(ROWS, "ru-RU"), durations=[3.1, 2.4])
    assert cache_hit(ready, ready["localizedScript"], ready["voiceId"])
    cleared = invalidate(ready, "script")
    assert cleared["audio"] is None and cleared["timeline"] is None
    assert cleared["status"] == "not_generated"
    visual = invalidate(ready, "visual")
    assert visual["audio"] == ready["audio"]
    assert visual["render"] is None


def test_source_transcript_is_not_replaced(tmp_path: Path):
    folder = tmp_path / "localization"
    first = store_source(folder, ROWS)
    store_source(folder, [{"original": "A different script", "start": 0, "end": 1}])
    saved = json.loads((folder / "source-transcript.json").read_text())
    assert saved["text"] == first["text"]
    assert saved["sourceLanguage"] == "en-US"


def test_voice_preview_needs_a_provider(monkeypatch):
    monkeypatch.delenv("RUNPOD_API_KEY", raising=False)
    with pytest.raises(LanguageError) as caught:
        preview_request("zh-CN")
    assert caught.value.code == "provider_not_configured"
    assert lip_sync_available() is False
    with pytest.raises(LanguageError) as missing:
        lip_sync_video("audio.wav", "video.mp4")
    assert missing.value.code == "lip_sync_unavailable"


def test_language_leak_in_the_spoken_script():
    with pytest.raises(LanguageError) as caught:
        prepare(ROWS, "ru-RU", {"segment_001": "Property Price stays in English here", "segment_002": "Цена"}, durations=[1, 1])
    assert caught.value.code == "language_leak"
    assert script_hash([{"id": "segment_001", "text": "a"}], "ru-male") == script_hash([{"id": "segment_001", "text": "a"}], "ru-male")


def test_a_dub_follows_measured_speech_and_russian_stays_original(tmp_path):
    from backend.media import ffmpeg
    from backend.rendition import materialize_speech
    calls = []

    def synthesize(text, voice, dest):
        calls.append((text, voice))
        ffmpeg("-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "1.25", "-c:a", "libmp3lame", dest)

    rows = [{"start": 0.0, "end": 4.0, "original": "При покупке квартиры в первую очередь смотрите на локацию."}]
    english = materialize_speech(
        tmp_path / "en",
        rows,
        "en-US",
        synthesize,
        translations={"segment_001": "When buying a property, look at the location first."},
    )
    assert calls == [("When buying a property, look at the location first.", "en-male")]
    assert english["audioMode"] == "tts"
    assert english["alignment"]["segments"][0]["timing"] == "measured-duration"
    assert english["alignment"]["segments"][0]["end"] < 3
    assert english["voiceResolution"]["cloned"] is False
    same = materialize_speech(tmp_path / "ru", rows, "ru-RU", synthesize)
    assert same["audioMode"] == "original"
    assert len(calls) == 1
