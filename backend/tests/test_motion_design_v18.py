"""V18 keeps a diagram only when the scene quote supports it."""
import json
from pathlib import Path

from backend.motion_design_v18 import apply_motion_design, enabled, speech_query, supports_equity

ROOT = Path(__file__).resolve().parents[2]
TRANSCRIPT = ROOT / "data" / "original2" / "source.transcript.json"


def _plan(quotes):
    scenes = []
    for index, quote in enumerate(quotes):
        scenes.append({
            "sceneId": f"s{index}",
            "query": "bangkok business district skyline daytime",
            "background": {"assetId": "cev6_i2v_city_skyline_001", "file": "x.mp4"},
            "businessMotion": {
                "component": "company_ownership",
                "labels": {"title": "股权结构"},
                "topologyNodes": 3,
            },
            "typography": {
                "stepsTitle": "设立路径",
                "steps": ["资本", "结构", "控制权"],
                "cards": [{"title": "股东", "explanation": "x"}],
                "cardMode": "progressive_one",
            },
            "speaker": {"layout": "speaker_split_left"},
        })
    return {
        "scenes": scenes,
        "beatWeights": [1] * len(scenes),
        "durationSeconds": 10 * len(scenes),
        "transcript": [
            {"start": i * 10, "end": i * 10 + 9, "original": quote, "id": f"seg_{i}"}
            for i, quote in enumerate(quotes)
        ],
    }


def test_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("MOTION_DESIGN_V18_ENABLED", raising=False)
    assert enabled() is False
    out = apply_motion_design(_plan(["在泰国请翻译"]))
    assert out["motionDesignV18Enabled"] is False
    assert out["scenes"][0]["businessMotion"]["component"] == "company_ownership"


def test_thailand_pay_is_not_an_equity_tree(monkeypatch):
    monkeypatch.setenv("MOTION_DESIGN_V18_ENABLED", "1")
    quote = "在泰国请翻译到底要花多少钱 8000-1万块人民币"
    assert supports_equity(quote) is False
    out = apply_motion_design(_plan([quote, "如果只是找华裔泰国人做陪同"]))
    for scene in out["scenes"]:
        assert scene.get("businessMotion") is None
        assert "股权" not in json.dumps(scene.get("typography") or {}, ensure_ascii=False)
        assert scene["sceneComposition"]["speakerPresentation"] == "fullscreen"
        assert "skyline" not in str(scene.get("query") or "")
    assert out["scenes"][0]["query"] == speech_query(quote)


def test_shareholder_quote_keeps_a_diagram(monkeypatch):
    monkeypatch.setenv("MOTION_DESIGN_V18_ENABLED", "1")
    quote = "普通泰国有限公司通常需要至少三名股东"
    assert supports_equity(quote) is True
    plan = _plan([quote])
    plan["scenes"][0]["semanticMotionV14"] = {
        "componentId": "motion.shareholder_network.v1",
        "visualIntent": "shareholder_network",
        "layout": "overlay",
        "faceRect": {"left": 200, "top": 400, "width": 400, "height": 280},
        "motionRect": {"left": 72, "top": 1100, "width": 900, "height": 360},
        "captionRect": {"left": 64, "top": 1500, "width": 952, "height": 200},
    }
    out = apply_motion_design(plan)
    kept = out["scenes"][0]["semanticMotionV14"]
    assert kept["componentId"] == "motion.shareholder_network.v1"
    assert kept["version"] == "v18"
    assert kept["columnScrim"] is False
    assert kept["motionRect"]["top"] >= 400


def test_original2_transcript_has_no_equity_graphic(monkeypatch):
    if not TRANSCRIPT.is_file():
        return
    monkeypatch.setenv("MOTION_DESIGN_V18_ENABLED", "1")
    rows = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
    quotes = [row["original"] for row in rows]
    out = apply_motion_design(_plan(quotes[:8]))
    blob = json.dumps(out["scenes"], ensure_ascii=False)
    assert "股权结构" not in blob
    assert "设立路径" not in blob
    assert all(scene.get("businessMotion") is None for scene in out["scenes"])


def test_three_identical_compositions_collapse(monkeypatch):
    monkeypatch.setenv("MOTION_DESIGN_V18_ENABLED", "1")
    quote = "至少三名股东的有限公司"
    plan = _plan([quote, quote, quote])
    for scene in plan["scenes"]:
        scene["query"] = "corporate boardroom"
        scene["background"] = {"assetId": "meeting"}
        scene["semanticMotionV14"] = {
            "componentId": "motion.shareholder_network.v1",
            "visualIntent": "shareholder_network",
            "layout": "overlay",
            "mediaSide": "left",
        }
    out = apply_motion_design(plan)
    keys = []
    for scene in out["scenes"]:
        payload = scene.get("semanticMotionV14") or {}
        if payload.get("visualIntent"):
            keys.append((payload.get("layout"), payload.get("mediaSide")))
    assert not (len(keys) >= 3 and keys[0] == keys[1] == keys[2])
