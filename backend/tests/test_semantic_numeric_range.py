"""Salary bands stay out of revenue metrics and ownership diagrams."""
from __future__ import annotations

import json
from pathlib import Path

from backend.director_v14 import classify_quote
from backend.director_v15 import classify_v15
from backend.motion_design_v18 import supports_equity
from backend.semantic_numeric_range import (
    apply_numeric_range,
    classify_numeric_range,
    enabled,
    lexicon_senses,
    normalized_grounded,
    parameters_grounded,
)

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL2 = json.loads((ROOT / "data/original2/source.transcript.json").read_text(encoding="utf-8"))
WORDS = ["月薪", "工资", "收入", "投资", "资本", "金额", "比例", "股东", "股权", "公司"]


def _hits(text: str) -> list[str]:
    segment = {"id": "lex", "start": 0, "end": 1}
    v14 = classify_quote(text, segment, locale="zh-CN")
    v15 = classify_v15(text, segment, locale="zh-CN")
    return [row["visualIntent"] for row in v14 + v15]


def test_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("SEMANTIC_NUMERIC_RANGE_ENABLED", raising=False)
    assert enabled() is False


def test_lexicon_does_not_collapse_into_revenue_or_ownership():
    expect = {
        "月薪": ["salary"],
        "工资": ["salary"],
        "收入": ["income"],
        "投资": ["investment"],
        "资本": ["capital"],
        "金额": ["amount"],
        "比例": ["ratio"],
        "股东": ["ownership"],
        "股权": ["ownership"],
        "公司": ["company"],
    }
    for word in WORDS:
        assert lexicon_senses(word) == expect[word]
        intents = _hits(word)
        assert "financial_metrics" not in intents
        assert "ownership_split" not in intents
        assert "shareholder_network" not in intents
    assert _hits("投资") == ["capital_flow"]
    assert _hits("资本") == []
    assert _hits("注册资本") == ["capital_flow"]
    assert _hits("营收 120000 元") == ["financial_metrics"]
    assert supports_equity("股东") is True
    assert supports_equity("股权") is True
    assert supports_equity("公司") is False
    assert supports_equity("月薪") is False
    assert supports_equity("泰国") is False
    assert supports_equity("资本") is False


def test_original2_ranges_keep_asr_tokens():
    spoken = {
        "seg_006": ("1.5万", "2.5万", "泰国", "salary"),
        "seg_007": ("3千", "4千", "人民币", "money"),
        "seg_010": ("2.5万", "3.5万", "泰诸", "salary"),
            "seg_011": ("4万", "5万", "泰诸", "money"),
        "seg_012": ("8000", "1万", "人民币", "money"),
        "seg_016": ("400", "1200", "人民币", "day_rate"),
    }
    for row in ORIGINAL2:
        quote = row["original"]
        assert classify_quote(quote, row, locale="zh-CN") == []
        assert classify_v15(quote, row, locale="zh-CN") == []
        payload = classify_numeric_range(quote, row, locale="zh-CN")
        expect = spoken.get(row["id"])
        if expect is None:
            assert payload is None
            continue
        low, high, unit, kind = expect
        assert payload["range"]["lowText"] == low
        assert payload["range"]["highText"] == high
        assert payload["range"]["unit"] == unit
        assert payload["range"]["kind"] == kind
        assert parameters_grounded(payload)
        blob = json.dumps(payload, ensure_ascii=False)
        assert "泰铢" not in blob
        assert "49" not in blob
        if row["id"] == "seg_006":
            assert payload["range"]["low"] == 15000
            assert payload["range"]["high"] == 25000
            assert "15000" not in quote
            assert payload["range"]["period"] == "month"
            assert "currency" not in payload["range"]
        if row["id"] == "seg_007":
            assert payload["range"]["low"] == 3000
            assert payload["range"]["high"] == 4000
            assert "3000" not in quote
            assert "3千" not in quote
            assert payload["range"]["currency"] == "人民币"
            assert "period" not in payload["range"]
        if row["id"] == "seg_012":
            assert payload["range"]["low"] == 8000
            assert payload["range"]["high"] == 10000
            assert "10000" not in quote
            assert payload["range"]["currency"] == "人民币"
        if row["id"] == "seg_010":
            assert payload["range"]["unit"] == "泰诸"
            assert "currency" not in payload["range"]
            assert payload["range"]["low"] == 25000
            assert payload["range"]["high"] == 35000


