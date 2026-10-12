from backend.director_v10_1 import REPAIR_BINDINGS, apply_premium_3d_v101, is_allowed, load_gate


def test_gate_rejects_float_over_speaker_trials():
    gate = load_gate()
    assert gate.get("approved_trial_v101") == []
    assert gate.get("production_ready") == []
    assert not is_allowed(
        gate, scene_id="problem", asset_id="l3d_generic_passport", motion="open"
    )
    assert not is_allowed(
        gate, scene_id="hook", asset_id="l3d_premium_suitcase", motion="slide_in"
    )


def test_v101_defaults_to_v9_baseline():
    assert REPAIR_BINDINGS == ()
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
            for sid in ("hook", "problem", "steps", "payoff", "return")
        ],
    }
    out = apply_premium_3d_v101(plan, seed=42)
    assert out["shotPlanVersion"] == "v10.1"
    assert out["compositionPolicy"] == "v9_clean"
    assert out["premium3d"]["boundCount"] == 0
    for scene in out["scenes"]:
        fo = (scene.get("composition") or {}).get("floatObject") or {}
        assert fo.get("family") != "premium_3d"
