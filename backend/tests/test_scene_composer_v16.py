"""V16 composer — speaker size, caption clearance, media match, diversity."""
from __future__ import annotations

import json
from pathlib import Path

from backend.scene_composer_v16 import (
    _safe,
    apply_scene_composer,
    caption_rect,
    enabled,
    geometry_from_pixels,
    wrap_lines,
)

ROOT = Path(__file__).resolve().parents[2]
TRANSCRIPT = json.loads((ROOT / "data/director_v5_original1/source.transcript.json").read_text(encoding="utf-8"))


def _plan():
    scenes = []
    for i, intent in enumerate(["capital_flow", "shareholder_network", "ownership_split", "business_comparison", "document_workflow"]):
        scenes.append({
            "sceneId": f"s{i}",
            "speaker": {"layout": "speaker_fullscreen"},
            "background": {"assetId": "cev6_i2v_re_facade_004", "file": "motion/cinematic-env-v6/clips/cev6_i2v_re_facade_004.mp4"},
            "semanticMotionV14": {
                "componentId": f"motion.{intent}.v1",
                "visualIntent": intent,
                "layout": "full_frame",
                "evidence": {"segmentId": "seg", "sourceTimestamp": [2 + i * 8, 6 + i * 8], "sourceQuote": "Capital enters the company", "factClass": "source_stated"},
            },
        })
    return {
        "language": "en-US",
        "durationSeconds": 60,
        "beatWeights": [1, 1, 1, 1, 1],
        "scenes": scenes,
    }


def test_flag_off(monkeypatch):
    monkeypatch.delenv("SCENE_COMPOSER_V16_ENABLED", raising=False)
    assert enabled() is False
    out = apply_scene_composer(_plan(), TRANSCRIPT, locale="en-US")
    assert out["sceneComposerV16Enabled"] is False
    assert "sceneComposition" not in out["scenes"][0]
    assert out["scenes"][0]["semanticMotionV14"]["layout"] == "full_frame"


def test_speaker_is_large_and_clears_face_and_captions(monkeypatch):
    monkeypatch.setenv("SCENE_COMPOSER_V16_ENABLED", "1")
    face = geometry_from_pixels([(30 + (i % 4), 20 + i) for i in range(16)], (90, 160))
    assert face is not None
    out = apply_scene_composer(_plan(), TRANSCRIPT, locale="en-US", geometry={"method": "test", "face": face})
    assert out["sceneComposerV16Enabled"] is True
    for scene in out["scenes"]:
        comp = scene["sceneComposition"]
        speaker = comp["speakerRegion"]
        motion = scene["semanticMotionV14"]["motionRect"]
        face_box = scene["semanticMotionV14"]["faceRect"]
        cap = scene["semanticMotionV14"]["captionRect"]
        assert speaker["width"] >= 640
        assert _safe(scene["semanticMotionV14"]["speakerMode"], speaker, motion, face_box, cap)
        assert scene["semanticMotionV14"]["layout"] != "full_frame"
        assert "full_frame" not in comp["layout"]
        assert comp["selectionExplanation"]


def test_diversity_breaks_a_three_peat(monkeypatch):
    monkeypatch.setenv("SCENE_COMPOSER_V16_ENABLED", "1")
    face = {"left": 250, "top": 180, "width": 580, "height": 520}
    out = apply_scene_composer(_plan(), TRANSCRIPT, locale="en-US", geometry={"method": "test", "face": face})
    layouts = [row["layout"] for row in out["sceneComposerV16Usage"]]
    assert not any(layouts[i] == layouts[i + 1] == layouts[i + 2] for i in range(len(layouts) - 2))


def test_banned_background_is_replaced(monkeypatch):
    monkeypatch.setenv("SCENE_COMPOSER_V16_ENABLED", "1")
    out = apply_scene_composer(_plan(), TRANSCRIPT, locale="en-US", geometry={"method": "test", "face": {"left": 250, "top": 180, "width": 580, "height": 520}})
    assets = {scene["sceneId"]: (scene.get("background") or {}).get("assetId") for scene in out["scenes"]}
    assert "facade" not in assets["s0"]
    assert assets["s0"] == "cev6_i2v_inv_glass_002"
    assert assets["s1"] == "cev6_i2v_biz_meeting_002"


def test_beige_wall_is_not_a_face():
    from backend.scene_composer_v16 import _skin
    assert _skin(130, 113, 88) is False
    assert _skin(231, 189, 165) is True


def test_wrap_and_caption_stay_in_frame():
    en = wrap_lines("Bank accounts work permits and visa applications", "en-US", 18)
    assert all(" " not in line or line == line.strip() for line in en)
    assert all(not any(len(part) > 18 and " " not in part for part in line.split()) for line in en)
    zh = wrap_lines("银行开户、工作证、签证申请都会盯着资金", "zh-CN", 8)
    assert any("、" in line for line in zh)
    rect = caption_rect("so the foreign capital ratio is usually less than 49%", "en-US")
    assert rect["top"] >= 0
    assert rect["top"] + rect["height"] <= 1920


def test_no_invented_values(monkeypatch):
    monkeypatch.setenv("SCENE_COMPOSER_V16_ENABLED", "1")
    plan = _plan()
    plan["scenes"][2]["semanticMotionV14"]["values"] = [{"value": 49, "qualifier": "at_most"}]
    out = apply_scene_composer(plan, TRANSCRIPT, locale="zh-CN", geometry={"method": "test", "face": {"left": 200, "top": 200, "width": 500, "height": 500}})
    values = out["scenes"][2]["semanticMotionV14"]["values"]
    assert values == [{"value": 49, "qualifier": "at_most"}]


def test_pip_scene_without_a_diagram_stays_full_frame(monkeypatch):
    monkeypatch.setenv("SCENE_COMPOSER_V16_ENABLED", "1")
    plan = _plan()
    plan["scenes"].append({
        "sceneId": "proof",
        "speaker": {"layout": "speaker_with_media", "framing": "pip"},
        "background": {"assetId": "cev6_i2v_city_harbor_003", "file": "x"},
    })
    out = apply_scene_composer(plan, TRANSCRIPT, locale="en-US", geometry={"method": "test", "face": {"left": 400, "top": 600, "width": 320, "height": 280}})
    proof = out["scenes"][-1]
    assert proof["sceneComposition"]["speakerPresentation"] == "fullscreen"
    assert proof["sceneComposition"]["speakerRegion"]["width"] == 1080
