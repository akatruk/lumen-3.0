"""One-shot editorial plan: schema, no repair call, labels survive into Remotion props."""
import json

import pytest

from backend.semantic_planner import PlannerError, validate_semantic_plan


def _passage(**extra):
    row = {
        "segment_ids": ["segment_001"],
        "intent": "enumeration",
        "narrative_role": "evidence",
        "visual_treatment": "process",
        "visual_need": "explanatory_graphic",
        "visual_concept": "工资完税单",
        "semantic_reason": "The sentence names the document.",
        "confidence": 0.9,
        "quote": "包括工资完税单",
        "labels": ["工资完税单"],
        "review_note": "",
    }
    row.update(extra)
    return row


def test_contiguous_chinese_label_passes():
    quote = "请准备房屋买卖合同和完税证明"
    plan = validate_semantic_plan({
        "language": "zh",
        "topic": "documents",
        "passages": [_passage(quote=quote, labels=["房屋买卖合同", "完税证明"], visual_concept="")],
    }, {"segment_001"})
    assert plan["passages"][0]["labels"] == ["房屋买卖合同", "完税证明"]
    assert plan["passages"][0]["renderer_capability"] == "clean_steps"
    assert plan["passages"][0]["visual_concept"] in (None, "")


def test_paraphrased_and_noncontiguous_labels_fail():
    quote = "请准备房屋买卖合同和完税证明"
    with pytest.raises(PlannerError) as caught:
        validate_semantic_plan({
            "language": "zh",
            "topic": "documents",
            "passages": [_passage(quote=quote, labels=["房屋合同", "完税单"], visual_concept="")],
        }, {"segment_001"})
    values = {item["value"] for item in caught.value.issues}
    assert values == {"房屋合同", "完税单"}
    assert {item["error"] for item in caught.value.issues} == {"label_not_in_quote"}
    assert all(item["quote"] == quote and item["field"] == "labels" for item in caught.value.issues)


def test_label_copied_from_another_passage_fails():
    with pytest.raises(PlannerError) as caught:
        validate_semantic_plan({
            "language": "zh",
            "topic": "documents",
            "passages": [
                _passage(quote="先说背景", labels=["完税证明"], visual_concept=""),
                _passage(quote="请准备完税证明", labels=["完税证明"], visual_concept=""),
            ],
        }, {"segment_001"})
    failed = [item for item in caught.value.issues if item["value"] == "完税证明"]
    assert failed[0]["passage"] == 1
    assert failed[0]["error"] == "label_not_in_quote"


def test_layout_name_is_not_a_media_id():
    with pytest.raises(PlannerError) as caught:
        validate_semantic_plan({
            "language": "zh",
            "topic": "documents",
            "passages": [_passage(visual_treatment="supporting_broll", visual_concept="split_plate", labels=[])],
        }, {"segment_001"}, media_ids={"icon_goal"})
    assert caught.value.issues[0]["error"] == "layout_name_used_as_media_id"
    assert caught.value.issues[0]["value"] == "split_plate"
    assert caught.value.issues[0]["field"] == "visual_concept"


def test_real_inventory_id_passes():
    plan = validate_semantic_plan({
        "language": "zh",
        "topic": "documents",
        "passages": [_passage(visual_treatment="supporting_broll", visual_concept="icon_goal", labels=[])],
    }, {"segment_001"}, media_ids={"icon_goal"})
    assert plan["passages"][0]["executed_treatment"] == "supporting_broll"
    assert plan["passages"][0]["visual_concept"] == "icon_goal"


def test_quote_assigned_to_the_wrong_segment_fails():
    with pytest.raises(PlannerError) as caught:
        validate_semantic_plan({
            "language": "zh",
            "topic": "documents",
            "passages": [_passage(segment_ids=["segment_002"], quote="包括工资完税单", labels=["工资完税单"])],
        }, {"segment_001", "segment_002"}, segments={
            "segment_001": "包括工资完税单",
            "segment_002": "资金打入监管账户",
        })
    assert caught.value.issues[0]["error"] == "quote_not_in_cited_segments"
    assert caught.value.issues[0]["segment_ids"] == ["segment_002"]


