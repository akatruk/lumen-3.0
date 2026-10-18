#!/usr/bin/env python3
"""Index Capital Cinematic V7 after frame QA.

visualGrounding is taken only from the QA file (observed frames).
Intent stays on the plan. Duration is the ffprobe value, never a 6s claim.
Incomplete locales stay PENDING_LOCALIZATION. Human tags_ru/tags_zh are kept.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "media" / "library"))
sys.path.insert(0, str(ROOT))

from ingest import register_approved  # noqa: E402

RECIPE = ROOT / "recipes" / "cinematic-env-factory-v7-batch1.json"
MANIFEST = ROOT / "media" / "library" / "out" / "manifest.json"
STILLS_PLAN = ROOT / "media" / "library" / "plans" / "cinematic-env-v7-batch1.jsonl"
I2V_PLAN = ROOT / "media" / "library" / "plans" / "cinematic-env-v7-i2v-batch1.jsonl"
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


def localized_from(plan: dict) -> dict:
    title_en = plan.get("conceptId") or plan["id"]
    return {
        "en-US": {
            "title": title_en.replace(".", " "),
            "description": " ".join(plan.get("tags") or []),
            "terms": list(plan.get("tags") or []),
        },
        "ru-RU": {
            "title": " ".join((plan.get("tags_ru") or [])[:4]),
            "description": " ".join(plan.get("tags_ru") or []),
            "terms": list(plan.get("tags_ru") or []),
        },
        "zh-CN": {
            "title": " ".join((plan.get("tags_zh") or [])[:4]),
            "description": " ".join(plan.get("tags_zh") or []),
            "terms": list(plan.get("tags_zh") or []),
        },
    }


def keep_human_tags(prev: dict | None, row: dict) -> dict:
    if not prev:
        return row
    if prev.get("tagsAuthority") == "human":
        for key in ("tags", "tags_ru", "tags_zh", "localized"):
            if prev.get(key):
                row[key] = prev[key]
    return row


def base_row(plan: dict, rel: str, digest: str | None, status: str, grounding: dict | None, duration: float | None) -> dict:
    row = {
        "id": plan["id"],
        "type": "video" if plan.get("kind") == "i2v" else "image",
        "category": "backgrounds",
        "tags": list(plan.get("tags") or []),
        "tags_ru": list(plan.get("tags_ru") or []),
        "tags_zh": list(plan.get("tags_zh") or []),
        "description": f"Capital cinematic {plan.get('domain')} {plan['id']}",
        "file": rel,
        "aspectRatio": "9:16",
        "composition": plan.get("composition") or "speaker_safe",
        "background": "photographic",
        "qualityScore": 0.9 if status == "approved" else 0.4,
        "textSafe": True,
        "textSafeAreas": [plan.get("negative_space") or "left"],
        "source": "runpod",
        "visualFamily": "cinematic_environment",
        "status": status,
        "batch": "cinematic-env-v7-batch1",
        "domain": plan.get("domain"),
        "origin1Fit": bool(plan.get("origin1_fit")),
        "conceptId": plan.get("conceptId"),
        "sceneRoles": ["background", "hero", "supporting_broll"],
        "energy": "balanced",
        "emotion": "editorial",
        "cameraMotion": plan.get("camera_motion"),
        "sha256": digest,
        "indexedAt": datetime.now(timezone.utc).isoformat(),
        "matchMode": "situational",
        "situations": ["capital", "business", "cinematic_environment", str(plan.get("domain") or "").lower()],
        "intent": plan.get("intent") or {
            "concept": plan.get("prompt"),
            "camera": plan.get("camera_motion"),
            "sourceStill": plan.get("source_still"),
        },
        "visualGrounding": grounding or {},
        "supportedLocales": ["en-US", "ru-RU", "zh-CN"],
        "localized": localized_from(plan),
        "multilingualContract": "required",
    }
    if row["type"] == "video":
        row["loopable"] = False
        row["fps"] = None
        row["width"] = None
        row["height"] = None
        row["duration"] = duration
        row["durationPolicy"] = plan.get("duration_policy") or "ffprobe"
        row["nativeMotionClaim"] = "svd_xt_frames_not_6s_setpts"
        if "video" not in row["tags"]:
            row["tags"] = row["tags"] + ["video", "i2v"]
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--library", type=Path, default=LIBRARY)
    parser.add_argument("--qa", type=Path, required=True, help="QA json: decisions + visualGrounding + probe")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stills = load_jsonl(STILLS_PLAN)
    still_by_id = {row["id"]: row for row in stills}
    i2v = []
    for plan in load_jsonl(I2V_PLAN):
        parent = still_by_id.get(plan.get("source_still")) or {}
        merged = dict(plan)
        for key in ("tags", "tags_ru", "tags_zh", "composition", "negative_space", "intent"):
            if not merged.get(key) and parent.get(key):
                merged[key] = parent[key]
        if parent.get("intent"):
            merged["intent"] = {"sourceStillIntent": parent["intent"], "motion": plan.get("camera_motion"), "prompt": plan.get("prompt")}
        i2v.append(merged)
    qa = json.loads(args.qa.read_text(encoding="utf-8"))
    decisions = qa.get("decisions") or {}
    grounding = qa.get("visualGrounding") or {}
    probe = {row["id"]: row for row in (qa.get("probe") or [])}

    rows = []
    for plan in stills + i2v:
        aid = plan["id"]
        kind = "clips" if plan.get("kind") == "i2v" else "stills"
        ext = ".mp4" if kind == "clips" else ".png"
        rel = f"motion/cinematic-env-v7/{kind}/{aid}{ext}"
        path = args.library / rel
        digest = sha256_file(path)
        decision = decisions.get(aid) or "needs_review"
        if not digest:
            decision = "planned"
        elif decision not in {"approved", "rejected", "needs_review"}:
            decision = "needs_review"
        dur = None
        if aid in probe:
            dur = probe[aid].get("duration")
        row = base_row(plan, rel, digest, decision if digest or decision == "planned" else "planned", grounding.get(aid), dur)
        if aid in probe:
            row["width"] = probe[aid].get("width")
            row["height"] = probe[aid].get("height")
            row["fps"] = probe[aid].get("r_frame_rate")
            row["nbFrames"] = probe[aid].get("nb_frames")
        if decision == "approved" and digest:
            registered = register_approved(row)
            row["qualityStatus"] = registered.get("qualityStatus")
            row["contractErrors"] = registered.get("contractErrors")
            if row["qualityStatus"] != "production_ready":
                row["status"] = "needs_review"
        else:
            row["qualityStatus"] = "PENDING_LOCALIZATION" if decision != "rejected" else "rejected"
            if decision == "rejected":
                row["status"] = "rejected"
                row["qualityStatus"] = "rejected"
        rows.append(row)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    assets = list(manifest.get("assets") or [])
    by_id = {a.get("id"): i for i, a in enumerate(assets)}
    added = updated = skipped = 0
    for row in rows:
        aid = row["id"]
        if aid in by_id:
            prev = assets[by_id[aid]]
            if prev.get("batch") not in (None, "cinematic-env-v7-batch1") and not str(aid).startswith("cev7_"):
                skipped += 1
                continue
            if str(aid).startswith("cev6_"):
                skipped += 1
                continue
            assets[by_id[aid]] = keep_human_tags(prev, {**prev, **row})
            updated += 1
        else:
            assets.append(row)
            by_id[aid] = len(assets) - 1
            added += 1
    manifest["assets"] = assets
    approved = [r["id"] for r in rows if r.get("status") == "approved" and r.get("qualityStatus") == "production_ready"]
    manifest["cinematicEnvFactoryV7"] = {
        "batch": "batch1",
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "productionReady": approved,
        "indexedAt": datetime.now(timezone.utc).isoformat(),
        "note": "Durations are ffprobe. visualGrounding is observed, separate from intent.",
    }
    summary = {
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "productionReady": approved,
        "rejected": [r["id"] for r in rows if r.get("status") == "rejected"],
        "dryRun": args.dry_run,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.dry_run:
        return
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
