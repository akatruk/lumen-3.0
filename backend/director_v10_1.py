"""Director V10.1 — premium 3D quality recovery on the V9 editorial baseline.

3D is optional. Only quality-gated approved_trial / production_ready variants
may replace a V9 float. Weak V10 auto-bindings are rejected.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from . import director_v9

ROOT = Path(__file__).resolve().parent.parent
GATE_PATH = ROOT / "media" / "library" / "3d_factory" / "quality_gate_v101.json"
ALPHA_PNG = ROOT / "3d-library" / "alpha_png"

# Post V10.1 moving review: float-over-speaker 3D lost to V9 on all three
# trial moments (face collision / plastic clutter). Keep the structure for
# future cutaway_hero experiments; gate + empty list = V9 baseline delivery.
REPAIR_BINDINGS: tuple[dict[str, Any], ...] = ()

# Archived trial bindings (do not re-enable without cutaway layout + production_ready).
_ARCHIVED_REPAIR_BINDINGS: tuple[dict[str, Any], ...] = (
    {
        "sceneId": "problem",
        "assetId": "l3d_generic_passport",
        "motion": "open",
        "concept": "residency",
        "scaleProfile": "hero",
        "areaShare": 0.3,
        "placement": "speaker_right_lower",
        "review": "REJECTED_face_collision",
    },
    {
        "sceneId": "steps",
        "assetId": "l3d_document_folder",
        "motion": "open",
        "concept": "documents",
        "scaleProfile": "supporting",
        "areaShare": 0.22,
        "placement": "speaker_left_lower",
        "review": "REJECTED_worse_than_v9",
    },
    {
        "sceneId": "payoff",
        "assetId": "l3d_premium_suitcase",
        "motion": "reveal",
        "concept": "relocation",
        "scaleProfile": "hero",
        "areaShare": 0.28,
        "placement": "speaker_left_lower",
        "review": "REJECTED_plastic_vs_v9_svg",
    },
)


def load_gate(path: Path | None = None) -> dict:
    p = path or GATE_PATH
    if not p.is_file():
        return {"approved_trial_v101": [], "production_ready": [], "sceneAllowlist": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def variant_id(asset_id: str, motion: str) -> str:
    return f"{asset_id}__{motion}"


def is_allowed(gate: dict, *, scene_id: str, asset_id: str, motion: str) -> bool:
    vid = variant_id(asset_id, motion)
    if vid in (gate.get("rejected") or []):
        return False
    ready = set(gate.get("production_ready") or [])
    trial = set(gate.get("approved_trial_v101") or [])
    if vid not in ready and vid not in trial:
        return False
    allow = (gate.get("sceneAllowlist") or {}).get(scene_id)
    if allow is not None and vid not in allow:
        return False
    seq = ALPHA_PNG / asset_id / motion
    if not seq.is_dir() or not any(seq.glob("frame_*.png")):
        return False
    return True


def _png_frame_count(asset_id: str, motion: str) -> int:
    seq = ALPHA_PNG / asset_id / motion
    return len(sorted(seq.glob("frame_*.png"))) if seq.is_dir() else 0


def build_float(binding: dict, gate: dict) -> dict | None:
    asset_id = binding["assetId"]
    motion = binding["motion"]
    if not is_allowed(gate, scene_id=binding["sceneId"], asset_id=asset_id, motion=motion):
        return None
    profiles = gate.get("scaleProfiles") or {}
    profile_name = binding.get("scaleProfile") or "supporting"
    profile = profiles.get(profile_name) or {}
    area = float(binding.get("areaShare") or profile.get("areaShare") or 0.22)
    n = _png_frame_count(asset_id, motion)
    return {
        "assetId": asset_id,
        "variantId": variant_id(asset_id, motion),
        "motion": motion,
        "file": f"3d-library/alpha_png/{asset_id}/{motion}",
        "concept": binding.get("concept"),
        "background": "transparent",
        "display": "float",
        "family": "premium_3d",
        "format": "png_seq",
        "frameCount": n,
        "fps": 30,
        "scaleProfile": profile_name,
        "areaShare": area,
        "minPx": int(profile.get("minPx") or 300),
        "maxPx": int(profile.get("maxPx") or 560),
        "preferredPlacement": binding.get("placement") or "speaker_right_lower",
        "placement": binding.get("placement") or "speaker_right_lower",
        "silhouette": asset_id,
        "qualityStatus": "approved_trial",
    }


def apply_premium_3d_v101(plan: dict, *, seed: int | None = None) -> dict:
    """Always rebuild V9 composition, then overlay only approved 3D repairs."""
    del seed  # seed reserved for future gated RNG; repairs are explicit
    out = director_v9.apply_composition_intelligence(plan)
    gate = load_gate()
    by_scene = {b["sceneId"]: b for b in REPAIR_BINDINGS}
    scenes = []
    bindings = []
    rejected = []

    for scene in out.get("scenes") or []:
        scene = dict(scene)
        sid = scene.get("sceneId")
        repair = by_scene.get(sid)
        if not repair:
            scenes.append(scene)
            continue
        picked = build_float(repair, gate)
        if not picked:
            rejected.append({
                "sceneId": sid,
                "variantId": variant_id(repair["assetId"], repair["motion"]),
                "reason": "gate_or_missing_png_seq",
            })
            scenes.append(scene)
            continue
        comp = dict(scene.get("composition") or {})
        # Complexity: steps already owns type — allow supporting 3D only
        if sid == "steps":
            metrics = scene.get("visualComplexityScore") or {}
            # Keep CleanSteps; folder is supporting secondary
            pass
        comp["floatObject"] = picked
        comp["secondaryVisual"] = "premium_3d"
        comp["suppressHero"] = True
        scene["composition"] = comp
        scene["heroObject"] = None
        fg = dict(scene.get("foreground") or {})
        fg["assetId"] = picked["assetId"]
        fg["file"] = picked["file"]
        fg["background"] = "transparent"
        fg["family"] = "premium_3d"
        fg["format"] = "png_seq"
        scene["foreground"] = fg
        # Omit opaque semantic webm boxes
        sm = dict(scene.get("semanticMotion") or {})
        sm["display"] = "omit"
        sm.pop("staged", None)
        scene["semanticMotion"] = sm
        bindings.append({"sceneId": sid, **picked})
        scenes.append(scene)

    out["scenes"] = scenes
    out["shotPlanVersion"] = "v10.1"
    out["compositionPolicy"] = "v9_clean"
    out["premium3d"] = {
        "policy": "v10.1_quality_gate",
        "bindings": bindings,
        "rejected": rejected,
        "boundCount": len(bindings),
        "productionReady": list(gate.get("production_ready") or []),
        "approvedTrial": list(gate.get("approved_trial_v101") or []),
        "pass": True,
        "deliveryFormat": gate.get("deliveryFormat") or "png_seq",
    }
    return out


def stage_premium_3d_v101(plan: dict, public_dir: Path, library: Path | None = None) -> dict:
    """Stage approved PNG sequences into Remotion public/picked (true RGBA alpha)."""
    picked = Path(public_dir) / "picked"
    picked.mkdir(parents=True, exist_ok=True)
    out = dict(plan)
    scenes = []
    for scene in out.get("scenes") or []:
        scene = dict(scene)
        comp = dict(scene.get("composition") or {})
        fo = dict(comp.get("floatObject") or {})
        if fo.get("format") != "png_seq":
            scenes.append(scene)
            continue
        asset_id = fo["assetId"]
        motion = fo["motion"]
        src = ALPHA_PNG / asset_id / motion
        dest = picked / f"{asset_id}_{motion}"
        if src.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            fo["staged"] = f"picked/{dest.name}"
            fo["format"] = "png_seq"
            fo["frameCount"] = len(sorted(dest.glob("frame_*.png")))
            fo["background"] = "transparent"
            comp["floatObject"] = fo
            scene["composition"] = comp
            fg = dict(scene.get("foreground") or {})
            fg["staged"] = fo["staged"]
            fg["format"] = "png_seq"
            fg["background"] = "transparent"
            scene["foreground"] = fg
        scenes.append(scene)

    out["scenes"] = scenes
    out = director_v9.stage_float_objects(out, public_dir, library)
    return out


def apply_premium_3d(plan: dict, *, seed: int | None = None) -> dict:
    return apply_premium_3d_v101(plan, seed=seed)


def stage_premium_3d(plan: dict, public_dir: Path, library: Path | None = None) -> dict:
    return stage_premium_3d_v101(plan, public_dir, library)
