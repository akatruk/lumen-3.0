"""Pipeline repair: transcript versions, planner failure, and no-match retrieval."""

import json

import pytest

from backend.asr_memory import assert_can_load
from backend.passage_retrieval import select_asset
from backend.qwen3_segments import group_tokens
from backend.semantic_planner import PlannerError, require_model, validate_semantic_plan
from backend.source_transcript import apply_correction, load_verified, save_verified
from backend.video_quality import validate_plan


def test_aligner_tokens_keep_their_times():
    segments, uncertain = group_tokens([
        {"text": "买房", "start": 0.1, "end": 0.4},
        {"text": "吗？", "start": 0.4, "end": 0.7},
        {"text": "然后", "start": 1.4, "end": 1.8},
        {"text": "x", "start": 2, "end": 2},
    ])
    assert uncertain[0]["reason"] == "zero_duration"
    assert segments[0]["text"] == "买房吗？"
    assert segments[0]["end"] == 0.7
    assert segments[1]["text"] == "然后"
    assert segments[1]["words"][0]["start"] == 1.4


def test_low_memory_refuses_qwen():
    with pytest.raises(RuntimeError, match="TRANSCRIPTION_MEMORY"):
        assert_can_load(1200, minimum_mb=6200)


def test_correction_keeps_raw_and_bumps_version(tmp_path, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "asr_model", "Qwen/Qwen3-ASR-1.7B")
    pid = "a" * 32
    source = tmp_path / pid / "source"
    source.parent.mkdir()
    source.write_bytes(b"bytes")
    save_verified(
        pid, source,
        [{"start": 0, "end": 2, "text": "旧词", "words": [{"text": "旧", "start": 0, "end": 1}]}],
        provider="qwen3-asr",
        provenance={"modelId": "Qwen/Qwen3-ASR-1.7B", "rawText": "旧词", "alignment": {"model": "Qwen/Qwen3-ForcedAligner-0.6B"}},
        declared_language="zh",
        duration=2,
    )
    updated = apply_correction(pid, source, "segment_001", "新词")
    assert updated["version"] == 2
    assert updated["rawSegments"][0]["text"] == "旧词"
    assert updated["segments"][0]["text"] == "新词"
    again = load_verified(pid, source)
    assert again["segments"][0]["text"] == "新词"


def test_qwen_provider_does_not_call_whisper(monkeypatch):
    from backend.config import settings
    from backend.providers.transcript import get_transcript_provider

    monkeypatch.setattr(settings, "asr_model", "Qwen/Qwen3-ASR-1.7B")
    called = {}

    def fake(video_path, language=None, on_phase=None):
        called["yes"] = True
        return {"speech": "speech", "segments": [{"start": 0, "end": 1, "text": "ok"}]}

    monkeypatch.setattr("backend.qwen3_asr.transcribe", fake)
    provider = get_transcript_provider()
    assert provider.name == "qwen3-asr"
    rows = provider.transcribe(__import__("pathlib").Path("source"))
    assert rows[0]["text"] == "ok"
    assert called["yes"] is True


def test_planner_rejects_invented_segment_and_missing_model(monkeypatch):
    from backend.config import settings

    with pytest.raises(PlannerError):
        validate_semantic_plan({
            "passages": [{
                "segment_ids": ["missing"],
                "intent": "Ask a question",
                "visual_need": "talking_head",
                "quote": "Really?",
            }],
        }, {"segment_001"})
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    with pytest.raises(PlannerError) as caught:
        require_model()
    assert caught.value.code == "PLANNER_UNAVAILABLE"


def test_unsupported_statistic_falls_back_without_stock():
    plan = validate_semantic_plan({
        "passages": [{
            "segment_ids": ["segment_001"],
            "intent": "statement",
            "visual_treatment": "animated_statistics",
            "visual_need": "explanatory_graphic",
            "visual_concept": "六个月",
            "semantic_reason": "The sentence states a duration.",
            "quote": "审批通常需要六个月。",
        }],
    }, {"segment_001"})
    passage = plan["passages"][0]
    assert passage["visual_treatment"] == "animated_statistics"
    assert passage["executed_treatment"] == "kinetic_typography"
    assert passage["fallback_treatment"] == "kinetic_typography"
    assert passage["renderer_capability"] == "beside_cards"


