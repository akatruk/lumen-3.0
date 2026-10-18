#!/usr/bin/env python3
"""Index Cinematic Environmental Background Factory V6 into the media manifest.

Indexes approved photoreal stills + I2V clips under motion/cinematic-env-v6/.
Does NOT promote V5 abstract pmv5_bg_* plates as environmental cinema.
Never overwrites status=approved binary masters from other sources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "recipes" / "cinematic-env-factory-v6-batch1.json"
MANIFEST = ROOT / "media" / "library" / "out" / "manifest.json"
STILLS_PLAN = ROOT / "media" / "library" / "plans" / "cinematic-env-v6-batch1.jsonl"
I2V_PLAN = ROOT / "media" / "library" / "plans" / "cinematic-env-v6-i2v-batch1.jsonl"
LIBRARY = ROOT / "media" / "library" / "out"


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def still_row(plan: dict, rel_file: str, digest: str | None, status: str) -> dict:
    return {
        "id": plan["id"],
        "type": "image",
        "category": "backgrounds",
        "tags": plan.get("tags") or [],
        "tags_ru": plan.get("tags_ru") or plan.get("tags") or [],
        "tags_zh": plan.get("tags_zh") or plan.get("tags") or [],
        "description": f"Cinematic env still {plan['domain']} — I2V-ready master",
        "description_ru": f"Кинематографичный фон {plan['domain']}",
        "description_zh": f"电影环境背景 {plan['domain']}",
        "file": rel_file,
        "aspectRatio": "9:16",
        "composition": plan.get("composition") or "speaker_safe",
        "background": "photographic",
        "qualityScore": 0.88 if status == "approved" else 0.7,
        "textSafe": True,
        "textSafeAreas": [plan.get("negative_space") or "left"],
        "source": "runpod",
        "visualFamily": "cinematic_environment",
        "status": status,
        "batch": "cinematic-env-v6-batch1",
        "domain": plan.get("domain"),
        "origin1Fit": bool(plan.get("origin1_fit")),
        "sceneRoles": ["background", "hero", "supporting_broll"],
        "energy": "balanced",
        "emotion": "editorial",
        "cameraMotion": plan.get("camera_motion"),
        "sha256": digest,
        "indexedAt": datetime.now(timezone.utc).isoformat(),
        "matchMode": "situational",
        "situations": [str(plan.get("domain") or "").lower(), "cinematic_environment"],
    }


def clip_row(plan: dict, still_plan: dict | None, rel_file: str, digest: str | None, status: str) -> dict:
    tags = list((still_plan or {}).get("tags") or [])
    if "video" not in tags:
        tags = tags + ["video", "i2v", "cinematic environment"]
    return {
        "id": plan["id"],
        "type": "video",
        "category": "backgrounds",
        "tags": tags,
        "tags_ru": list((still_plan or {}).get("tags_ru") or tags),
        "tags_zh": list((still_plan or {}).get("tags_zh") or tags),
        "description": f"Cinematic env I2V clip from {plan.get('source_still')} — {plan.get('camera_motion')}",
        "file": rel_file,
        "aspectRatio": "9:16",
        "composition": (still_plan or {}).get("composition") or "speaker_safe",
        "background": "photographic",
        "qualityScore": 0.9 if status == "approved" else 0.72,
        "textSafe": True,
        "textSafeAreas": [(still_plan or {}).get("negative_space") or "left"],
        "source": "runpod",
        "visualFamily": "cinematic_environment",
        "status": status,
        "batch": "cinematic-env-v6-batch1",
        "domain": plan.get("domain"),
        "origin1Fit": bool(plan.get("origin1_fit")),
        "sourceStill": plan.get("source_still"),
        "sceneRoles": ["background", "hero", "supporting_broll"],
        "energy": "medium",
        "emotion": "editorial",
        "cameraMotion": plan.get("camera_motion"),
        "loopable": False,
        "duration": float(plan.get("seconds") or 5),
        "fps": int(plan.get("fps") or 30),
        "width": 1080,
        "height": 1920,
        "sha256": digest,
        "indexedAt": datetime.now(timezone.utc).isoformat(),
        "matchMode": "situational",
        "situations": [str(plan.get("domain") or "").lower(), "cinematic_environment", "premium_background"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--recipe", type=Path, default=RECIPE)
    parser.add_argument("--library", type=Path, default=LIBRARY)
    parser.add_argument("--approved-ids", type=Path, help="JSON list of asset ids that passed QA")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    recipe = json.loads(args.recipe.read_text(encoding="utf-8"))
    stills = {p["id"]: p for p in load_jsonl(STILLS_PLAN)}
    i2v = load_jsonl(I2V_PLAN)
    approved: set[str] | None = None
    if args.approved_ids and args.approved_ids.is_file():
        approved = set(json.loads(args.approved_ids.read_text(encoding="utf-8")))

    rows: list[dict] = []
    for sid, plan in stills.items():
        rel = f"motion/cinematic-env-v6/stills/{sid}.png"
        path = args.library / rel
        digest = sha256_file(path)
        status = "approved" if (approved is None and digest) or (approved and sid in approved) else (
            "needs_review" if digest else "planned"
        )
        if approved is not None and sid not in approved and digest:
            status = "rejected"
        rows.append(still_row(plan, rel, digest, status if digest else "planned"))

    for plan in i2v:
        cid = plan["id"]
        rel = f"motion/cinematic-env-v6/clips/{cid}.mp4"
        path = args.library / rel
        digest = sha256_file(path)
        if approved is not None:
            status = "approved" if cid in approved and digest else ("rejected" if digest else "planned")
        else:
            status = "approved" if digest else "planned"
        rows.append(clip_row(plan, stills.get(plan.get("source_still")), rel, digest, status))

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    assets = list(manifest.get("assets") or [])
    by_id = {a.get("id"): i for i, a in enumerate(assets)}
    added = updated = skipped = 0
    for row in rows:
        aid = row["id"]
        if aid in by_id:
            prev = assets[by_id[aid]]
            if prev.get("status") == "approved" and prev.get("batch") != "cinematic-env-v6-batch1":
                skipped += 1
                continue
            assets[by_id[aid]] = {**prev, **row}
            updated += 1
        else:
            assets.append(row)
            by_id[aid] = len(assets) - 1
            added += 1

    manifest["assets"] = assets
    manifest["cinematicEnvFactoryV6"] = {
        "batch": "batch1",
        "recipe": str(args.recipe.relative_to(ROOT)),
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "gpu": recipe.get("policy", {}).get("gpu"),
        "indexedAt": datetime.now(timezone.utc).isoformat(),
        "note": "V5 abstract pmv5_bg_* kept but not promoted as environmental cinema",
    }
    print(
        json.dumps(
            {"added": added, "updated": updated, "skipped": skipped, "total": len(assets), "dryRun": args.dry_run},
            indent=2,
        )
    )
    if args.dry_run:
        return
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
