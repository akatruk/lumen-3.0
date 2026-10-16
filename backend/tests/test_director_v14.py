"""V14 semantic motion — evidence gates and registry match."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.director_v14 import (
    _ordinal_labels,
    _steps_from_quote,
    adjacent_contrasts,
    apply_semantic_motion,
    audit_row,
    classify_quote,
    enabled,
    ordinal_timeline_payloads,
)
from backend.director_v15 import classify_v15
from backend.semantic_numeric_range import classify_numeric_range
from media.library.semantic_motion_registry import components, search_motion_components

ROOT = Path(__file__).resolve().parents[2]
TRANSCRIPT = json.loads((ROOT / "data/director_v5_original1/source.transcript.json").read_text(encoding="utf-8"))


def _plan():
    return {
        "language": "en-US",
        "durationSeconds": 60,
        "beatWeights": [1] * 10,
        "scenes": [{"sceneId": f"s{i}", "speaker": {"layout": "speaker_fullscreen"}, "typography": {"cards": [{"title": "Control"}]}} for i in range(10)],
    }


def test_flag_off_keeps_plan(monkeypatch):
    monkeypatch.delenv("SEMANTIC_MOTION_V14_ENABLED", raising=False)
    assert enabled() is False
    plan = _plan()
    out = apply_semantic_motion(plan, TRANSCRIPT, locale="en-US")
    assert out["semanticMotionV14Enabled"] is False
    assert "semanticMotionV14" not in out["scenes"][0]
    assert out["scenes"][0]["typography"]["cards"][0]["title"] == "Control"


def test_flag_on_selects_evidence_and_drops_text_cards(monkeypatch):
    monkeypatch.setenv("SEMANTIC_MOTION_V14_ENABLED", "1")
    out = apply_semantic_motion(_plan(), TRANSCRIPT, locale="en-US")
    assert out["semanticMotionV14Enabled"] is True
    intents = [row["visualIntent"] for row in out["semanticMotionV14Usage"]]
    assert "ownership_split" in intents
    assert "shareholder_network" in intents
    assert "capital_flow" in intents
    assert "business_comparison" in intents
    for scene in out["scenes"]:
        payload = scene.get("semanticMotionV14")
        if not payload:
            continue
        assert scene["typography"]["cards"] == []
        assert scene.get("businessMotion") is None
        ev = payload["evidence"]
        assert ev["factClass"] == "source_stated"
        assert ev["segmentId"]
        assert ev["sourceQuote"]


def test_forty_nine_does_not_invent_fifty_one():
    row = next(s for s in TRANSCRIPT if s["id"] == "seg_007")
    found = classify_quote(row["original"] + " " + row["en"], row, locale="en-US")
    split = next(p for p in found if p["visualIntent"] == "ownership_split")
    values = [v["value"] for v in split["values"]]
    assert values == [49.0] or values == [49]
    assert 51 not in values
    assert split["values"][0]["qualifier"] == "at_most"


def test_shareholder_count_requires_speech():
    bare = classify_quote("Company control is locked.", {"id": "x", "start": 0, "end": 1}, locale="en-US")
    assert all(p["visualIntent"] != "shareholder_network" or not p.get("showCount") for p in bare)
    row = next(s for s in TRANSCRIPT if s["id"] == "seg_006")
    found = classify_quote(row["en"] + " " + row["original"], row, locale="zh-CN")
    net = next(p for p in found if p["visualIntent"] == "shareholder_network")
    assert net["showCount"] is True
    assert net["nodeCount"] == 3
    assert net["countPrefix"] == "≥"


def test_comparison_needs_both_sides():
    one_side = classify_quote(
        "but the first step of a Chinese investment company is completely different",
        {"id": "seg_001", "start": 1, "end": 2},
        locale="en-US",
    )
    assert all(p["visualIntent"] != "business_comparison" for p in one_side)
    both = classify_quote(
        "差异很直白 中国注册公司看的是数字 泰国注册公司看的是结构",
        {"id": "seg_012", "start": 1, "end": 2},
        locale="zh-CN",
    )
    comp = next(p for p in both if p["visualIntent"] == "business_comparison")
    assert comp["operator"] == "≠"
    assert comp["left"] == "中国"
    assert comp["right"] == "泰国"


def test_timeline_uses_named_steps_only():
    invented = classify_quote("registration happens somehow", {"id": "n", "start": 0, "end": 1}, locale="en-US")
    assert all(p["visualIntent"] != "process_timeline" for p in invented)
    named = classify_quote(
        "Bank accounts, work permits and visa applications all watch capital",
        {"id": "seg_010", "start": 0, "end": 1},
        locale="en-US",
    )
    assert all(p["visualIntent"] != "process_timeline" for p in named)
    ordered = classify_quote(
        "Bank accounts, work permits and visa applications all watch capital. Step 1 is the account.",
        {"id": "seg_010b", "start": 0, "end": 1},
        locale="en-US",
    )
    timeline = next(p for p in ordered if p["visualIntent"] == "process_timeline")
    labels = [s["label"] for s in timeline["steps"]]
    assert labels[0].startswith("Bank")
    assert len(labels) == 3


def test_chinese_ordinal_layers_keep_source_labels():
    quote = "我建议先做三个筛选 第一层叫使用场景 未来五年 第二层叫家庭结构 今天适合三口之家的方案 第三层叫代价 这里不只是申请费"
    labels = _steps_from_quote(quote, "zh")
    assert labels == ["使用场景", "家庭结构", "代价"]
    found = classify_quote(quote, {"id": "s05", "start": 42.8, "end": 75.0}, locale="zh-CN")
    timeline = next(p for p in found if p["visualIntent"] == "process_timeline")
    assert timeline["componentId"] == "motion.process_timeline.v1"
    assert [step["label"] for step in timeline["steps"]] == ["使用场景", "家庭结构", "代价"]
    assert "银行开户" not in [step["label"] for step in timeline["steps"]]
    english_locale = classify_quote(quote, {"id": "s05", "start": 42.8, "end": 75.0}, locale="en-US")
    assert [step["label"] for step in next(p for p in english_locale if p["visualIntent"] == "process_timeline")["steps"]] == labels


def test_unseen_chinese_ordinal_labels_and_later_sentence():
    inline = "第一层叫市场准入 第二层叫税务居民 第三层叫退出路径"
    assert _steps_from_quote(inline, "zh") == ["市场准入", "税务居民", "退出路径"]
    later = "第一层。市场准入。第二层。税务居民。第三层。退出路径。"
    assert _steps_from_quote(later, "zh") == ["市场准入", "税务居民", "退出路径"]
    arabic = "第1步：开户 第2步：核对 第3步：归档"
    assert _steps_from_quote(arabic, "zh") == ["开户", "核对", "归档"]


def test_missing_out_of_order_and_repeated_ordinals():
    missing = "第一层叫使用场景 第三层叫代价"
    assert _ordinal_labels(missing) == [
        {"ordinal": 1, "label": "使用场景", "clause": "第一层叫使用场景"},
        {"ordinal": 3, "label": "代价", "clause": "第三层叫代价"},
    ]
    assert _steps_from_quote(missing, "zh") is None
    assert all(p["visualIntent"] != "process_timeline" for p in classify_quote(missing, {"id": "m", "start": 0, "end": 1}, locale="zh-CN"))
    ordered = _steps_from_quote("第三层叫代价 第一层叫使用场景 第二层叫家庭结构", "zh")
    assert ordered == ["使用场景", "家庭结构", "代价"]
    repeated = _steps_from_quote("第一层叫使用场景 第一层叫别的名称 第二层叫家庭结构 第三层叫代价", "zh")
    assert repeated == ["使用场景", "家庭结构", "代价"]


def test_non_process_chinese_does_not_invent_steps():
    for text in (
        "今天适合三口之家的方案",
        "三个问题都先放下",
        "第一层楼很高，第二层楼更贵，第三层楼空着",
        "身份规划的第一步 不是选国家 而是定义问题",
    ):
        assert _steps_from_quote(text, "zh") is None
        assert all(
            p["visualIntent"] != "process_timeline"
            for p in classify_quote(text, {"id": "n", "start": 0, "end": 1}, locale="zh-CN")
        )


def test_shareholder_word_alone_is_not_ownership():
    found = classify_quote("股东", {"id": "sh", "start": 0, "end": 1}, locale="zh-CN")
    assert all(p["visualIntent"] not in {"ownership_split", "shareholder_network", "process_timeline"} for p in found)


def test_existing_english_and_russian_process_lists():
    unordered = (
        ("Bank accounts, work permits and visa applications all watch capital", "en-US"),
        ("Банковские счета, разрешения на работу и визовые заявления следят за капиталом", "ru-RU"),
        ("银行开户、工作证、签证申请都会盯着资金到位情况", "zh-CN"),
    )
    for quote, locale in unordered:
        found = classify_quote(quote, {"id": "list", "start": 0, "end": 1}, locale=locale)
        assert all(p["visualIntent"] != "process_timeline" for p in found), quote
    en = classify_quote(
        "Bank accounts, work permits and visa applications all watch capital. Step 1 is the account.",
        {"id": "en", "start": 0, "end": 1},
        locale="en-US",
    )
    en_labels = [step["label"] for step in next(p for p in en if p["visualIntent"] == "process_timeline")["steps"]]
    assert en_labels[0].startswith("Bank")
    assert len(en_labels) == 3
    ru = classify_quote(
        "Банковские счета, разрешения на работу и визовые заявления следят за капиталом. Шаг 1 это счёт.",
        {"id": "ru", "start": 0, "end": 1},
        locale="ru-RU",
    )
    ru_labels = [step["label"] for step in next(p for p in ru if p["visualIntent"] == "process_timeline")["steps"]]
    assert ru_labels == ["Банковские счета", "разрешения на работу", "визовые заявления"]


def test_ordinal_cluster_keeps_speech_times(monkeypatch):
    monkeypatch.setenv("SEMANTIC_MOTION_V14_ENABLED", "1")
    rows = [
        {"id": "a", "start": 42.8, "end": 45.2, "text": "我建议先做三个筛选"},
        {"id": "b", "start": 45.2, "end": 47.4, "text": "第一层叫使用场景"},
        {"id": "c", "start": 59.32, "end": 61.56, "text": "第二层叫家庭结构"},
        {"id": "d", "start": 67.72, "end": 70.12, "text": "今天适合三口之家的方案"},
        {"id": "e", "start": 73.24, "end": 75.0, "text": "第三层叫代价"},
    ]
    plan = {
        "language": "zh-CN",
        "durationSeconds": 75,
        "beatWeights": [1],
        "scenes": [{"sceneId": "layers", "speaker": {"layout": "speaker_fullscreen"}, "typography": {"cards": [{"title": "x"}]}}],
    }
    out = apply_semantic_motion(plan, rows, locale="zh-CN")
    payload = next(scene["semanticMotionV14"] for scene in out["scenes"] if scene.get("semanticMotionV14"))
    assert payload["componentId"] == "motion.process_timeline.v1"
    assert [step["label"] for step in payload["steps"]] == ["使用场景", "家庭结构", "代价"]
    assert [step["at"] for step in payload["steps"]] == [2.4, 16.52, 30.44]


def test_registry_matches_three_locales():
    rows = components()
    assert len(rows) >= 5
    intents = {row["visualIntent"] for row in rows}
    assert {"capital_flow", "shareholder_network", "business_comparison", "ownership_split", "process_timeline"} <= intents
    for row in rows:
        assert row["supportedLocales"] == ["ru-RU", "en-US", "zh-CN"]
        assert row["supportedLayouts"] == ["full_frame", "speaker_visual", "overlay"]
        assert row["qualityStatus"] == "production_ready"
    assert search_motion_components("поток капитала", locale="ru-RU")[0]["visualIntent"] == "capital_flow"
    assert search_motion_components("股东结构", locale="zh-CN")[0]["visualIntent"] == "shareholder_network"
    assert search_motion_components("ownership percentage", locale="en-US")[0]["visualIntent"] == "ownership_split"


def test_not_but_contrast_is_not_a_shareholder_chart():
    row = next(s for s in TRANSCRIPT if s["id"] == "seg_005")
    found = classify_quote(row["original"], row, locale="zh-CN")
    assert [item["visualIntent"] for item in found] == ["business_comparison"]
    comp = found[0]
    assert comp["left"] == "钱"
    assert comp["right"] == "股东结构"
    assert comp["contrast"] == "不是而是"
    assert comp["evidence"]["sourceQuote"] == row["original"]
    assert comp["evidence"]["sourceTimestamp"] == [row["start"], row["end"]]


def test_control_versus_amount_uses_the_spoken_sides():
    row = next(s for s in TRANSCRIPT if s["id"] == "seg_008")
    found = classify_quote(row["original"], row, locale="zh-CN")
    assert [item["visualIntent"] for item in found] == ["business_comparison"]
    assert found[0]["left"] == "控制权"
    assert found[0]["right"] == "金额"
    assert found[0]["contrast"] == "锁定反而"
    assert found[0]["evidence"]["sourceTimestamp"] == [29.26, 34.46]


def test_timing_comparison_does_not_add_capital_flow():
    row = next(s for s in TRANSCRIPT if s["id"] == "seg_009")
    found = classify_quote(row["original"], row, locale="zh-CN")
    assert [item["visualIntent"] for item in found] == ["business_comparison"]
    assert found[0]["left"] == "中国"
    assert found[0]["right"] == "泰国"
    capital = next(s for s in TRANSCRIPT if s["id"] == "seg_002")
    assert [item["visualIntent"] for item in classify_quote(capital["original"], capital, locale="zh-CN")] == ["capital_flow"]


def test_split_not_but_keeps_each_side_from_its_line():
    rows = json.loads((ROOT / "data/original3/asr.json").read_text(encoding="utf-8"))["segments"]
    indexed = []
    for index, row in enumerate(rows):
        indexed.append({**row, "id": f"seg_{index:03d}", "original": row["text"]})
    events = adjacent_contrasts(indexed, locale="zh-CN")
    pairs = [(event["left"], event["right"], event["evidence"]["sourceTimestamp"]) for event in events]
    assert ("选国家", "定义问题", [11.4, 14.24]) in pairs
    assert ("多一本证件", "在关键时候多一种合法选择", [136.04, 141.0]) in pairs
    for event in events:
        quote = event["evidence"]["sourceQuote"]
        assert event["left"] in quote and event["right"] in quote
        assert event["visualIntent"] == "business_comparison"
    alone = classify_quote("不是选国家", {"id": "seg_007", "start": 11.4, "end": 12.76}, locale="zh-CN")
    assert alone == []


def test_split_layers_need_the_ordinal_cluster():
    rows = json.loads((ROOT / "data/original3/asr.json").read_text(encoding="utf-8"))["segments"]
    indexed = []
    for index, row in enumerate(rows):
        indexed.append({**row, "id": f"seg_{index:03d}", "original": row["text"]})
    layer_ids = {"seg_024", "seg_033", "seg_040"}
    for row in indexed:
        if row["id"] not in layer_ids:
            continue
        found = classify_quote(row["original"], row, locale="zh-CN")
        assert all(item["visualIntent"] != "process_timeline" for item in found)
    events = ordinal_timeline_payloads(indexed, locale="zh-CN")
    assert len(events) == 1
    _cluster, payload = events[0]
    assert [step["label"] for step in payload["steps"]] == ["使用场景", "家庭结构", "代价"]
    assert set(layer_ids) <= set(payload["evidence"]["segmentIds"])
    labels = [step["label"] for step in payload["steps"]]
    assert labels.count("三口之家") == 0
    assert "会不会工作" not in labels
    assert "申请费" not in labels


def test_lists_family_counts_and_year_spans_are_not_workflows():
    samples = [
        "申请费、资金占用、续签保险、住房",
        "苹果、香蕉、橙子",
        "今天适合三口之家的方案",
        "会不会工作 开公司 送孩子上学",
        "这里不只是申请费 还包括资金占用税务申报 续签保险 住房",
        "要从家庭未来五到十年的生活出发",
        "第一申请费 第二资金占用 第三续签保险",
        "三个问题都先放下",
    ]
    for text in samples:
        segment = {"id": "neg", "start": 0, "end": 1}
        found = classify_quote(text, segment, locale="zh-CN") + classify_v15(text, segment, locale="zh-CN")
        assert all(
            item["visualIntent"] not in {"process_timeline", "document_workflow", "investment_milestones"}
            for item in found
        )
        assert classify_numeric_range(text, segment, locale="zh-CN") is None
        assert _steps_from_quote(text, "zh") is None


def _comparisons(plan):
    found = []
    for scene in plan["scenes"]:
        payload = scene.get("semanticMotionV14") or {}
        if payload.get("visualIntent") == "business_comparison":
            found.append(payload)
    return found


def test_repeated_comparisons_stay_distinct(monkeypatch):
    monkeypatch.setenv("SEMANTIC_MOTION_V14_ENABLED", "1")
    out = apply_semantic_motion(_plan(), TRANSCRIPT, locale="zh-CN")
    pairs = {
        (item["left"], item["right"], (item.get("evidence") or {}).get("segmentId"))
        for item in _comparisons(out)
    }
    assert ("钱", "股东结构", "seg_005") in pairs
    assert ("控制权", "金额", "seg_008") in pairs
    assert ("中国", "泰国", "seg_009") in pairs
    assert ("法人代表", "董事权限", "seg_011") in pairs
    assert ("中国", "泰国", "seg_012") in pairs
    accepted = [row for row in out["semanticEventAudit"] if row["status"] == "accepted" and row["visualIntent"] == "business_comparison"]
    assert len(accepted) >= 5
    for row in accepted:
        assert row["componentId"]
        assert row["outputTime"][1] > row["outputTime"][0]
        assert row["sceneId"]
        assert row["flags"] == []
        assert row["sourceQuote"]
        assert row["segmentIds"]


def test_duplicate_thought_is_merged(monkeypatch):
    monkeypatch.setenv("SEMANTIC_MOTION_V14_ENABLED", "1")
    row = next(item for item in TRANSCRIPT if item["id"] == "seg_005")
    out = apply_semantic_motion(_plan(), [row, dict(row)], locale="zh-CN")
    assert len(_comparisons(out)) == 1
    merged = [item for item in out["semanticEventAudit"] if item["status"] == "merged"]
    assert merged
    assert merged[0]["reason"] == "duplicate_thought"
    assert merged[0]["mergedInto"] == _comparisons(out)[0]["eventId"]
    assert merged[0]["sceneId"]


def test_scene_boundary_keeps_both_events(monkeypatch):
    monkeypatch.setenv("SEMANTIC_MOTION_V14_ENABLED", "1")
    rows = [
        {"id": "seg_a", "start": 0.4, "end": 3.2, "original": "不是钱而是股东结构"},
        {"id": "seg_b", "start": 4.6, "end": 7.4, "original": "不是控制权而是金额"},
    ]
    plan = {
        "language": "zh-CN",
        "durationSeconds": 10,
        "beatWeights": [1, 1],
        "scenes": [
            {"sceneId": "left", "speaker": {"layout": "speaker_fullscreen"}},
            {"sceneId": "right", "speaker": {"layout": "speaker_fullscreen"}},
        ],
    }
    out = apply_semantic_motion(plan, rows, locale="zh-CN")
    comps = _comparisons(out)
    assert len(comps) == 2
    straddling = next(item for item in comps if item["evidence"]["segmentId"] == "seg_b")
    assert straddling["outputTime"][0] == pytest.approx(4.6, abs=0.05)
    assert straddling["outputTime"][1] == pytest.approx(7.4, abs=0.05)
    assert straddling["left"] == "控制权"
    assert straddling["right"] == "金额"


def test_timeline_keeps_source_time_when_the_render_is_shorter(monkeypatch):
    monkeypatch.setenv("SEMANTIC_MOTION_V14_ENABLED", "1")
    rows = [
        {"id": "early", "start": 10.0, "end": 16.0, "original": "不是钱而是股东结构"},
        {"id": "late", "start": 50.0, "end": 58.0, "original": "不是选国家 而是定义问题"},
        {"id": "pad", "start": 58.0, "end": 60.0, "original": "结束"},
    ]
    plan = {
        "language": "zh-CN",
        "durationSeconds": 30,
        "beatWeights": [1, 1, 1, 1],
        "scenes": [{"sceneId": f"s{i}", "speaker": {"layout": "speaker_fullscreen"}} for i in range(4)],
    }
    out = apply_semantic_motion(plan, rows, locale="zh-CN")
    kept = _comparisons(out)
    assert len(kept) == 1
    assert kept[0]["evidence"]["segmentId"] == "early"
    assert kept[0]["outputTime"] == pytest.approx([10.0, 16.0], abs=0.05)
    rejected = [row for row in out["semanticEventAudit"] if row["status"] == "rejected"]
    assert any(row["reason"] == "trimmed_past_output" and row["segmentIds"] == ["late"] for row in rejected)


def test_original3_joins_reach_the_render_plan(monkeypatch):
    monkeypatch.setenv("SEMANTIC_MOTION_V14_ENABLED", "1")
    rows = json.loads((ROOT / "data/original3/asr.json").read_text(encoding="utf-8"))["segments"]
    indexed = [{**row, "id": f"seg_{index:03d}", "original": row["text"]} for index, row in enumerate(rows)]
    plan = {
        "language": "zh-CN",
        "durationSeconds": 150,
        "beatWeights": [1] * 10,
        "scenes": [{"sceneId": f"s{i}", "speaker": {"layout": "speaker_fullscreen"}} for i in range(10)],
    }
    out = apply_semantic_motion(plan, indexed, locale="zh-CN")
    comps = _comparisons(out)
    pairs = {(item["left"], item["right"]) for item in comps}
    assert ("选国家", "定义问题") in pairs
    assert ("多一本证件", "在关键时候多一种合法选择") in pairs
    timeline = next(
        scene["semanticMotionV14"]
        for scene in out["scenes"]
        if (scene.get("semanticMotionV14") or {}).get("visualIntent") == "process_timeline"
    )
    assert [step["label"] for step in timeline["steps"]] == ["使用场景", "家庭结构", "代价"]
    assert timeline["outputTime"][0] == pytest.approx(42.8, abs=0.05)
    assert timeline["outputTime"][1] == pytest.approx(76.2, abs=0.05)
    assert timeline["evidence"]["sourceTimestamp"] == pytest.approx([42.8, 75.0], abs=0.05)
    assert timeline["layout"] == "speaker_visual"
    origin = timeline["evidence"]["sourceTimestamp"][0]
    spoken = {"使用场景": 45.2, "家庭结构": 59.32, "代价": 73.24}
    for step in timeline["steps"]:
        assert origin + step["at"] == pytest.approx(spoken[step["label"]], abs=0.05)
    assert timeline["timebase"]["sourceOrigin"] == pytest.approx(origin, abs=0.05)
    assert timeline["timebase"]["sceneStart"] == pytest.approx(timeline["outputTime"][0], abs=0.05)
    country = next(item for item in comps if item["left"] == "选国家")
    document = next(item for item in comps if item["left"] == "多一本证件")
    assert country["outputTime"] == pytest.approx([11.4, 14.24], abs=0.05)
    assert country["evidence"]["sourceTimestamp"] == pytest.approx([11.4, 14.24], abs=0.05)
    assert country["layout"] == "speaker_visual"
    assert document["outputTime"] == pytest.approx([136.04, 141.0], abs=0.05)
    assert document["evidence"]["sourceTimestamp"] == pytest.approx([136.04, 141.0], abs=0.05)
    cursor = 0.0
    for scene, weight in zip(out["scenes"], out["beatWeights"]):
        span = (cursor, cursor + weight)
        cursor += weight
        payload = scene.get("semanticMotionV14") or {}
        if span[1] <= 11.35 or (14.3 <= span[0] and span[1] <= 42.75) or (76.3 <= span[0] and span[1] <= 136.0):
            assert not payload.get("componentId")
    accepted = [row for row in out["semanticEventAudit"] if row["status"] == "accepted"]
    assert accepted
    assert all(row["flags"] == [] for row in accepted)
    assert all(row["componentId"] and row["outputTime"] and row["sceneId"] for row in accepted)


def test_accepted_without_picture_is_flagged():
    row = audit_row(
        {"eventId": "evt_missing", "visualIntent": "business_comparison", "evidence": {"sourceQuote": "不是钱而是股东结构"}},
        status="accepted",
    )
    assert "accepted_without_component" in row["flags"]
    assert "accepted_without_time_window" in row["flags"]


def test_no_complement_on_plan(monkeypatch):
    monkeypatch.setenv("SEMANTIC_MOTION_V14_ENABLED", "1")
    out = apply_semantic_motion(_plan(), TRANSCRIPT, locale="ru-RU")
    for scene in out["scenes"]:
        payload = scene.get("semanticMotionV14") or {}
        for value in payload.get("values") or []:
            assert value["value"] != 51
