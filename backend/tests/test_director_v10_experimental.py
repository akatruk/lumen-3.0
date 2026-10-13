"""Test-only PREMIUM_3D_MODE=experimental — speech match, no production_ready mutation."""
from __future__ import annotations

import json
from pathlib import Path

from backend.director_v10 import apply_premium_3d
from backend.director_v10_2 import (
    apply_premium_3d_experimental,
    load_gate,
    match_experimental_v2_assets,
)


GATE = Path(__file__).resolve().parents[2] / "media" / "library" / "3d_factory" / "quality_gate_v2.json"


def _scenes(*ids: str) -> list[dict]:
    return [
        {
            "sceneId": sid,
            "speaker": {"layout": "speaker_medium", "framing": "medium"},
            "shotPlan": {"keywords": []},
            "foreground": {},
            "semanticMotion": {},
            "typography": {},
            "background": {},
        }
        for sid in ids
    ]


def test_investment_speech_no_relevant_3d_asset():
    """origin1 / Chinese investment / Thailand — must NOT bind passport/suitcase/folder."""
    plan = {
        "visualSeed": 42,
        "transcript": [
            {"en": "Many people think that foreign investment companies only change the language of China"},
            {"en": "The core of Chinese investment companies is the capital investment"},
            {"en": "The first thing in Thailand is not money but the shareholder structure"},
            {"en": "Ordinary Thai companies usually need at least three shareholders"},
        ],
        "scenes": _scenes("hook", "problem", "steps", "payoff"),
    }
    out = apply_premium_3d_experimental(plan, seed=42)
    assert out["premium3d"]["status"] == "NO_RELEVANT_3D_ASSET"
    assert out["premium3d"]["boundCount"] == 0
    assert out["premium3d"]["bindings"] == []
    for scene in out["scenes"]:
        fo = (scene.get("composition") or {}).get("floatObject") or {}
        assert fo.get("family") != "premium_3d"
        assert fo.get("qualityStatus") != "experimental_override"


def test_passport_speech_binds_v2_without_touching_gate(tmp_path, monkeypatch):
    plan = {
        "visualSeed": 7,
        "transcript": [
            {"en": "First you need a valid passport and residence permit for relocation"},
        ],
        "scenes": _scenes("hook", "problem", "steps", "payoff"),
    }
    before = json.loads(GATE.read_text(encoding="utf-8"))
    assert before.get("production_ready") == []

    out = apply_premium_3d_experimental(plan, seed=7)
    assert out["premium3d"]["status"] == "BOUND"
    assert out["premium3d"]["boundCount"] >= 1
    assert any(b["assetId"] == "l3d_v2_passport" for b in out["premium3d"]["bindings"])
    bound = next(
        s for s in out["scenes"]
        if ((s.get("composition") or {}).get("floatObject") or {}).get("family") == "premium_3d"
    )
    fo = bound["composition"]["floatObject"]
    assert fo["format"] == "png_seq"
    assert fo["qualityStatus"] == "experimental_override"
    assert "alpha_png" in fo["file"]

    after = json.loads(GATE.read_text(encoding="utf-8"))
    assert after.get("production_ready") == []
    assert after == before


def test_env_experimental_routes_through_director_v10(monkeypatch):
    monkeypatch.setenv("PREMIUM_3D_MODE", "experimental")
    plan = {
        "visualSeed": 1,
        "transcript": [{"en": "Shareholder capital structure in Thailand investment companies"}],
        "scenes": _scenes("hook", "problem"),
    }
    out = apply_premium_3d(plan, seed=1)
    assert out["premium3d"]["policy"] == "experimental_speech_match"
    assert out["premium3d"]["status"] == "NO_RELEVANT_3D_ASSET"


def test_match_helper_rejects_structure_as_documents():
    hits = match_experimental_v2_assets(
        "the first thing in thailand is not money but the shareholder structure"
    )
    assert hits == []


def test_gate_file_still_empty_after_module_import():
    gate = load_gate()
    assert gate.get("production_ready") == []
