from backend.director_v10_2 import apply_premium_3d_v102, is_premium_ready, load_gate


def test_gate_empty_production_ready_by_default():
    gate = load_gate()
    assert gate.get("production_ready") == []
    assert not is_premium_ready(gate, "l3d_v2_passport", "passport_open")


def test_v102_defaults_to_v9_when_not_ready():
    plan = {
        "visualSeed": 42,
        "scenes": [
            {
                "sceneId": sid,
                "speaker": {"layout": "speaker_medium", "framing": "medium"},
                "shotPlan": {"keywords": [{"id": "relocation"}, {"id": "residency"}, {"id": "documents"}]},
                "foreground": {},
                "semanticMotion": {},
                "typography": {"stepsTitle": "Steps"} if sid == "steps" else {},
                "background": {},
            }
            for sid in ("hook", "problem", "steps", "payoff")
        ],
    }
    out = apply_premium_3d_v102(plan, seed=42)
    assert out["shotPlanVersion"] == "v10.2"
    assert out["premium3d"]["boundCount"] == 0
    for scene in out["scenes"]:
        fo = (scene.get("composition") or {}).get("floatObject") or {}
        assert fo.get("family") != "premium_3d"
