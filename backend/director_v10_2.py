"""Director V10.2 — premium 3D V2 gate on V9 baseline.

Only qualityStatus=production_ready / gate.production_ready variants bind.
Hero bindings live in quality_gate_v2.json but stay inactive until allowlisted.

Experimental (test-only) path: PREMIUM_3D_MODE=experimental binds l3d_v2_*
PNG sequences only when speech/concepts semantically match. Never mutates
production_ready. No speech match → NO_RELEVANT_3D_ASSET (V9-equivalent).
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from . import director_v9

ROOT = Path(__file__).resolve().parent.parent
GATE_PATH = ROOT / "media" / "library" / "3d_factory" / "quality_gate_v2.json"
ALPHA_PNG = ROOT / "3d-library-v2" / "alpha_png"

# Speech / concept → V2 asset. Strict: immigration/docs only — not investment finance.
_EXPERIMENTAL_SPEECH_MATCHES: tuple[dict[str, Any], ...] = (
    {
        "concept": "passport",
        "assetId": "l3d_v2_passport",
        "motion": "passport_open",
        "patterns": (
            r"\bpassport\b",
            r"\bvisa\b",
            r"\bresiden(?:ce|cy)\b",
            r"\bimmigration\b",
            r"\bcitizenship\b",
            r"\bпереезд\b",
            r"\bпаспорт\b",
            r"\bвиз[аыуе]\b",
            r"\bВНЖ\b",
        ),
        "keywordIds": ("passport", "residency", "relocation"),
    },
    {
        "concept": "suitcase",
        "assetId": "l3d_v2_suitcase",
        "motion": "suitcase_roll",
        "patterns": (
            r"\bsuitcase\b",
            r"\bluggage\b",
            r"\brelocati(?:on|ng)\b",
            r"\bmoving abroad\b",
            r"\bpack(?:ing)? (?:bags|suitcase)\b",
            r"\bчемодан\b",
        ),
        "keywordIds": ("relocation", "family"),
    },
    {
        "concept": "documents",
        "assetId": "l3d_v2_folder",
        "motion": "folder_open",
        "patterns": (
            r"\bdocuments?\b",
            r"\bpaperwork\b",
            r"\bapplication (?:form|desk|file)\b",
            r"\bfolder\b",
            r"\bдокумент",
            r"\bпапк",
        ),
        # Do NOT treat generic "structure" / "investment" / "shareholder" as documents.
        "keywordIds": ("documents", "program", "consult"),
    },
)

_SCENE_PRIORITY = ("problem", "payoff", "steps", "context", "residency", "consult", "hook")


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


def _png_seq_meta(asset_id: str, motion: str) -> tuple[Path, int] | None:
    seq = ALPHA_PNG / asset_id / motion
    if not seq.is_dir():
        return None
    frames = sorted(seq.glob("frame_*.png"))
    if not frames:
        return None
    return seq, len(frames)


def collect_speech_corpus(plan: dict) -> str:
    """Join real speech only — transcript + speech-backed headlines.

    Deliberately omits shotPlan keyword ids / floatObject.keyword so immigration
    defaults cannot fake a match for unrelated finance speech.
    """
    chunks: list[str] = []
    for row in plan.get("transcript") or []:
        if isinstance(row, dict):
            for key in ("original", "en", "ru", "zh", "text"):
                val = row.get(key)
                if val:
                    chunks.append(str(val))
        elif isinstance(row, str):
            chunks.append(row)
    for scene in plan.get("scenes") or []:
        typ = scene.get("typography") or {}
        for key in ("headline", "title", "subtitle"):
            if typ.get(key):
                chunks.append(str(typ[key]))
        exe = scene.get("execution") or {}
        # Prefer speech caption mode headlines; skip stock criteria card dumps if empty transcript.
        if exe.get("captionMode") == "speech" or plan.get("transcript"):
            for key in ("headline", "caption"):
                if exe.get(key):
                    chunks.append(str(exe[key]))
    return " ".join(chunks).lower()


def match_experimental_v2_assets(corpus: str, *, keyword_ids: set[str] | None = None) -> list[dict]:
    """Return speech-matched V2 candidates. Empty → NO_RELEVANT_3D_ASSET."""
    del keyword_ids  # speech patterns only; keywords are not authoritative
    text = (corpus or "").lower()
    hits: list[dict] = []
    for row in _EXPERIMENTAL_SPEECH_MATCHES:
        pattern_hit = any(re.search(p, text, re.I) for p in row["patterns"])
        if not pattern_hit:
            continue
        meta = _png_seq_meta(row["assetId"], row["motion"])
        if not meta:
            continue
        _, n = meta
        hits.append({
            "concept": row["concept"],
            "assetId": row["assetId"],
            "motion": row["motion"],
            "variantId": f"{row['assetId']}__{row['motion']}",
            "frameCount": n,
            "match": "speech_pattern",
        })
    return hits


def build_float_experimental(scene_id: str, binding: dict) -> dict | None:
    """Build float without consulting production_ready (test-only override)."""
    del scene_id
    asset_id = binding["assetId"]
    motion = binding["motion"]
    meta = _png_seq_meta(asset_id, motion)
    if not meta:
        return None
    _, n = meta
    scale = binding.get("scaleProfile") or "hero"
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
        "scaleProfile": scale,
        "areaShare": float(binding.get("areaShare") or 0.26),
        "minPx": 380 if scale == "hero" else 280,
        "maxPx": 520 if scale == "hero" else 400,
        "placement": binding.get("placement") or "speaker_right_lower",
        "preferredPlacement": binding.get("placement"),
        "silhouette": asset_id,
        "qualityStatus": "experimental_override",
        "factory": "v2",
        "concept": binding.get("concept"),
    }


def build_float(scene_id: str, binding: dict, gate: dict) -> dict | None:
    asset_id = binding["assetId"]
    motion = binding["motion"]
    if not is_premium_ready(gate, asset_id, motion):
        return None
    allow = (gate.get("sceneAllowlist") or {}).get(scene_id)
    if allow is not None and f"{asset_id}__{motion}" not in allow:
        return None
    meta = _png_seq_meta(asset_id, motion)
    if not meta:
        return None
    _, n = meta
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


def apply_premium_3d_experimental(plan: dict, *, seed: int | None = None) -> dict:
    """Test-only: bind l3d_v2 PNG seqs when speech matches; else V9-equivalent.

    Does not write quality_gate_v2.production_ready. Face-safe placements only;
    no force-bind of immigration assets onto unrelated finance speech.
    """
    del seed
    out = director_v9.apply_composition_intelligence(plan)
    # Prefer explicit transcript on plan; enrich_plan may have stamped headlines already.
    corpus = collect_speech_corpus({**out, "transcript": plan.get("transcript") or out.get("transcript")})
    hits = match_experimental_v2_assets(corpus)
    gate = load_gate()  # read-only; production_ready must stay empty for prod
    if not hits:
        out["shotPlanVersion"] = "v10.2"
        out["compositionPolicy"] = "v9_clean"
        out["premium3d"] = {
            "policy": "experimental_speech_match",
            "bindings": [],
            "rejected": [],
            "boundCount": 0,
            "status": "NO_RELEVANT_3D_ASSET",
            "speechCorpusChars": len(corpus),
            "productionReady": list(gate.get("production_ready") or []),
            "pass": True,
            "deliveryFormat": "png_seq",
            "factory": "v2",
            "note": "No passport/suitcase/documents speech match — V9 floats retained",
        }
        return out

    scene_ids = [s.get("sceneId") for s in (out.get("scenes") or [])]
    bind_slots: list[tuple[str, dict]] = []
    for hit in hits:
        # Prefer narrative scenes over hook; avoid double-binding same asset.
        slot = next((sid for sid in _SCENE_PRIORITY if sid in scene_ids and sid not in {b[0] for b in bind_slots}), None)
        if not slot:
            slot = next((sid for sid in scene_ids if sid not in {b[0] for b in bind_slots}), None)
        if not slot:
            break
        bind_slots.append((slot, {
            "assetId": hit["assetId"],
            "motion": hit["motion"],
            "concept": hit["concept"],
            "scaleProfile": "hero" if hit["concept"] != "documents" else "supporting",
            "areaShare": 0.26 if hit["concept"] != "documents" else 0.2,
            "placement": "speaker_right_lower" if hit["concept"] == "passport" else "speaker_left_lower",
        }))

    bindings = []
    rejected = []
    scenes = []
    by_slot = {sid: binding for sid, binding in bind_slots}
    for scene in out.get("scenes") or []:
        scene = dict(scene)
        sid = scene.get("sceneId")
        binding = by_slot.get(sid)
        if binding:
            picked = build_float_experimental(sid, binding)
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
                    "reason": "missing_png_seq",
                })
        scenes.append(scene)
    out["scenes"] = scenes
    out["shotPlanVersion"] = "v10.2"
    out["compositionPolicy"] = "v9_clean"
    out["premium3d"] = {
        "policy": "experimental_speech_match",
        "bindings": bindings,
        "rejected": rejected,
        "boundCount": len(bindings),
        "status": "BOUND" if bindings else "NO_RELEVANT_3D_ASSET",
        "matchedConcepts": [h["concept"] for h in hits],
        "speechCorpusChars": len(corpus),
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
