from backend.director_v10 import CONCEPT_TO_3D, apply_premium_3d, pick_3d_variant


def test_concept_map_covers_pilot():
    for concept in ("relocation", "passport", "documents", "goals"):
        assert concept in CONCEPT_TO_3D


def test_pick_from_registry():
    registry = [
        {
            "assetId": "l3d_premium_suitcase",
            "variantId": "l3d_premium_suitcase__reveal",
            "motion": "reveal",
            "qualityStatus": "approved",
            "alphaVerified": True,
            "file": "motion/premium3d/l3d_premium_suitcase_reveal.webm",
            "preferredPlacement": "speaker_left_lower",
        },
        {
            "assetId": "l3d_premium_suitcase",
            "variantId": "l3d_premium_suitcase__slide_in",
            "motion": "slide_in",
            "qualityStatus": "approved",
            "alphaVerified": True,
            "file": "motion/premium3d/l3d_premium_suitcase_slide_in.webm",
        },
    ]
    used = set()
    a = pick_3d_variant(concept="relocation", seed=1, used_variants=used, registry=registry)
    assert a is not None
    assert a["family"] == "premium_3d"
    used.add(a["variantId"])
    b = pick_3d_variant(concept="relocation", seed=2, used_variants=used, registry=registry)
    assert b is not None
    # Prefer unused variant when available
    assert b["variantId"] != a["variantId"] or len(registry) == 1


def test_apply_keeps_clean_policy(monkeypatch):
    monkeypatch.delenv("PREMIUM_3D_MODE", raising=False)
    plan = {
        "compositionPolicy": "v9_clean",
        "shotPlanVersion": "v9",
        "visualSeed": 7,
        "scenes": [
            {
                "sceneId": "hook",
                "speaker": {"layout": "speaker_punch_in", "framing": "close"},
                "composition": {
                    "floatObject": {
                        "keyword": "relocation",
                        "assetId": "imm_obj_suitcase",
                        "background": "transparent",
                        "placement": "speaker_right_lower",
                    }
                },
                "shotPlan": {"keywords": [{"id": "relocation"}]},
                "foreground": {},
                "semanticMotion": {},
                "typography": {},
            }
        ],
    }
    out = apply_premium_3d(plan, seed=7)
    # Default path is V10.1 quality gate — no unverified 3D on hook.
    assert out["shotPlanVersion"] == "v10.1"
    assert out["compositionPolicy"] == "v9_clean"
    fo = (out["scenes"][0].get("composition") or {}).get("floatObject") or {}
    assert fo.get("family") != "premium_3d"