def test_semantic_beats_follow_segment_time(tmp_path, monkeypatch):
    from backend.config import settings
    from backend.passage_retrieval import apply_semantic_beats
    from backend.semantic_planner import plan_path

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    path = plan_path("pid")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "planner": "openrouter",
        "language": "zh",
        "topic": "passport",
        "passages": [
            {"segment_ids": ["segment_002"], "intent": "question", "visual_need": "supporting_broll",
             "visual_concept": "护照", "quote": "第二个护照需要哪些文件？"},
            {"segment_ids": ["segment_001"], "intent": "statement", "visual_need": "talking_head",
             "quote": "很多人以为境外投资很难。"},
        ],
    }), encoding="utf-8")
    out = apply_semantic_beats({"scenes": [{"sceneId": "hook", "query": "family home doorway relocation"}], "beatWeights": [1, 1, 1]}, "pid", [
        {"id": "segment_001", "start": 0, "end": 4, "text": "很多人以为境外投资很难。"},
        {"id": "segment_002", "start": 4, "end": 9, "text": "第二个护照需要哪些文件？"},
    ])
    assert [scene["sceneId"] for scene in out["scenes"]] == ["passage_01", "passage_02"]
    assert out["scenes"][0]["start"] == 0
    assert out["scenes"][0]["kind"] == "talking_head"
    assert out["beatWeights"] == [4000, 5000]
    assert out["form"] == "semantic"
    assert "hook" not in [scene["sceneId"] for scene in out["scenes"]]


def test_semantic_bounds_stay_within_one_frame():
    from backend.passage_retrieval import absolute_bounds

    scenes = [
        {"start": 0.0, "end": 4.2},
        {"start": 4.2, "end": 9.0},
        {"start": 9.0, "end": 13.4},
    ]
    frames, beats = absolute_bounds(scenes, 13.4)
    assert frames == 402
    assert beats == [(0, 126), (126, 270), (270, 402)]
    for scene, (start, end) in zip(scenes, beats):
        assert abs(start / 30 - scene["start"]) * 1000 <= 150
        assert abs(end / 30 - scene["end"]) * 1000 <= 150


