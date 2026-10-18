"""original4 passage overlay stays inside one project file."""
from backend.passage_experiment import apply_passage_experiment, correct_transcript

PID = "210d701a7b9e44c1bb2eb177f6a00742"

ROWS = [
    {"start": 33.72, "end": 38.84, "text": "第一,去查当地人的真实二手房程交数据"},
    {"start": 38.84, "end": 42.68, "text": "这套房子真实市场价值打击折"},
    {"start": 42.68, "end": 48.92, "text": "第二,海报上的诸经回报率是毛售益还是扣除物业"},
    {"start": 48.92, "end": 53.84, "text": "管理费,控制损耗核税后的金售益"},
    {"start": 53.84, "end": 56.72, "text": "第三,持满法定年县后"},
    {"start": 56.72, "end": 59.34, "text": "當地本地人會借盤嗎?"},
    {"start": 59.34, "end": 62.68, "text": "還是只能賣給下一個中國買家?"},
    {"start": 64.68, "end": 67.48, "text": "買到偏遠地區的垃圾盤"},
]


def _plan():
    return {"scenes": [{"id": f"s{i}", "editorial": {"purpose": "speaker-full"}} for i in range(10)]}


def test_caption_tokens_are_replaced_only_on_the_matching_row():
    fixed = correct_transcript(ROWS, PID)
    text = " ".join(row["text"] for row in fixed)
    assert "程交" not in text and "成交" in text
    assert "诸经" not in text and "租金回报率" in text
    assert "毛售益" not in text and "毛收益" in text
    assert "金售益" not in text and "净收益" in text
    assert "年县" not in text and "年限" in text
    assert "借盤" not in text and "接盘" in text
    assert "扣除物业" in text
    assert "控制损耗" in text
    assert correct_transcript(ROWS, "other-project")[0]["text"].endswith("程交数据")


def test_three_checks_follow_the_ordinals_and_keep_reviewed_plates():
    plan = apply_passage_experiment(_plan(), correct_transcript(ROWS, PID), PID, "zh-CN")
    scenes = plan["scenes"]
    assert scenes[4]["editorial"]["quoteSeconds"] == [33.72, 42.68]
    assert scenes[4]["background"]["assetId"] == "re_mkt_comparable_masses"
    assert [card["title"] for card in scenes[4]["criteriaCards"]] == ["二手房成交", "市场价值"]
    assert scenes[5]["editorial"]["quoteSeconds"] == [42.68, 53.84]
    assert scenes[5]["background"]["assetId"] == "re_rent_column_remainder"
    titles = [card["title"] for card in scenes[5]["criteriaCards"]]
    assert titles[:2] == ["毛收益", "净收益"]
    assert "税后" not in titles and "扣除" not in titles
    assert scenes[6]["editorial"]["quoteSeconds"][0] == 53.84
    assert scenes[6]["background"]["assetId"] == "re_liq_two_paths"
    assert [card["title"] for card in scenes[6]["criteriaCards"]] == ["本地人", "买家"]
    assert all("中国" not in card["title"] for card in scenes[6]["criteriaCards"])
    assert not (scenes[7].get("background") or {}).get("assetId")
    assert scenes[8]["background"]["assetId"] == "re_fin_distant_building"
    assert sum(plan["beatWeights"]) == round(85.5 * 30)
    assert apply_passage_experiment(_plan(), ROWS, "other-project", "zh-CN")["scenes"][4].get("background") is None
