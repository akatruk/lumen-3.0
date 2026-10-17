"""Editorial policy across the four source shapes. Not original4-hardcoded."""
from backend.director_v8 import LONG_BEATS
from backend.editorial_decision import apply_editorial_decision, relevance

TEMPLATE = [beat["weight"] for beat in LONG_BEATS]


def _scene(scene_id, *, layout, framing, asset=None, query=None, cards=None, steps=None, title=None):
    typography = {}
    if cards:
        typography["cards"] = cards
    if steps:
        typography["steps"] = steps
    if title:
        typography["stepsTitle"] = title
    return {
        "sceneId": scene_id,
        "query": query,
        "speaker": {"layout": layout, "framing": framing},
        "background": {"assetId": asset, "file": f"{asset}.png" if asset else None},
        "foreground": {},
        "typography": typography,
        "execution": {},
    }


def _plan(scenes, transcript_seconds=60):
    return {
        "scenes": scenes,
        "beatWeights": [1] * len(scenes),
        "durationSeconds": transcript_seconds,
    }


def test_generic_property_stock_does_not_cover_a_real_estate_sentence():
    quote = "买房送身份听起来特别诱人"
    assert relevance(quote, "family home doorway relocation", "people_property_001") == 0
    plan = _plan([
        _scene("residency", layout="speaker_split_right", framing="split", asset="people_property_001", query="document review desk paperwork"),
        _scene("consult", layout="speaker_with_media", framing="pip", asset="cev7_i2v_cap_ceo_advisor_006", query="phone consultation office advisor"),
        _scene("steps", layout="speaker_with_diagram", framing="pip", steps=["咨询", "方案", "文件"], title="全程陪同"),
    ])
    transcript = [{"start": 0, "end": 60, "zh": quote, "original": quote}]
    out = apply_editorial_decision(
        plan, transcript, locale="zh-CN", target_seconds=60, source_seconds=85.5, duration_mode="target",
    )
    assert out["durationContract"]["sourceSeconds"] == 85.5
    assert out["durationContract"]["targetSeconds"] == 60
    assert out["durationContract"]["mode"] == "target"
    for scene in out["scenes"]:
        assert scene["sceneComposition"]["speakerPresentation"] == "fullscreen"
        assert scene["background"]["assetId"] is None
        assert scene["editorial"]["purpose"] == "speaker-full"
    assert out["scenes"][2]["steps"] == []


def test_passport_evidence_keeps_one_plate_and_rejects_the_repeat():
    quote = "办理护照是营销里的身份承诺"
    assert relevance(quote, "passport", "passport_cover") >= 0.5
    scenes = [
        _scene("a", layout="speaker_split_right", framing="split", asset="passport_cover", query="passport"),
        _scene("b", layout="speaker_with_media", framing="pip", asset="passport_cover", query="passport"),
    ]
    plan = _plan(scenes)
    transcript = [{"start": 0, "end": 30, "zh": quote, "original": quote}, {"start": 30, "end": 60, "zh": quote, "original": quote}]
    out = apply_editorial_decision(
        plan, transcript, locale="zh-CN", target_seconds=60, source_seconds=85.5, duration_mode="target",
    )
    assert out["scenes"][0]["sceneComposition"]["editorial"] == "support"
    assert out["scenes"][0]["speaker"]["framing"] == "split"
    assert out["scenes"][1]["editorial"]["repeated"] is True
    assert out["scenes"][1]["sceneComposition"]["speakerPresentation"] == "fullscreen"


def test_original1_shareholder_sentence_does_not_gain_a_house_or_a_headcount():
    quote = "普通泰国有限公司通常需要至少三名股东"
    plan = _plan([
        _scene("context", layout="speaker_split_right", framing="split", asset="people_property_001", query="family home doorway relocation"),
        _scene("beside", layout="speaker_split_left", framing="split", cards=[{"title": "三名股东", "explanation": "至少三名股东"}]),
        _scene("steps", layout="speaker_with_diagram", framing="pip", cards=[{"title": "2 Shareholders", "explanation": "two"}]),
    ])
    transcript = [{"start": 0, "end": 60, "ru": quote, "zh": quote, "original": quote}]
    out = apply_editorial_decision(
        plan, transcript, locale="zh-CN", target_seconds=60, source_seconds=90, duration_mode="target",
    )
    assert out["scenes"][0]["background"]["assetId"] is None
    assert out["scenes"][1]["sceneComposition"]["editorial"] == "graphic"
    assert out["scenes"][1]["typography"]["cards"][0]["title"] == "三名股东"
    assert out["scenes"][2]["criteriaCards"] == []
    assert "2" not in str(out["scenes"][2].get("typography"))


def test_original2_salary_line_does_not_invent_currency():
    quote = "这笔是工资，那笔是翻译费用"
    plan = _plan([
        _scene("beside", layout="speaker_split_left", framing="split", cards=[{"title": "$8,000", "explanation": "salary"}]),
        _scene("proof", layout="speaker_with_media", framing="pip", asset="office_meeting_001", query="business meeting money"),
    ])
    transcript = [{"start": 0, "end": 60, "zh": quote, "original": quote}]
    out = apply_editorial_decision(
        plan, transcript, locale="zh-CN", target_seconds=60, source_seconds=70, duration_mode="target",
    )
    assert all(scene["sceneComposition"]["speakerPresentation"] == "fullscreen" for scene in out["scenes"])
    assert "$" not in str(out["scenes"][0])


def test_original3_identity_line_does_not_invent_a_country_or_a_salary():
    quote = "身份和家庭开支要分开看"
    plan = _plan([
        _scene("context", layout="speaker_split_right", framing="split", asset="people_property_001", query="family home doorway relocation"),
        _scene("beside", layout="speaker_split_left", framing="split", cards=[{"title": "泰国", "explanation": "工资 8000"}]),
    ])
    transcript = [{"start": 0, "end": 40, "zh": quote, "original": quote}]
    out = apply_editorial_decision(
        plan, transcript, locale="zh-CN", target_seconds=40, source_seconds=80, duration_mode="target",
    )
    assert out["scenes"][0]["background"]["assetId"] is None
    assert out["scenes"][1]["criteriaCards"] == []
    blob = str(out["scenes"])
    assert "8000" not in blob
    assert "泰国" not in blob


def test_rhythm_follows_speech_instead_of_the_long60_template():
    scenes = [_scene(f"b{i}", layout="speaker_fullscreen", framing="fullscreen") for i in range(10)]
    plan = _plan(scenes)
    plan["beatWeights"] = list(TEMPLATE)
    transcript = [{"start": 0, "end": 8, "zh": "先说护照", "original": "先说护照"}]
    out = apply_editorial_decision(
        plan, transcript, locale="zh-CN", target_seconds=60, source_seconds=85.5, duration_mode="target",
    )
    assert out["editorialRhythm"] == "transcript_midpoint"
    assert out["beatWeights"] != list(TEMPLATE)
    assert out["beatWeights"][0] > out["beatWeights"][-1]
    assert sum(out["beatWeights"]) == 1800
