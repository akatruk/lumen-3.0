"""Placeholder ASR must not poison Hypit graphics or cache."""
from backend.source_analysis import is_placeholder_transcript
from backend.hypit_prompt import animation_shots, _phrase_rows


def test_placeholder_detector():
    assert is_placeholder_transcript([{"text": "[segment 1]"}, {"text": "[segment 2]"}])
    assert not is_placeholder_transcript([{"text": "We help families buy apartments overseas."}])


def test_phrase_rows_skip_placeholder_captions():
    rows = _phrase_rows({
        "language": "en",
        "captions": [
            {"start": 0, "end": 4, "original": "[segment 1]", "en": "[segment 1]"},
            {"start": 4, "end": 10, "original": "Look at location first", "en": "Look at location first"},
        ],
    })
    assert len(rows) == 1
    assert rows[0][2] == "Look at location first"


def test_animation_shots_skip_placeholder_only_manual():
    shots = animation_shots({
        "language": "en",
        "card_motion": 100,
        "captions": [
            {"start": 0, "end": 8, "original": "[segment 1]", "en": "[segment 1]"},
        ],
    }, 20)
    assert shots == []
