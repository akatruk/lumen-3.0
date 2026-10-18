"""Speech understanding: versioned transcript, local baseline, no keyword match."""

import json

import pytest

from backend.asr_memory import assert_can_load
from backend.passage_retrieval import apply_passage_media, select_asset
from backend.semantic_planner import PLANNER, PlannerError, build_local_baseline, validate_semantic_plan
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


def test_local_baseline_is_labeled_and_not_a_model():
    record = {
        "transcriptVersion": "source-transcript-1",
        "version": 1,
        "sourceLanguage": "zh-CN",
        "sourceChecksum": "abc",
        "segments": [{"id": "segment_001", "start": 0, "end": 2, "text": "很多人第一次来咨询"}],
    }
    plan = build_local_baseline(record)
    assert plan["planner"] == "local_baseline"
    assert plan["analysis_quality"] == "local_baseline"
    assert plan["model"] is None
    assert plan.get("topic") is None
    checked = validate_semantic_plan(plan, {"segment_001"})
    assert checked["planner"] == PLANNER
    with pytest.raises(PlannerError):
        validate_semantic_plan({
            "planner": "heuristic",
            "passages": [{
                "segment_ids": ["segment_001"],
                "intent": "spoken_line",
                "visual_need": "talking_head",
                "quote": "x",
            }],
        }, {"segment_001"})


def test_keyword_overlap_is_not_a_match():
    decision = select_asset(
        "the passport is stamped at the border",
        [{
            "id": "pass",
            "file": "passport.mp4",
            "status": "reviewed",
            "description": "passport stamp at the border",
        }],
    )
    assert decision["status"] == "NO_MATCH"
    assert any(item["reason"] == "keyword_overlap_not_acceptance" for item in decision["rejected"])
    specific = select_asset(
        "请看护照盖章",
        [
            {
                "id": "meet",
                "file": "meeting.mp4",
                "status": "accepted",
                "description": "passport stamp",
                "support": [{"all": ["会议"]}],
            },
            {
                "id": "pass",
                "file": "passport.mp4",
                "status": "accepted",
                "description": "unrelated words",
                "support": [{"all": ["护照", "盖章"]}],
            },
            {
                "id": "bad",
                "file": "x.mp4",
                "status": "quarantined",
                "description": "护照盖章",
                "support": [{"all": ["护照", "盖章"]}],
            },
        ],
    )
    assert specific["status"] == "selected"
    assert specific["assetId"] == "pass"
    assert specific["reason"] == "reviewed_support"


def test_no_match_clears_the_plate(tmp_path, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr("backend.source_transcript.settings.asr_model", "Qwen/Qwen3-ASR-1.7B")
    monkeypatch.setattr(
        "backend.source_transcript.settings.asr_config_version",
        "qwen3-asr-1.7b-bf16-cpu-align-0.6b-1",
    )
    pid = "c" * 32
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
            "detectedLanguage": "zh",
            "languageProbability": 0.99,
        },
        duration=2,
    )
    plan = apply_passage_media(
        {
            "scenes": [{
                "background": {"assetId": "office_stock", "file": "office.mp4"},
                "editorial": {"quoteSeconds": [0, 2]},
                "speaker": {"layout": "speaker_split_right"},
            }],
        },
        pid,
        [{"id": "segment_001", "start": 0, "end": 2, "text": "很多人第一次来咨询"}],
    )
    scene = plan["scenes"][0]
    assert scene["mediaDecision"]["status"] == "NO_MATCH"
    assert scene["background"]["assetId"] is None
    assert scene["speaker"]["layout"] == "speaker_fullscreen"
    assert plan["semanticPlan"]["planner"] == "local_baseline"
    stored = json.loads((tmp_path / pid / "localization" / "semantic-plan.json").read_text())
    assert stored["planner"] == "local_baseline"
    assert stored["model"] is None


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
