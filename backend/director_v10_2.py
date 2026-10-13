"""Director V10.2 — premium 3D V2 gate on V9 baseline.

Only qualityStatus=production_ready / gate.production_ready variants bind.
Hero bindings live in quality_gate_v2.json but stay inactive until allowlisted.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from . import director_v9

ROOT = Path(__file__).resolve().parent.parent
GATE_PATH = ROOT / "media" / "library" / "3d_factory" / "quality_gate_v2.json"
ALPHA_PNG = ROOT / "3d-library-v2" / "alpha_png"


def load_gate(path: Path | None = None) -> dict:
    p = path or GATE_PATH
    if not p.is_file():
        return {"production_ready": [], "sceneAllowlist": {}, "heroBindings": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def is_premium_ready(gate: dict, asset_id: str, motion: str) -> bool:
    vid = f"{asset_id}__{motion}"
    if vid in (gate.get("rejected") or []):
        return False
    return vid in set(gate.get("production_ready") or [])


def build_float(scene_id: str, binding: dict, gate: dict) -> dict | None:
    asset_id = binding["assetId"]
    motion = binding["motion"]
    if not is_premium_ready(gate, asset_id, motion):
        return None
    allow = (gate.get("sceneAllowlist") or {}).get(scene_id)
    if allow is not None and f"{asset_id}__{motion}" not in allow:
        return None
    seq = ALPHA_PNG / asset_id / motion
    if not seq.is_dir() or not any(seq.glob("frame_*.png")):
        return None
    n = len(sorted(seq.glob("frame_*.png")))
    return {
        "assetId": asset_id,
        "variantId": f"{asset_id}__{motion}",
        "motion": motion,
        "file": f"3d-library-v2/alpha_png/{asset_id}/{motion}",
        "background": "transparent",
        "display": "float",
        "family": "premium_3d",
        "format": "png_seq",
        "frameCount": n,
        "fps": 30,
        "scaleProfile": binding.get("scaleProfile") or "hero",
        "areaShare": float(binding.get("areaShare") or 0.26),
        "minPx": 380 if binding.get("scaleProfile") == "hero" else 280,
        "maxPx": 520 if binding.get("scaleProfile") == "hero" else 400,
        "placement": binding.get("placement") or "speaker_right_lower",
        "preferredPlacement": binding.get("placement"),
        "silhouette": asset_id,
        "qualityStatus": "production_ready",
        "factory": "v2",
    }


def apply_premium_3d_v102(plan: dict, *, seed: int | None = None) -> dict:
    del seed
    out = director_v9.apply_composition_intelligence(plan)
    gate = load_gate()
    heroes = gate.get("heroBindings") or {}
    bindings = []
    rejected = []
    scenes = []
    for scene in out.get("scenes") or []:
        scene = dict(scene)
        sid = scene.get("sceneId")
        binding = heroes.get(sid)
        if binding:
            picked = build_float(sid, binding, gate)
            if picked:
                comp = dict(scene.get("composition") or {})
                comp["floatObject"] = picked
                comp["secondaryVisual"] = "premium_3d"
                comp["suppressHero"] = True
                scene["composition"] = comp
                scene["heroObject"] = None
                fg = dict(scene.get("foreground") or {})
                fg.update({
                    "assetId": picked["assetId"],
                    "file": picked["file"],
                    "background": "transparent",
                    "family": "premium_3d",
                    "format": "png_seq",
                })
                scene["foreground"] = fg
                sm = dict(scene.get("semanticMotion") or {})
                sm["display"] = "omit"
                sm.pop("staged", None)
                scene["semanticMotion"] = sm
                bindings.append({"sceneId": sid, **picked})
            else:
                rejected.append({
                    "sceneId": sid,
                    "variantId": f"{binding['assetId']}__{binding['motion']}",
                    "reason": "not_production_ready_or_missing_png",
                })
        scenes.append(scene)
    out["scenes"] = scenes
    out["shotPlanVersion"] = "v10.2"
    out["compositionPolicy"] = "v9_clean"
    out["premium3d"] = {
        "policy": "v10.2_quality_gate",
        "bindings": bindings,
        "rejected": rejected,
        "boundCount": len(bindings),
        "productionReady": list(gate.get("production_ready") or []),
        "pass": True,
        "deliveryFormat": "png_seq",
        "factory": "v2",
    }
    return out


def stage_premium_3d_v102(plan: dict, public_dir: Path, library: Path | None = None) -> dict:
    picked_root = Path(public_dir) / "picked"
    picked_root.mkdir(parents=True, exist_ok=True)
    out = dict(plan)
    scenes = []
    for scene in out.get("scenes") or []:
        scene = dict(scene)
        comp = dict(scene.get("composition") or {})
        fo = dict(comp.get("floatObject") or {})
        if fo.get("format") != "png_seq" or fo.get("factory") != "v2":
            scenes.append(scene)
            continue
        src = ALPHA_PNG / fo["assetId"] / fo["motion"]
        dest = picked_root / f"{fo['assetId']}_{fo['motion']}"
        if src.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            fo["staged"] = f"picked/{dest.name}"
            fo["frameCount"] = len(sorted(dest.glob("frame_*.png")))
            comp["floatObject"] = fo
            scene["composition"] = comp
            fg = dict(scene.get("foreground") or {})
            fg["staged"] = fo["staged"]
            fg["format"] = "png_seq"
            scene["foreground"] = fg
        scenes.append(scene)
    out["scenes"] = scenes
    return director_v9.stage_float_objects(out, public_dir, library)


def apply_premium_3d(plan: dict, *, seed: int | None = None) -> dict:
    return apply_premium_3d_v102(plan, seed=seed)


def stage_premium_3d(plan: dict, public_dir: Path, library: Path | None = None) -> dict:
    return stage_premium_3d_v102(plan, public_dir, library)
