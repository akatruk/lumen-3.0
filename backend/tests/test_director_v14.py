"""V14 semantic motion — evidence gates and registry match."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.director_v14 import apply_semantic_motion, classify_quote, enabled
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
    timeline = next(p for p in named if p["visualIntent"] == "process_timeline")
    labels = [s["label"] for s in timeline["steps"]]
    assert labels[0].startswith("Bank")
    assert len(labels) == 3


def test_registry_matches_three_locales():
    rows = components()
    assert len(rows) == 5
    for row in rows:
        assert row["supportedLocales"] == ["ru-RU", "en-US", "zh-CN"]
        assert row["supportedLayouts"] == ["full_frame", "speaker_visual", "overlay"]
        assert row["qualityStatus"] == "production_ready"
    assert search_motion_components("поток капитала", locale="ru-RU")[0]["visualIntent"] == "capital_flow"
    assert search_motion_components("股东结构", locale="zh-CN")[0]["visualIntent"] == "shareholder_network"
    assert search_motion_components("ownership percentage", locale="en-US")[0]["visualIntent"] == "ownership_split"


def test_no_complement_on_plan(monkeypatch):
    monkeypatch.setenv("SEMANTIC_MOTION_V14_ENABLED", "1")
    out = apply_semantic_motion(_plan(), TRANSCRIPT, locale="ru-RU")
    for scene in out["scenes"]:
        payload = scene.get("semanticMotionV14") or {}
        for value in payload.get("values") or []:
            assert value["value"] != 51
