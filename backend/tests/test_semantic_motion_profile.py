"""Evidence-gated motion through the same functions the Create Video job calls."""
import json

from backend.director_v14 import classify_quote
from backend.semantic_motion_profile import PROFILE, apply_profile
from backend.semantic_numeric_range import apply_numeric_range, classify_numeric_range
from backend.tests.test_studio import client, create


def _plan(duration=60, count=2):
    return {
        "language": "zh-CN",
        "durationSeconds": duration,
        "beatWeights": [1] * count,
        "scenes": [
            {"sceneId": f"s{i}", "speaker": {"layout": "speaker_fullscreen"}}
            for i in range(count)
        ],
    }


def test_profile_selects_range_without_the_global_flag(monkeypatch):
    monkeypatch.delenv("SEMANTIC_NUMERIC_RANGE_ENABLED", raising=False)
    monkeypatch.delenv("SEMANTIC_MOTION_V14_ENABLED", raising=False)
    rows = [{
        "id": "day",
        "start": 0.0,
        "end": 4.0,
        "original": "那大概在400-1200人民币每天",
    }]
    off = apply_numeric_range(_plan(8), rows, locale="zh-CN")
    assert off["semanticNumericRangeEnabled"] is False
    on = apply_profile(_plan(8), rows, locale="zh-CN")
    assert on["semanticMotionProfile"] == PROFILE
    ranges = [
        scene["semanticMotionV14"]
        for scene in on["scenes"]
        if (scene.get("semanticMotionV14") or {}).get("visualIntent") == "numeric_range"
    ]
    assert len(ranges) == 1
    assert ranges[0]["range"]["lowText"] == "400"
    assert ranges[0]["range"]["highText"] == "1200"
    assert ranges[0]["range"]["unit"] == "人民币"
    assert ranges[0]["range"]["period"] == "day"
    assert ranges[0]["lifecycle"]["source_segment_ids"] == ["day"]
    assert ranges[0]["lifecycle"]["display_end"] <= 4.35


def test_minimum_count_is_not_a_range_and_layers_keep_their_names(monkeypatch):
    monkeypatch.delenv("SEMANTIC_NUMERIC_RANGE_ENABLED", raising=False)
    monkeypatch.delenv("SEMANTIC_MOTION_V14_ENABLED", raising=False)
    assert classify_numeric_range("普通泰国有限公司通常需要至少三名股东", {"id": "n", "start": 0, "end": 1}, locale="zh-CN") is None
    rows = [
        {"id": "a", "start": 0.0, "end": 2.0, "original": "第一层叫使用场景"},
        {"id": "b", "start": 3.0, "end": 5.0, "original": "第二层叫家庭结构"},
        {"id": "c", "start": 6.0, "end": 8.0, "original": "第三层叫代价"},
    ]
    out = apply_profile(_plan(10), rows, locale="zh-CN")
    timelines = [
        scene["semanticMotionV14"]
        for scene in out["scenes"]
        if (scene.get("semanticMotionV14") or {}).get("visualIntent") == "process_timeline"
    ]
    assert len(timelines) == 1
    assert [step["label"] for step in timelines[0]["steps"]] == ["使用场景", "家庭结构", "代价"]
    assert all(not str(step["label"]).startswith("步骤") for step in timelines[0]["steps"])


def test_studio_captions_without_ids_still_keep_the_timeline(monkeypatch):
    monkeypatch.delenv("SEMANTIC_MOTION_V14_ENABLED", raising=False)
    rows = [
        {"start": 0.0, "end": 2.0, "original": "第一层叫使用场景", "zh": "第一层叫使用场景"},
        {"start": 3.0, "end": 5.0, "original": "第二层叫家庭结构", "zh": "第二层叫家庭结构"},
        {"start": 6.0, "end": 8.0, "original": "第三层叫代价", "zh": "第三层叫代价"},
    ]
    out = apply_profile(_plan(10), rows, locale="zh-CN")
    graphic = next(
        scene["semanticMotionV14"]
        for scene in out["scenes"]
        if (scene.get("semanticMotionV14") or {}).get("visualIntent") == "process_timeline"
    )
    assert graphic["lifecycle"]["source_segment_ids"] == ["segment_001", "segment_002", "segment_003"]
    assert [step["label"] for step in graphic["steps"]] == ["使用场景", "家庭结构", "代价"]


