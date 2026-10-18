"""V15 semantic motion — new diagrams only when the quote supports them."""
from __future__ import annotations

import json
from pathlib import Path

from backend.director_v14 import apply_semantic_motion
from backend.director_v15 import apply_semantic_motion_v15, classify_v15, enabled
from media.library.semantic_motion_registry import components, search_motion_components

ROOT = Path(__file__).resolve().parents[2]
TRANSCRIPT = json.loads((ROOT / "data/director_v5_original1/source.transcript.json").read_text(encoding="utf-8"))
V15_INTENTS = {
    "risk_matrix",
    "capital_allocation",
    "company_ecosystem",
    "document_workflow",
    "financial_metrics",
    "business_decision",
    "geographic_expansion",
    "investment_milestones",
    "contract_relationship",
    "before_after",
}


def _plan():
    return {
        "language": "en-US",
        "durationSeconds": 60,
        "beatWeights": [1] * 10,
        "scenes": [{"sceneId": f"s{i}", "speaker": {"layout": "speaker_fullscreen"}, "typography": {"cards": [{"title": "Control"}]}} for i in range(10)],
    }


def _intents(plan):
    return [row["visualIntent"] for row in plan.get("semanticMotionV15Usage") or []]


def test_flag_off_is_noop(monkeypatch):
    monkeypatch.delenv("SEMANTIC_MOTION_V15_ENABLED", raising=False)
    monkeypatch.delenv("SEMANTIC_MOTION_V14_ENABLED", raising=False)
    assert enabled() is False
    out = apply_semantic_motion_v15(_plan(), TRANSCRIPT, locale="en-US")
    assert out["semanticMotionV15Enabled"] is False
    assert "semanticMotionV14" not in out["scenes"][0]


def test_origin1_upgrades_documents_and_skips_unsupported(monkeypatch):
    monkeypatch.setenv("SEMANTIC_MOTION_V15_ENABLED", "1")
    monkeypatch.delenv("SEMANTIC_MOTION_V14_ENABLED", raising=False)
    out = apply_semantic_motion_v15(_plan(), TRANSCRIPT, locale="en-US")
    intents = set(_intents(out))
    assert "document_workflow" not in intents
    assert "process_timeline" not in intents
    assert "ownership_split" in intents
    assert "shareholder_network" in intents
    assert "business_comparison" in intents
    assert "capital_flow" in intents
    forbidden = V15_INTENTS
    assert intents.isdisjoint(forbidden)
    for scene in out["scenes"]:
        payload = scene.get("semanticMotionV14") or {}
        for value in payload.get("values") or []:
            assert value["value"] != 51
        assert "benefit" not in payload
        motion = scene.get("businessMotion") or {}
        assert motion.get("localRatio") != 51


def test_unspoken_local_ratio_is_removed(monkeypatch):
    monkeypatch.setenv("SEMANTIC_MOTION_V15_ENABLED", "1")
    plan = _plan()
    plan["scenes"][0]["businessMotion"] = {"localRatio": 51, "originalSourceText": "less than 49%"}
    out = apply_semantic_motion_v15(plan, TRANSCRIPT, locale="en-US")
    assert all((scene.get("businessMotion") or {}).get("localRatio") != 51 for scene in out["scenes"])


def test_chinese_layers_stay_a_timeline_not_documents():
    quote = "第一层叫使用场景 第二层叫家庭结构 第三层叫代价"
    found = classify_v15(quote, {"id": "layers", "start": 45.2, "end": 75.0}, locale="zh-CN")
    assert all(p["visualIntent"] != "document_workflow" for p in found)
    from backend.director_v14 import classify_quote
    from backend.director_v15 import _upgrade_documents

    timeline = next(p for p in classify_quote(quote, {"id": "layers", "start": 45.2, "end": 75.0}, locale="zh-CN") if p["visualIntent"] == "process_timeline")
    assert _upgrade_documents(timeline)["visualIntent"] == "process_timeline"
    assert _upgrade_documents(timeline)["componentId"] == "motion.process_timeline.v1"