def test_numbered_process_with_verbatim_labels_needs_no_concept():
    quote = "还会引入反洗钱数据库穿透审查你过去五年到十年的资金积累链条"
    plan = validate_semantic_plan({
        "language": "zh",
        "topic": "review",
        "passages": [_passage(
            quote=quote,
            labels=["反洗钱数据库", "资金积累链条"],
            visual_concept="",
            visual_treatment="process",
        )],
    }, {"segment_001"})
    assert plan["passages"][0]["labels"] == ["反洗钱数据库", "资金积累链条"]
    assert plan["passages"][0]["visual_concept"] in (None, "")


def test_label_outside_the_quote_is_rejected():
    with pytest.raises(PlannerError) as caught:
        validate_semantic_plan({
            "language": "zh",
            "topic": "documents",
            "passages": [_passage(labels=["股权转让协议"])],
        }, {"segment_001"})
    assert caught.value.feedback == "label_not_in_quote"


def test_one_shot_requests_a_single_call(tmp_path, monkeypatch):
    from backend.config import settings
    from backend.semantic_planner import plan_editorial_once

    monkeypatch.setattr(settings, "data_dir", tmp_path)

    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    calls = []

    class _Plan:
        def model_dump(self):
            return {
                "transcript_version": 1,
                "language": "zh",
                "topic": "documents",
                "passages": [_passage()],
            }

    def fake_json_call(*_args, **kwargs):
        calls.append(kwargs)
        return _Plan()

    monkeypatch.setattr("backend.providers.llm.OpenRouterLLMProvider.json_call", fake_json_call)
    plan = plan_editorial_once(
        "pid",
        [{"id": "segment_001", "start": 0, "end": 2, "text": "包括工资完税单", "words": []}],
        "zh-CN",
        duration=2,
        media=[{"id": "icon_goal", "description": "A line icon."}],
    )
    assert len(calls) == 1
    assert calls[0]["allow_repair"] is False
    assert calls[0]["attach_video"] is False
    assert plan["planner"] == "openrouter"
    assert plan["passages"][0]["labels"] == ["工资完税单"]


def test_supplied_labels_survive_editorial_decision_and_scene_plan(tmp_path, monkeypatch):
    from backend.config import settings
    from backend.editorial_decision import apply_editorial_decision
    from backend.passage_retrieval import apply_semantic_beats
    from backend.remotion_engine import resolve_scene_plan
    from backend.semantic_planner import plan_path

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    speech = "包括工资完税单"
    words = []
    cursor = 0.0
    for char in speech:
        words.append({"text": char, "start": round(cursor, 3), "end": round(cursor + 0.4, 3)})
        cursor += 0.4
    path = plan_path("pid")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "planner": "openrouter",
        "language": "zh",
        "topic": "documents",
        "passages": [_passage()],
    }), encoding="utf-8")
    transcript = [{"id": "segment_001", "start": 0, "end": cursor, "text": speech, "words": words}]
    planned = apply_semantic_beats({"scenes": [{"sceneId": "hook"}]}, "pid", transcript)
    decided = apply_editorial_decision(
        planned, transcript, locale="zh-CN", target_seconds=cursor, source_seconds=cursor, duration_mode="full",
    )
    assert planned["form"] == "semantic"
    assert [(scene["start"], scene["end"]) for scene in decided["scenes"]] == [
        (scene["start"], scene["end"]) for scene in planned["scenes"]
    ]
    labeled = [scene for scene in decided["scenes"] if scene.get("steps")]
    assert labeled
    assert labeled[0]["typography"]["stepCues"][0]["text"] == "工资完税单"
    assert labeled[0]["speaker"]["framing"] == "split"
    assert labeled[0]["background"] == {}
    props = resolve_scene_plan(
        visual_plan=decided,
        locale="zh-CN",
        duration_seconds=cursor,
        speaker_file="source-edit.mp4",
        generation_id="editorial_once",
    )
    rendered = [scene for scene in props["scenes"] if (scene.get("typography") or {}).get("steps")]
    assert rendered
    assert "工资完税单" in rendered[0]["typography"]["steps"]
    assert rendered[0].get("assetId") in (None, "")
    assert rendered[0]["start"] == pytest.approx(0.0, abs=0.05)
    assert rendered[0]["end"] == pytest.approx(cursor, abs=0.05)