def test_apply_stays_off_and_does_not_invent_equity(monkeypatch):
    monkeypatch.delenv("SEMANTIC_NUMERIC_RANGE_ENABLED", raising=False)
    plan = {
        "language": "zh-CN",
        "durationSeconds": 65,
        "beatWeights": [1, 1, 1, 1, 1, 1],
        "scenes": [
            {"sceneId": f"s{i}", "speaker": {"layout": "speaker_fullscreen"}}
            for i in range(6)
        ],
    }
    out = apply_numeric_range(plan, ORIGINAL2, locale="zh-CN")
    assert out["semanticNumericRangeEnabled"] is False
    assert all("semanticMotionV14" not in scene for scene in out["scenes"])
    monkeypatch.setenv("SEMANTIC_NUMERIC_RANGE_ENABLED", "1")
    armed = apply_numeric_range(plan, ORIGINAL2, locale="zh-CN")
    ranges = [scene.get("semanticMotionV14") for scene in armed["scenes"] if scene.get("semanticMotionV14")]
    assert ranges
    assert all(item["visualIntent"] == "numeric_range" for item in ranges)
    assert any(item["range"]["unit"] == "泰国" and item["range"]["lowText"] == "1.5万" for item in ranges)
    assert all("股权" not in json.dumps(item, ensure_ascii=False) for item in ranges)


def test_salary_ranges_stay_on_separate_scenes(monkeypatch):
    monkeypatch.setenv("SEMANTIC_NUMERIC_RANGE_ENABLED", "1")
    plan = {
        "language": "zh-CN",
        "durationSeconds": 65,
        "beatWeights": [1, 1],
        "scenes": [
            {"sceneId": "a", "speaker": {"layout": "speaker_fullscreen"}},
            {"sceneId": "b", "speaker": {"layout": "speaker_fullscreen"}},
        ],
    }
    out = apply_numeric_range(plan, ORIGINAL2, locale="zh-CN")
    ranges = [scene["semanticMotionV14"] for scene in out["scenes"] if (scene.get("semanticMotionV14") or {}).get("visualIntent") == "numeric_range"]
    bands = {(item["range"]["low"], item["range"]["high"], (item.get("evidence") or {}).get("segmentId")) for item in ranges}
    assert bands == {
        (15000, 25000, "seg_006"),
        (3000, 4000, "seg_007"),
        (25000, 35000, "seg_010"),
        (40000, 50000, "seg_011"),
        (8000, 10000, "seg_012"),
        (400, 1200, "seg_016"),
    }
    accepted = [row for row in out["semanticEventAudit"] if row["status"] == "accepted"]
    assert len(accepted) == 6
    assert all(row["flags"] == [] and row["outputTime"][1] > row["outputTime"][0] for row in accepted)


def test_scaled_numbers_must_be_derived_and_bands_stay_separate():
    quote = "月薪差不多在1.5-2.5万泰国左右吧"
    assert normalized_grounded(quote, 15000, 25000)
    assert not normalized_grounded(quote, 1500, 2500)
    assert not normalized_grounded(quote, 15, 25)
    assert "15000" not in quote
    spoken = "折合人民币三四千"
    assert normalized_grounded(spoken, 3000, 4000)
    assert not normalized_grounded(spoken, 3, 4)
    wan = "也就是8000-1万块的人民币"
    assert normalized_grounded(wan, 8000, 10000)
    joined = "月薪差不多在1.5-2.5万泰国左右吧 优秀的甚至能拿到4-5万泰诸"
    assert normalized_grounded(joined, 15000, 25000)
    assert normalized_grounded(joined, 40000, 50000)
    assert not normalized_grounded(joined, 15000, 50000)
    first = classify_numeric_range(joined, {"id": "joined", "start": 0, "end": 1}, locale="zh-CN")
    assert first["range"]["low"] == 15000
    assert first["range"]["high"] == 25000
    forged = json.loads(json.dumps(first))
    forged["range"]["currency"] = "泰铢"
    assert parameters_grounded(forged) is False
    year = "要从家庭未来五到十年的生活出发"
    assert classify_numeric_range(year, {"id": "y", "start": 0, "end": 1}, locale="zh-CN") is None
    assert normalized_grounded(year, 5, 10) is False
