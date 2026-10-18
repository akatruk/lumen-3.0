"""Speech understanding: versioned transcript, local baseline, no keyword match."""

import json

import pytest

from backend.asr_memory import assert_can_load
from backend.passage_retrieval import select_asset
from backend.semantic_planner import PlannerError, validate_semantic_plan
from backend.source_analysis import _cache_valid
from backend.source_transcript import apply_correction, load_verified, save_verified


def test_low_memory_refuses_qwen():
    with pytest.raises(RuntimeError, match="TRANSCRIPTION_MEMORY"):
        assert_can_load(1200, minimum_mb=6200)


def test_correction_keeps_raw_and_bumps_version(tmp_path, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr("backend.source_transcript.settings.asr_model", "Qwen/Qwen3-ASR-1.7B")
    monkeypatch.setattr(
        "backend.source_transcript.settings.asr_config_version",
        "qwen3-asr-1.7b-bf16-cpu-align-0.6b-1",
    )
    pid = "b" * 32
    source = tmp_path / pid / "source"
    source.parent.mkdir()
    source.write_bytes(b"bytes")
    save_verified(
        pid,
        source,
        [{"start": 0, "end": 2, "text": "很多人第一次来咨询"}],
        provider="qwen3-asr",
        provenance={
            "modelId": "Qwen/Qwen3-ASR-1.7B",
            "configVersion": "qwen3-asr-1.7b-bf16-cpu-align-0.6b-1",
            "rawText": "很多人第一次来咨询",
            "detectedLanguage": "zh",
            "languageProbability": 0.99,
        },
        duration=2,
    )
    updated = apply_correction(pid, source, "segment_001", "新词很多人第一次来咨询")
    assert updated["version"] == 2
    assert updated["rawSegments"][0]["text"] == "很多人第一次来咨询"
    assert updated["segments"][0]["text"] == "新词很多人第一次来咨询"
    again = load_verified(pid, source)
    assert again["segments"][0]["text"] == "新词很多人第一次来咨询"
    assert again["provider"] == "qwen3-asr"


def test_edit_invalidates_cached_plan(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"video")
    meta = {
        "analysis_version": "source-v1",
        "source_checksum": __import__("hashlib").sha256(b"video").hexdigest(),
        "transcript_edit_version": 2,
        "plan_bound_transcript_edit": 1,
    }
    plan = {"transcript": [{"start": 0, "end": 1, "original": "hello there people"}]}
    assert _cache_valid(meta, source, plan) is False
    meta["plan_bound_transcript_edit"] = 2
    assert _cache_valid(meta, source, plan) is True








def test_qwen_failure_does_not_call_whisper(monkeypatch):
    from backend.qwen3_asr import QwenAsrError
    from backend.source_analysis import _transcribe_source

    monkeypatch.setattr("backend.source_analysis.get_transcript_provider", lambda: type("P", (), {"name": "qwen3-asr"})())

    def boom(*args, **kwargs):
        raise QwenAsrError("TRANSCRIPTION_PROVIDER_UNAVAILABLE")

    monkeypatch.setattr("backend.qwen3_asr.transcribe", boom)
    called = {"whisper": False}

    def whisper(*args, **kwargs):
        called["whisper"] = True
        return []

    monkeypatch.setattr("backend.whisperx_local.transcribe_segments", whisper)
    with pytest.raises(Exception, match="TRANSCRIPTION_PROVIDER_UNAVAILABLE"):
        _transcribe_source(__import__("pathlib").Path("/no/such/source"), duration=1, language=None)
    assert called["whisper"] is False


def test_semantic_plan_rejects_heuristic_and_unknown_segment():
    passage = {"segment_ids": ["segment_001"], "intent": "statement", "visual_treatment": "talking_head", "quote": "We explain the process."}
    with pytest.raises(PlannerError, match="PLANNER_INVALID"):
        validate_semantic_plan({"planner": "heuristic", "passages": [passage]}, {"segment_001"})
    with pytest.raises(PlannerError, match="PLANNER_INVALID"):
        validate_semantic_plan({"planner": "openrouter", "passages": [passage]}, {"segment_002"})


def test_asset_selection_rejects_missing_and_unsupported_files(tmp_path):
    decision = select_asset("passport", "Which passport documents?", [
        {"id": "missing", "file": "passport.png", "root": str(tmp_path), "tags": ["passport"]},
        {"id": "l3d_passport", "file": "passport.webm", "tags": ["passport"]},
    ])
    assert decision["status"] == "NO_MATCH"
    assert {row["reason"] for row in decision["rejected"]} == {"missing_file", "unsupported_plate"}