def test_missing_library_file_is_not_referenced(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    (root / "icon.png").write_bytes(b"png")
    decision = select_asset("passport", "second passport", [
        {"id": "gone", "file": "missing.png", "description": "passport", "status": "reviewed", "root": str(root)},
        {"id": "icon", "file": "icon.png", "description": "passport", "status": "reviewed", "root": str(root)},
    ])
    assert decision["assetId"] == "icon"
    assert all(item["id"] != "gone" or item["reason"] == "missing_file" for item in decision["rejected"])


def test_webm_plate_is_rejected():
    decision = select_asset("护照", "第二个护照需要哪些文件？", [
        {"id": "l3d_generic_passport__open", "file": "motion/premium3d/passport.webm", "description": "passport", "status": "reviewed"},
        {"id": "photo", "file": "photos/passport.jpg", "description": "passport stamp", "status": "reviewed"},
    ])
    assert decision["assetId"] == "photo"
    assert any(item["reason"] == "unsupported_plate" for item in decision["rejected"])


def test_question_and_number_cannot_stay_talking_head():
    with pytest.raises(PlannerError):
        validate_semantic_plan({
            "passages": [{
                "segment_ids": ["segment_001"],
                "intent": "问题",
                "visual_need": "talking_head",
                "quote": "第二个护照需要哪些文件？",
            }],
        }, {"segment_001"})


def test_semantic_provider_does_not_fall_back_to_heuristic(monkeypatch):
    from backend.config import settings
    from backend.providers.director import HeuristicDirectorProvider, get_director_provider

    monkeypatch.setattr(settings, "semantic_planner_required", True)
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    provider = get_director_provider("semantic")
    assert not isinstance(provider, HeuristicDirectorProvider)
    with pytest.raises(PlannerError) as caught:
        provider.build_plan(
            duration=4,
            language="zh",
            transcript=[{"id": "segment_001", "start": 0, "end": 2, "text": "第二个护照需要哪些文件？"}],
            project_id="p",
        )
    assert caught.value.code == "PLANNER_UNAVAILABLE"
    assert isinstance(get_director_provider("none"), HeuristicDirectorProvider)


def test_revalidate_replaces_rewritten_query(tmp_path, monkeypatch):
    from backend.config import settings
    from backend.passage_retrieval import revalidate_assets
    from backend.semantic_planner import plan_path

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "semantic_planner_required", True)
    path = plan_path("pid")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "planner": "openrouter",
        "language": "zh",
        "topic": "passport documents",
        "passages": [{
            "segment_ids": ["segment_001"],
            "intent": "question",
            "visual_need": "supporting_broll",
            "visual_concept": "passport stamp",
            "quote": "第二个护照需要哪些文件？",
        }],
    }), encoding="utf-8")
    visual = {"scenes": [{
        "start": 0, "end": 4, "query": "business meeting",
        "assetId": "office",
        "background": {"assetId": "office", "query": "business meeting", "file": "office.mp4"},
    }]}
    catalog = [
        {"id": "office", "file": "office.mp4", "description": "business meeting", "status": "reviewed"},
        {"id": "stamp", "file": "stamp.mp4", "description": "passport stamp document", "status": "reviewed"},
        {"id": "bad", "file": "bad.mp4", "description": "passport stamp", "status": "quarantined"},
    ]
    out = revalidate_assets(visual, "pid", [{
        "id": "segment_001", "start": 0, "end": 4, "text": "第二个护照需要哪些文件？",
    }], catalog=catalog)
    scene = out["scenes"][0]
    assert scene["assetId"] == "stamp"
    assert "passport" in scene["mediaDecision"]["reason"]
    assert any(item["id"] == "bad" for item in scene["mediaDecision"]["rejected"])


def test_business_keyword_is_not_a_match():
    decision = select_asset(
        "business meeting",
        "the business is growing",
        [{
            "id": "meet",
            "file": "meeting.mp4",
            "status": "reviewed",
            "description": "business meeting in an office",
        }],
    )
    assert decision["status"] == "NO_MATCH"
    specific = select_asset(
        "passport stamp",
        "the passport is stamped",
        [
            {"id": "meet", "file": "meeting.mp4", "status": "reviewed", "description": "business meeting"},
            {"id": "pass", "file": "passport.mp4", "status": "reviewed", "description": "passport stamp at the border"},
            {"id": "bad", "file": "x.mp4", "status": "quarantined", "description": "passport stamp"},
        ],
    )
    assert specific["status"] == "selected"
    assert specific["assetId"] == "pass"
    assert any(item["reason"] == "ineligible" for item in specific["rejected"])


def test_quality_report_does_not_claim_human_review():
    report = validate_plan(
        {"scenes": [{"sceneId": "a", "mediaDecision": {"status": "NO_MATCH"}, "background": {}}]},
        [{"text": "hello"}],
    )
    assert report["humanReviewRequired"] is True
    assert report["ok"] is True


def test_edit_invalidates_cached_plan(tmp_path, monkeypatch):
    from backend.config import settings
    from backend.source_analysis import _cache_valid

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    source = tmp_path / "source"
    source.write_bytes(b"video")
    meta = {
        "analysis_version": "source-v1",
        "source_checksum": __import__("hashlib").sha256(b"video").hexdigest(),
        "transcript_edit_version": 2,
        "plan_bound_transcript_edit": 1,
    }
    plan = {"transcript": [{"start": 0, "end": 1, "original": "hello there"}]}
    assert _cache_valid(meta, source, plan) is False
    meta["plan_bound_transcript_edit"] = 2
    assert _cache_valid(meta, source, plan) is True
    json.dumps(plan)