def test_unverified_unit_is_omitted_and_a_forged_currency_is_rejected(monkeypatch):
    monkeypatch.delenv("SEMANTIC_NUMERIC_RANGE_ENABLED", raising=False)
    rows = [{
        "id": "pay",
        "start": 1.0,
        "end": 5.0,
        "original": "月薪差不多在1.5-2.5万泰国左右吧",
    }]
    out = apply_profile(_plan(8), rows, locale="zh-CN")
    graphic = next(scene["semanticMotionV14"] for scene in out["scenes"] if scene.get("semanticMotionV14"))
    assert graphic["range"]["lowText"] == "1.5万"
    assert graphic["range"]["highText"] == "2.5万"
    assert graphic["range"]["unit"] == ""
    assert graphic["unitOmitted"] == "asr_unit_unverified"
    assert "泰铢" not in json.dumps(graphic, ensure_ascii=False)
    forged = json.loads(json.dumps(graphic))
    forged["range"]["unit"] = "泰铢"
    forged["range"]["currency"] = "泰铢"
    from backend.semantic_motion_profile import bind_graphic_lifecycle
    plan = _plan(8)
    plan["scenes"][0]["semanticMotionV14"] = forged
    dropped = bind_graphic_lifecycle(plan, rows)
    assert "semanticMotionV14" not in dropped["scenes"][0]
    assert dropped["semanticMotionRejections"][0]["reason"] == "ungrounded_range"


def test_previous_contrast_ends_when_its_sentence_ends(monkeypatch):
    monkeypatch.delenv("SEMANTIC_MOTION_V14_ENABLED", raising=False)
    rows = [
        {
            "id": "capital",
            "start": 0.0,
            "end": 6.0,
            "original": "再看出资节奏 中国认缴时间弹性很大 泰国则要求实缴部分资本",
        },
        {
            "id": "roles",
            "start": 12.0,
            "end": 20.0,
            "original": "管理逻辑也不同 中国强调法人代表 泰国更看重的是董事权限 很多法律文件只认董事签字不看公章",
        },
    ]
    out = apply_profile(_plan(22), rows, locale="zh-CN")
    comparisons = [
        (scene["semanticMotionV14"]["left"], scene["semanticMotionV14"]["right"], scene["semanticMotionV14"]["lifecycle"])
        for scene in out["scenes"]
        if (scene.get("semanticMotionV14") or {}).get("visualIntent") == "business_comparison"
    ]
    assert ("中国", "泰国") in {(left, right) for left, right, _life in comparisons}
    assert ("法人代表", "董事权限") in {(left, right) for left, right, _life in comparisons}
    country = next(life for left, right, life in comparisons if (left, right) == ("中国", "泰国"))
    assert country["display_end"] <= 6.35
    assert country["evidence_end"] == 6.0
    for scene in out["scenes"]:
        life = (scene.get("semanticMotionV14") or {}).get("lifecycle") or {}
        if life.get("display_start", 0) >= 12:
            titles = [card.get("title") for card in scene.get("criteriaCards") or []]
            assert titles != ["中国", "泰国"]


def test_a_stale_display_interval_is_rejected():
    from backend.semantic_motion_profile import bind_graphic_lifecycle
    plan = _plan(20, 1)
    plan["scenes"][0]["semanticMotionV14"] = {
        "componentId": "motion.business_comparison.v1",
        "visualIntent": "business_comparison",
        "left": "中国",
        "right": "泰国",
        "outputTime": [0, 20],
        "evidence": {
            "segmentId": "capital",
            "sourceTimestamp": [0, 6],
            "sourceQuote": "中国和泰国",
        },
    }
    out = bind_graphic_lifecycle(plan, [{"id": "capital", "start": 0, "end": 6, "original": "中国和泰国"}])
    assert "semanticMotionV14" not in out["scenes"][0]
    assert out["semanticMotionRejections"][0]["reason"] == "stale_after_evidence"


def test_unordered_and_foreign_lines_do_not_become_a_chinese_timeline():
    samples = [
        ("zh-CN", "是出行受限 是孩子未来教育 是退休居住"),
        ("ru-RU", "Мы сопровождаем весь процесс: от консультации до документов и заявления."),
        ("en-US", "Bank accounts and visas are different topics, not three numbered layers."),
    ]
    for locale, text in samples:
        found = classify_quote(text, {"id": "x", "start": 0, "end": 2, "original": text}, locale=locale)
        assert all(item["visualIntent"] != "process_timeline" for item in found)


def test_profile_persists_on_the_project_and_rejects_an_unknown_name(client):
    pid = create(client).json()["id"]
    saved = client.put(
        f"/api/studio/projects/{pid}/editing-controls",
        json={
            "animation_percent": 60,
            "intensity_percent": 60,
            "motion_percent": 80,
            "density_percent": 70,
            "visual_energy": "balanced",
            "semantic_motion_profile": PROFILE,
        },
    )
    assert saved.status_code == 200, saved.text
    state = client.get(f"/api/studio/projects/{pid}").json()
    assert state["context"]["semantic_motion_profile"] == PROFILE
    refused = client.put(
        f"/api/studio/projects/{pid}/editing-controls",
        json={
            "animation_percent": 60,
            "intensity_percent": 60,
            "motion_percent": 80,
            "density_percent": 70,
            "visual_energy": "balanced",
            "semantic_motion_profile": "enable_everything",
        },
    )
    assert refused.status_code == 422
    assert client.get(f"/api/studio/projects/{pid}").json()["context"]["semantic_motion_profile"] == PROFILE