def test_v14_alone_keeps_timeline(monkeypatch):
    monkeypatch.delenv("SEMANTIC_MOTION_V15_ENABLED", raising=False)
    monkeypatch.setenv("SEMANTIC_MOTION_V14_ENABLED", "1")
    out = apply_semantic_motion(_plan(), TRANSCRIPT, locale="en-US")
    intents = [row["visualIntent"] for row in out["semanticMotionV14Usage"]]
    assert "process_timeline" not in intents
    assert "document_workflow" not in intents


def test_risk_matrix_uses_spoken_labels_only():
    found = classify_v15("This is low risk and high risk.", {"id": "r", "start": 0, "end": 1}, locale="en-US")
    matrix = next(p for p in found if p["visualIntent"] == "risk_matrix")
    labels = [cell["label"] for cell in matrix["cells"]]
    assert labels == ["Low risk", "High risk"]
    assert "axisX" not in matrix
    bare = classify_v15("There is some risk.", {"id": "r2", "start": 0, "end": 1}, locale="en-US")
    assert all(p["visualIntent"] != "risk_matrix" for p in bare)


def test_allocation_does_not_invent_a_slice():
    found = classify_v15(
        "operations 40% and property 35% and reserves 25%",
        {"id": "a", "start": 0, "end": 1},
        locale="en-US",
    )
    alloc = next(p for p in found if p["visualIntent"] == "capital_allocation")
    assert [segment["value"] for segment in alloc["segments"]] == [40.0, 35.0, 25.0]
    assert len(alloc["segments"]) == 3


def test_geography_needs_an_expansion_verb():
    contrast = classify_v15(
        "China and Thailand processes are different",
        {"id": "g", "start": 0, "end": 1},
        locale="en-US",
    )
    assert all(p["visualIntent"] != "geographic_expansion" for p in contrast)
    moved = classify_v15(
        "We expanded from Thailand to Singapore",
        {"id": "g2", "start": 0, "end": 1},
        locale="en-US",
    )
    geo = next(p for p in moved if p["visualIntent"] == "geographic_expansion")
    assert geo["places"] == ["Thailand", "Singapore"]
    assert geo["directed"] is True


def test_metrics_and_contract_and_before_do_not_add_claims():
    money = classify_v15("Revenue was 120000 USD.", {"id": "m", "start": 0, "end": 1}, locale="ru-RU")
    metric = next(p for p in money if p["visualIntent"] == "financial_metrics")
    assert metric["metrics"][0]["value"] == 120000
    assert metric["metrics"][0]["unit"] == "USD"
    ratio = classify_v15("foreign capital ratio is less than 49%", {"id": "m2", "start": 0, "end": 1}, locale="en-US")
    assert all(p["visualIntent"] != "financial_metrics" for p in ratio)
    contract = classify_v15("The investor and the company signed a contract.", {"id": "c", "start": 0, "end": 1}, locale="en-US")
    parties = next(p for p in contract if p["visualIntent"] == "contract_relationship")["parties"]
    assert [party["id"] for party in parties] == ["investor", "company", "contract"]
    change = classify_v15("before restructuring and after restructuring", {"id": "b", "start": 0, "end": 1}, locale="en-US")
    state = next(p for p in change if p["visualIntent"] == "before_after")
    assert state["before"] == "restructuring"
    assert state["after"] == "restructuring"
    assert "benefit" not in state


def test_registry_has_fifteen_components():
    rows = components()
    assert len(rows) == 15
    assert V15_INTENTS <= {row["visualIntent"] for row in rows}
    assert search_motion_components("风险矩阵", locale="zh-CN")[0]["visualIntent"] == "risk_matrix"
    assert search_motion_components("матрица рисков", locale="ru-RU")[0]["visualIntent"] == "risk_matrix"
    assert search_motion_components("document workflow", locale="en-US")[0]["visualIntent"] == "document_workflow"
