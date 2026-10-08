"""Project language is one locale. The director prompt, cards, and voice follow it."""
from backend.hypit_prompt import illustration_request
from backend.language import (
    LanguageError,
    audio_instruction,
    available_card_ids,
    build_language_directive,
    card_supports,
    default_locale,
    keep_source_audio,
    language_leak,
    validate_scene,
    voice_for,
)


HOOKS = {
    "en-US": "Location decides a lot when you buy property.",
    "ru-RU": "При покупке недвижимости расположение решает очень многое.",
    "zh-CN": "买房的时候，地段真的很重要。",
}


def test_the_prompt_names_library_files_and_not_the_spoken_line():
    from backend.hypit_prompt import animation_shots
    spoken = "Планируете переезд"
    prompt = illustration_request({
        "language": "ru-RU",
        "captions": [{"start": 0, "end": 6, "original": spoken, "ru": spoken}],
    })
    assert "--- MEDIA LIBRARY ---" in prompt
    assert "global_route_001 ./motion/global/global_route_001.webm" in prompt
    assert "people_door_001 ./static/people/people_door_001.png" in prompt
    assert spoken not in prompt
    shots = animation_shots({
        "language": "ru",
        "captions": [{"start": 1, "end": 8, "original": spoken, "ru": spoken}],
        "card_motion": 100,
    }, 40)
    assert shots[0]["library_id"] == "people_door_001"
    assert shots[0]["file"] == "1.mp4"
    assert shots[0]["library_path"].endswith("static/people/people_door_001.png")
    assert spoken not in shots[0]["library_path"]


def test_one_base_prompt_carries_each_directive():
    manual = {
        "captions": [{"original": "Планируете переезд"}],
        "card_motion": 60,
        "animation_intensity": 60,
        "animation_motion": 80,
        "animation_density": 70,
    }
    base = illustration_request(manual)
    for locale, marker in (("en-US", "English (en-US)"), ("ru-RU", "ru-RU"), ("zh-CN", "zh-CN")):
        prompt = illustration_request({**manual, "language": locale})
        assert prompt.startswith(base)
        assert prompt.index(base) < prompt.index("--- PROJECT LANGUAGE ---") < prompt.index("--- AVAILABLE CARDS ---")
        assert marker in prompt
        assert f'"locale": "{locale}"' in prompt
        assert build_language_directive(locale) in prompt
        assert "count: 25" in prompt
        assert "property_listing" in prompt
        assert "Планируете переезд" not in prompt
        assert len(available_card_ids(locale)) == 25


def test_same_language_keeps_the_original_voice():
    manual = {"language": "ru-RU", "captions": [{"original": "Планируете переезд"}]}
    assert keep_source_audio(manual) is True
    assert "Keep the original speaker audio." in audio_instruction(manual, "ru-RU")


def test_a_different_language_does_not_keep_the_source_audio():
    manual = {"language": "en-US", "captions": [{"original": "Планируете переезд"}]}
    assert keep_source_audio(manual) is False
    note = audio_instruction(manual, "en-US")
    assert "en-male" in note and "Do not keep the source-language audio." in note
    assert voice_for("en-US") == "en-male"
    assert voice_for("zh-CN") == "zh-male"


def test_missing_voice_is_named(monkeypatch):
    import backend.language as language
    monkeypatch.setitem(language.LANGUAGE_CONFIG["zh-CN"], "voice", "missing-voice")
    try:
        voice_for("zh-CN")
    except LanguageError as exc:
        assert exc.code == "MISSING_TARGET_LANGUAGE_VOICE"
        assert exc.locale == "zh-CN"
    else:
        raise AssertionError("missing voice was substituted")


def test_existing_projects_keep_a_detectable_language():
    assert default_locale(None, "Планируете переезд") == "ru-RU"
    assert default_locale("en", "") == "en-US"
    assert default_locale(None, "") == "en-US"
    assert default_locale("zh-CN", "English words") == "zh-CN"


def test_scene_locale_and_leaks():
    for locale, text in HOOKS.items():
        validate_scene({"locale": locale, "type": "kinetic_hook", "text": text}, locale)
        assert language_leak(text, locale) is None
    assert language_leak("Property Price", "ru-RU") == "Property Price"
    assert language_leak("Bangkok ROI", "ru-RU") is None
    try:
        validate_scene({"locale": "en-US", "type": "kinetic_hook", "text": "Hello"}, "ru-RU")
    except LanguageError as exc:
        assert exc.code == "scene_locale_mismatch"
    else:
        raise AssertionError("wrong scene locale was accepted")
    assert card_supports("property_listing", "zh-CN") is True
    assert card_supports("english_only", "en-US") is False