def test_unknown_asset_is_rejected(tmp_path, monkeypatch):
    from backend.config import settings
    from backend.semantic_planner import plan_editorial_once

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")

    class _Plan:
        def model_dump(self):
            return {
                "transcript_version": 1,
                "language": "zh",
                "topic": "documents",
                "passages": [_passage(visual_treatment="supporting_broll", visual_concept="missing-plate", executed_treatment="supporting_broll")],
            }

    monkeypatch.setattr(
        "backend.providers.llm.OpenRouterLLMProvider.json_call",
        lambda *_args, **_kwargs: _Plan(),
    )
    with pytest.raises(PlannerError) as caught:
        plan_editorial_once(
            "pid",
            [{"id": "segment_001", "start": 0, "end": 2, "text": "包括工资完税单"}],
            "zh-CN",
            duration=2,
            media=[{"id": "icon_goal", "description": "A line icon."}],
        )
    assert caught.value.feedback == "asset_not_in_inventory"


def test_openrouter_without_words_fails_closed(tmp_path, monkeypatch):
    from backend.config import settings
    from backend.passage_retrieval import apply_semantic_beats
    from backend.semantic_planner import plan_path

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    path = plan_path("pid")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "planner": "openrouter",
        "language": "zh",
        "topic": "documents",
        "passages": [_passage()],
    }), encoding="utf-8")
    with pytest.raises(PlannerError) as caught:
        apply_semantic_beats(
            {"scenes": [{"sceneId": "hook", "start": 0, "end": 10}]},
            "pid",
            [{"id": "segment_001", "start": 0, "end": 2, "text": "包括工资完税单"}],
        )
    assert caught.value.feedback == "aligner_words_missing"


def test_legacy_mode_keeps_the_heuristic_plan(tmp_path, monkeypatch):
    from backend.config import settings
    from backend.passage_retrieval import apply_semantic_beats

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "llm_provider", "none")
    original = {"scenes": [{"sceneId": "hook", "start": 0, "end": 10}]}
    kept = apply_semantic_beats(
        original,
        "pid",
        [{"id": "segment_001", "start": 0, "end": 2, "text": "包括工资完税单"}],
    )
    assert kept["scenes"] == original["scenes"]


def test_word_times_survive_the_long60_grid(tmp_path, monkeypatch):
    from backend.config import settings
    from backend.director_evidence import apply_claim_check
    from backend.director_v3 import stamp_editorial_authority
    from backend.director_v8 import expand_plan_for_duration
    from backend.passage_retrieval import apply_semantic_beats
    from backend.remotion_engine import resolve_scene_plan
    from backend.semantic_planner import plan_path

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    speech = "前面先说背景包括工资完税单"
    words = []
    cursor = 0.0
    for char in speech:
        words.append({"text": char, "start": round(cursor, 3), "end": round(cursor + 0.5, 3)})
        cursor += 0.5
    path = plan_path("pid")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "planner": "openrouter",
        "model": "qwen/test",
        "planHash": "abc123",
        "transcript_version": 1,
        "language": "zh",
        "topic": "documents",
        "passages": [_passage()],
    }), encoding="utf-8")
    transcript = [{"id": "segment_001", "start": 0, "end": cursor, "text": speech, "words": words}]
    expanded = expand_plan_for_duration(
        {"scenes": [{"sceneId": "hook", "start": 0, "end": cursor}], "language": "zh"},
        duration_seconds=50,
        transcript=transcript,
        locale="zh-CN",
    )
    assert expanded.get("form") == "long60"
    planned = apply_semantic_beats(expanded, "pid", transcript)
    checked = apply_claim_check(planned, transcript)
    labeled = [scene for scene in checked["scenes"] if scene.get("steps")]
    assert labeled
    assert labeled[0]["start"] == pytest.approx(words[speech.index("包")]["start"], abs=0.05)
    assert labeled[0]["typography"]["stepCues"][0]["start"] == pytest.approx(words[speech.index("工")]["start"], abs=0.05)
    assert "工资完税单" in labeled[0]["steps"]
    assert checked["editorialAuthority"] == "openrouter"
    assert checked["form"] == "semantic"
    props = resolve_scene_plan(
        visual_plan=checked,
        locale="zh-CN",
        duration_seconds=cursor,
        speaker_file="source-edit.mp4",
        generation_id="locked",
    )
    stamped = stamp_editorial_authority(props, checked)
    assert stamped["editorialPlanHash"] == "abc123"
    assert stamped["editorialModel"] == "qwen/test"
    rendered = [scene for scene in stamped["scenes"] if (scene.get("typography") or {}).get("steps")]
    assert rendered[0]["start"] == pytest.approx(labeled[0]["start"], abs=0.05)
    assert "工资完税单" in rendered[0]["typography"]["steps"]
