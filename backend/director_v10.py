"""Director V10 — premium 3D asset selection on top of V9 clean composition.

Uses approved 3D factory alpha clips (VP9 yuva420p) as float objects when a
semantic concept matches. Falls back to V9 SVG/PNG if no 3D variant is staged.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from . import director_v9

REGISTRY_CANDIDATES = (
    Path(__file__).resolve().parent.parent / "3d-library" / "3d-asset-registry.json",
    Path(__file__).resolve().parent.parent / "media" / "library" / "out" / "premium-3d-v1-rows.json",
)

# concept / keyword → 3d assetId
CONCEPT_TO_3D = {
    "relocation": "l3d_premium_suitcase",
    "passport": "l3d_generic_passport",
    "residency": "l3d_generic_passport",
    "documents": "l3d_document_folder",
    "program": "l3d_document_folder",
    "goals": "l3d_global_mobility_globe",
    "family": "l3d_global_mobility_globe",
    "consult": "l3d_document_folder",
    "budget": "l3d_apartment_building",
}


def load_registry(path: Path | None = None) -> list[dict]:
    if path and path.is_file():
        data = json.loads(path.read_text())
        return list(data.get("assets") or data if isinstance(data, list) else [])
    for cand in REGISTRY_CANDIDATES:
        if cand.is_file():
            data = json.loads(cand.read_text())
            if isinstance(data, list):
                return data
            return list(data.get("assets") or [])
    return []


def pick_3d_variant(
    *,
    concept: str,
    seed: int,
    used_variants: set[str],
    registry: list[dict] | None = None,
) -> dict | None:
    rows = registry if registry is not None else load_registry()
    asset_id = CONCEPT_TO_3D.get(concept)
    if not asset_id:
        return None
    candidates = [
        r for r in rows
        if (r.get("assetId") == asset_id or str(r.get("id", "")).startswith(asset_id))
        and r.get("qualityStatus", "approved") == "approved"
        and (r.get("alphaVerified") is not False)
    ]
    if not candidates:
        # rows from index may use id = variantId
        candidates = [
            r for r in rows
            if str(r.get("id") or "").startswith(asset_id + "__")
            and r.get("qualityStatus", "approved") == "approved"
        ]
    if not candidates:
        return None
    fresh = [c for c in candidates if (c.get("variantId") or c.get("id")) not in used_variants]
    pool = fresh or candidates
    rng = random.Random(seed + hash(concept) % 997)
    choice = rng.choice(pool)
    variant = choice.get("variantId") or choice.get("id")
    motion = choice.get("motion") or choice.get("motionPreset") or "reveal"
    # Prefer published library path, else factory alpha path
    file_rel = choice.get("file")
    if not file_rel:
        file_rel = f"motion/premium3d/{asset_id}_{motion}.webm"
        factory = Path(__file__).resolve().parent.parent / "3d-library" / "alpha" / f"{asset_id}_{motion}.webm"
        if factory.is_file() and not (Path(__file__).resolve().parent.parent / "media" / "library" / "out" / file_rel).is_file():
            file_rel = f"../3d-library/alpha/{asset_id}_{motion}.webm"
    return {
        "assetId": asset_id,
        "variantId": variant,
        "motion": motion,
        "file": file_rel,
        "concept": concept,
        "background": "transparent",
        "display": "float",
        "family": "premium_3d",
        "preferredPlacement": choice.get("preferredPlacement") or "speaker_right_lower",
        "areaShare": 0.16,
    }


def apply_premium_3d(plan: dict, *, seed: int | None = None) -> dict:
    """V10.1 quality gate (default). Legacy unbound V10 auto-pick is disabled.

    Set PREMIUM_3D_MODE=v10_legacy to restore the original auto-bind behavior
    for debugging only — do not use in production.
    """
    import os

    mode = (os.environ.get("PREMIUM_3D_MODE") or "v10.2").strip().lower()
    if mode in ("v10.2", "v102"):
        from . import director_v10_2

        return director_v10_2.apply_premium_3d_v102(plan, seed=seed)
    if mode in ("v10.1", "v101", "gate", ""):
        from . import director_v10_1

        return director_v10_1.apply_premium_3d_v101(plan, seed=seed)
    if mode in ("off", "0", "false", "v9"):
        out = director_v9.apply_composition_intelligence(plan)
        out["shotPlanVersion"] = out.get("shotPlanVersion") or "v9"
        out["premium3d"] = {"policy": "off", "bindings": [], "boundCount": 0, "pass": True}
        return out
    # --- legacy V10 auto-bind (explicit opt-in only) ---
    if plan.get("compositionPolicy") == "v9_clean" or plan.get("shotPlanVersion") in ("v9", "v10"):
        out = dict(plan)
    else:
        out = director_v9.apply_composition_intelligence(plan)
    registry = load_registry()
    used: set[str] = set()
    seed_i = int(seed or out.get("visualSeed") or 1)
    scenes = []
    bindings = []
    for scene in out.get("scenes") or []:
        scene = dict(scene)
        comp = dict(scene.get("composition") or {})
        fo = dict(comp.get("floatObject") or {})
        kids = []
        if fo.get("keyword"):
            kids.append(fo["keyword"])
        for k in ((scene.get("shotPlan") or {}).get("keywords") or []):
            if isinstance(k, dict) and k.get("id"):
                kids.append(k["id"])
            elif isinstance(k, str):
                kids.append(k)
        concept = next((c for c in kids if c in CONCEPT_TO_3D), None)
        if concept and fo:
            picked = pick_3d_variant(concept=concept, seed=seed_i, used_variants=used, registry=registry)
            if picked:
                used.add(picked["variantId"])
                picked["placement"] = fo.get("placement") or picked.get("preferredPlacement")
                picked["silhouette"] = picked["assetId"]
                comp["floatObject"] = picked
                comp["secondaryVisual"] = "premium_3d"
                scene["composition"] = comp
                fg = dict(scene.get("foreground") or {})
                fg["assetId"] = picked["assetId"]
                fg["file"] = picked["file"]
                fg["background"] = "transparent"
                fg["family"] = "premium_3d"
                scene["foreground"] = fg
                bindings.append({"sceneId": scene.get("sceneId"), **picked})
        scenes.append(scene)
    out["scenes"] = scenes
    out["shotPlanVersion"] = "v10"
    out["compositionPolicy"] = "v9_clean"
    out["premium3d"] = {
        "bindings": bindings,
        "registryCount": len(registry),
        "boundCount": len(bindings),
        "pass": len(bindings) >= 1 or not registry,
        "policy": "v10_legacy",
    }
    return out


def stage_premium_3d(plan: dict, public_dir: Path, library: Path | None = None) -> dict:
    """Stage gated PNG sequences (V10.1) or legacy webm when PREMIUM_3D_MODE=v10_legacy."""
    import os

    mode = (os.environ.get("PREMIUM_3D_MODE") or "v10.2").strip().lower()
    if mode in ("v10.2", "v102"):
        from . import director_v10_2

        return director_v10_2.stage_premium_3d_v102(plan, public_dir, library)
    if mode in ("v10.1", "v101", "gate", ""):
        from . import director_v10_1

        return director_v10_1.stage_premium_3d_v101(plan, public_dir, library)
    if mode in ("off", "0", "false", "v9"):
        return director_v9.stage_float_objects(plan, public_dir, library)

    root = Path(library or Path(__file__).resolve().parent.parent / "media" / "library" / "out")
    factory_alpha = Path(__file__).resolve().parent.parent / "3d-library" / "alpha"
    picked = Path(public_dir) / "picked"
    picked.mkdir(parents=True, exist_ok=True)
    out = dict(plan)
    scenes = []
    for scene in out.get("scenes") or []:
        scene = dict(scene)
        comp = dict(scene.get("composition") or {})
        fo = dict(comp.get("floatObject") or {})
        if fo.get("family") != "premium_3d" and not str(fo.get("file") or "").endswith(".webm"):
            scenes.append(scene)
            continue
        rel = fo.get("file")
        src = None
        if rel:
            cand = root / rel
            if cand.is_file():
                src = cand
            else:
                name = Path(rel).name
                for base in (root / "motion" / "premium3d", factory_alpha):
                    alt = base / name
                    if alt.is_file():
                        src = alt
                        break
                if src is None and (factory_alpha / name).is_file():
                    src = factory_alpha / name
        if src and src.is_file():
            dest = picked / src.name
            if not dest.exists() or dest.stat().st_size != src.stat().st_size:
                dest.write_bytes(src.read_bytes())
            fo["staged"] = f"picked/{dest.name}"
            fo["background"] = "transparent"
            fo["display"] = "float"
            fo["format"] = "webm_alpha"
            comp["floatObject"] = fo
            scene["composition"] = comp
            fg = dict(scene.get("foreground") or {})
            fg["staged"] = fo["staged"]
            fg["background"] = "transparent"
            scene["foreground"] = fg
        scenes.append(scene)
    out["scenes"] = scenes
    out = director_v9.stage_float_objects(out, public_dir, library)
    return out
