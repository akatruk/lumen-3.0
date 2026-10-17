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
    emphasis = [scene for scene in out["scenes"] if scene["editorial"]["purpose"] == "semantic-emphasis"]
    assert len(emphasis) <= 2
    assert emphasis
    for scene in out["scenes"]:
        assert scene["background"]["assetId"] is None
        phrase = scene["editorial"]["phrase"]
        if phrase:
            assert phrase in quote
            assert scene["sceneComposition"]["speakerPresentation"] == "emphasis"
            assert scene["editorial"]["component"] == "KineticHeadline"
            assert scene["speaker"]["visibility"] == "primary"
        else:
            assert scene["sceneComposition"]["speakerPresentation"] == "fullscreen"
        assert "全程陪同" not in str(scene.get("headline") or "")
        assert scene.get("steps") in (None, [])
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
    assert out["scenes"][1]["background"]["assetId"] is None
    repeated_phrase = out["scenes"][1]["editorial"]["phrase"]
    if repeated_phrase:
        assert repeated_phrase in quote
        assert out["scenes"][1]["sceneComposition"]["speakerPresentation"] == "emphasis"
    else:
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
    blob = str(out["scenes"])
    assert "$" not in blob
    assert "8000" not in blob
    assert "元" not in blob
    for scene in out["scenes"]:
        phrase = scene["editorial"]["phrase"]
        if phrase:
            assert phrase in quote
            assert scene["headline"] == phrase
        else:
            assert scene["sceneComposition"]["speakerPresentation"] == "fullscreen"


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


def test_a_spoken_number_becomes_an_overlay_without_a_plate():
    quote = "这套房的挂牌价大约是85万，后面再谈税费"
    plan = _plan([
        _scene("hook", layout="speaker_fullscreen", framing="fullscreen"),
        _scene("context", layout="speaker_split_right", framing="split", asset="people_property_001", query="family home"),
    ])
    transcript = [{"id": "seg-1", "start": 0, "end": 60, "zh": quote, "original": quote}]
    out = apply_editorial_decision(
        plan, transcript, locale="zh-CN", target_seconds=60, source_seconds=85.5, duration_mode="target",
    )
    emphasis = [scene for scene in out["scenes"] if scene["editorial"]["purpose"] == "semantic-emphasis"]
    assert len(emphasis) == 1
    first = emphasis[0]
    assert first["headline"] == "85万"
    assert first["execution"]["headline"] == "85万"
    assert first["headline"] in quote
    assert first["background"]["assetId"] is None
    assert first["editorial"]["segmentId"] == "seg-1"
    assert first["editorial"]["component"] == "KineticHeadline"
    assert all(scene["background"]["assetId"] is None for scene in out["scenes"])


# First 60s of the stored original4 ASR. Phrases below are substrings, not corrections.
ORIGINAL4_60 = [
    (0.0, 3.84, "买房送身份听起来是不是特别诱人"),
    (3.84, 6.68, "钱没花掉还白得个绿卡"),
    (6.68, 11.36, "甜美的陷阱往往就藏在这种占便宜的心理里"),
    (11.36, 15.76, "今天只没帮你们把移民价值和房厂价值"),
    (15.76, 18.92, "彻底路撥开来算比民白账"),
    (18.92, 21.12, "所谓的买房移民"),
    (21.12, 27.84, "房厂挂牌价里通常包含了高额的移民液水和开发商用金"),
    (27.84, 29.84, "在签字刷卡前"),
    (29.84, 33.72, "你必须理性问自己三个硬核问题"),
]


def test_original4_chinese_lines_become_two_kinetic_headlines(tmp_path):
    transcript = [
        {"id": f"seg-{index}", "start": start, "end": end, "zh": text, "original": text}
        for index, (start, end, text) in enumerate(ORIGINAL4_60)
    ]
    # 60s production plan is the 10-beat grid, not six equal slices.
    scenes = []
    for beat in LONG_BEATS:
        scene = _scene(beat["id"], layout="speaker_split_right", framing="split", asset=f"stock-{beat['id']}", query="family home meeting office")
        scene["composition"] = {"floatObject": {"assetId": "goal", "file": "static/icons/goal.svg"}}
        scene["execution"] = {"headline": "买房送身份听起来是不是特别诱人"}
        scenes.append(scene)
    plan = _plan(scenes)
    plan["beatWeights"] = [beat["weight"] for beat in LONG_BEATS]
    out = apply_editorial_decision(
        plan, transcript, locale="zh-CN", target_seconds=60, source_seconds=85.5, duration_mode="target",
    )
    emphasis = [scene for scene in out["scenes"] if scene["editorial"]["purpose"] == "semantic-emphasis"]
    assert len(emphasis) == 2
    phrases = [scene["headline"] for scene in emphasis]
    assert "甜美的陷阱" in phrases
    assert "硬核问题" in phrases
    assert "买房送身份听起来是不是特别诱人" not in phrases
    late = next(scene for scene in emphasis if scene["headline"] == "硬核问题")
    assert late["editorial"]["quoteSeconds"][0] >= 20
    early = next(scene for scene in emphasis if scene["headline"] == "甜美的陷阱")
    assert late["editorial"]["quoteSeconds"][0] - early["editorial"]["quoteSeconds"][0] >= 15
    # The opening beat starts at 0. The title waits for the spoken line.
    assert early["editorial"]["quoteSeconds"][0] == 0
    assert early["emphasisRange"] == [6.68, 11.36]
    assert early["editorial"]["displaySeconds"] == [6.68, 11.36]
    assert late["emphasisRange"][0] >= 20
    assert late["editorial"]["displaySeconds"] == late["emphasisRange"]
    spoken = {row["original"]: row["id"] for row in transcript}
    for scene in emphasis:
        phrase = scene["headline"]
        host = next(text for text in spoken if phrase in text)
        assert scene["editorial"]["segmentId"] == spoken[host]
        assert scene["editorial"]["component"] == "KineticHeadline"
        assert scene["sceneComposition"]["speakerPresentation"] == "emphasis"
        assert scene["speaker"]["visibility"] == "primary"
        assert scene["speaker"]["layout"] == "speaker_medium"
        assert scene["execution"]["headline"] == phrase
        assert (scene.get("composition") or {}).get("floatObject") is None
        assert scene["background"]["assetId"] is None
        assert "步骤" not in str(scene)
        assert scene["editorial"]["phrase"] == phrase
    assert all(scene["background"]["assetId"] is None for scene in out["scenes"])
    blob = str(out["scenes"])
    assert "全程陪同" not in blob
    assert "诸经" not in blob
    assert "程交" not in blob
    from backend.director_v9 import stage_float_objects
    staged = stage_float_objects(out, tmp_path)
    for scene in staged["scenes"]:
        if scene["editorial"]["purpose"] != "semantic-emphasis":
            continue
        assert (scene.get("foreground") or {}).get("file") is None
        assert ((scene.get("composition") or {}).get("floatObject") or {}).get("staged") is None
