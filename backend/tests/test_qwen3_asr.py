"""Qwen3-ASR stays off the Whisper path and does not invent speech."""

from backend.providers.transcript import get_transcript_provider
from backend.qwen3_segments import group_tokens
from backend.source_transcript import cache_matches_model


def test_character_timings_become_lines_and_zero_duration_is_kept_visible():
    segments, uncertain = group_tokens(
        [
            {"text": "买", "start": 0.0, "end": 0.2},
            {"text": "房", "start": 0.2, "end": 0.2},
            {"text": "诱", "start": 0.4, "end": 0.5},
            {"text": "第", "start": 1.4, "end": 1.6},
            {"text": "一", "start": 1.6, "end": 1.8},
        ],
        "买诱？第一",
    )
    assert uncertain[0]["reason"] == "zero_duration"
    assert uncertain[0]["text"] == "房"
    assert segments[0]["text"] == "买诱？"
    assert segments[0]["end"] == 0.5
    assert segments[1]["text"] == "第一"
    assert segments[1]["start"] == 1.4
    assert segments[1]["words"][0]["text"] == "第"


def test_qwen_model_does_not_select_whisper(monkeypatch):
    monkeypatch.setattr("backend.providers.transcript.settings.asr_model", "Qwen/Qwen3-ASR-1.7B")
    provider = get_transcript_provider()
    assert provider.name == "qwen3-asr"


def test_small_model_transcript_is_not_the_qwen_cache(monkeypatch):
    monkeypatch.setattr("backend.source_transcript.settings.asr_model", "Qwen/Qwen3-ASR-1.7B")
    monkeypatch.setattr("backend.source_transcript.settings.asr_config_version", "qwen3-asr-1.7b-bf16-cpu-align-0.6b-1")
    assert cache_matches_model({"provider": "whisperx", "modelId": "small", "configVersion": "cpu-int8-vad-1"}) is False


def test_a_correction_is_not_replaced_by_another_model(monkeypatch):
    monkeypatch.setattr("backend.source_transcript.settings.asr_model", "Qwen/Qwen3-ASR-1.7B")
    assert cache_matches_model({
        "provider": "whisperx",
        "modelId": "small",
        "corrections": [{"segmentId": "segment_001", "text": "成交"}],
    }) is True
