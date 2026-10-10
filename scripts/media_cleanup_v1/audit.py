"""Inventory + quality + duplicate analysis for the media library."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .classify import QUALITY_ORDER, classify_asset, pick_best
from .hashes import hamming, phash_asset_file, sha256_file
from .stability import recent_writes


def load_assets(manifest_path: Path) -> list[dict]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return data["assets"] if isinstance(data, dict) else data


def inventory(library: Path, assets: list[dict]) -> dict:
    by_type: Counter = Counter()
    by_cat: Counter = Counter()
    by_src: Counter = Counter()
    by_status: Counter = Counter()
    present = missing = 0
    missing_ids = []
    for asset in assets:
        by_type[asset.get("type") or "?"] += 1
        by_cat[asset.get("category") or "?"] += 1
        by_src[asset.get("source") or "?"] += 1
        by_status[asset.get("status") or "active"] += 1
        path = library / (asset.get("file") or "")
        if asset.get("file") and path.is_file():
            present += 1
        else:
            missing += 1
            missing_ids.append(asset.get("id"))
    disk_files = sum(1 for p in library.rglob("*") if p.is_file())
    return {
        "manifest_assets": len(assets),
        "files_present": present,
        "files_missing": missing,
        "missing_ids": missing_ids,
        "disk_files_total": disk_files,
        "by_type": dict(by_type.most_common()),
        "by_category": dict(by_cat.most_common()),
        "by_source": dict(by_src.most_common()),
        "by_status": dict(by_status.most_common()),
        "library": str(library),
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def run_audit(
    library: Path,
    *,
    manifest_path: Path | None = None,
    phash_threshold: int = 10,
    frame_dir: Path | None = None,
    limit: int | None = None,
) -> dict:
    manifest_path = manifest_path or (library / "manifest.json")
    assets = load_assets(manifest_path)
    if limit:
        assets = assets[:limit]
    inv = inventory(library, assets)
    frame_dir = frame_dir or (library / "contact-sheets" / "cleanup" / "_frames")
    frame_dir.mkdir(parents=True, exist_ok=True)

    quality_reports = []
    quality_by_id = {}
    sha_groups: dict[str, list[str]] = defaultdict(list)
    phash_by_id: dict[str, str] = {}
    asset_by_id = {a["id"]: a for a in assets}

    for asset in assets:
        q = classify_asset(library, asset)
        quality_reports.append(q.to_dict())
        quality_by_id[asset["id"]] = q
        path = library / (asset.get("file") or "")
        if path.is_file():
            digest = sha256_file(path)
            if digest:
                sha_groups[digest].append(asset["id"])
            ph = phash_asset_file(path, frame_dir=frame_dir)
            if ph:
                phash_by_id[asset["id"]] = ph

    # Exact duplicates
    exact_dupes = []
    for digest, ids in sorted(sha_groups.items(), key=lambda kv: -len(kv[1])):
        if len(ids) < 2:
            continue
        members = [asset_by_id[i] for i in ids if i in asset_by_id]
        best = pick_best(members, quality_by_id)
        exact_dupes.append({
            "sha256": digest,
            "ids": ids,
            "recommend_keep": best,
            "recommend_quarantine": [i for i in ids if i != best],
            "kind": "exact_sha256",
        })

    # Perceptual near-duplicates (greedy clustering)
    ids_with_hash = list(phash_by_id.keys())
    used = set()
    near_dupes = []
    for i, aid in enumerate(ids_with_hash):
        if aid in used:
            continue
        cluster = [aid]
        ha = phash_by_id[aid]
        for bid in ids_with_hash[i + 1:]:
            if bid in used:
                continue
            if hamming(ha, phash_by_id[bid]) <= phash_threshold:
                cluster.append(bid)
        if len(cluster) < 2:
            continue
        for cid in cluster:
            used.add(cid)
        members = [asset_by_id[c] for c in cluster if c in asset_by_id]
        best = pick_best(members, quality_by_id)
        near_dupes.append({
            "phash_seed": ha,
            "ids": cluster,
            "recommend_keep": best,
            "recommend_quarantine": [c for c in cluster if c != best],
            "kind": "perceptual",
            "threshold": phash_threshold,
        })

    quality_counts = Counter(r["quality"] for r in quality_reports)

    # Quarantine recommendations (do not apply)
    recommend = []
    seen = set()

    def add_rec(aid: str, reason: str, quality: str):
        if aid in seen:
            return
        seen.add(aid)
        recommend.append({
            "id": aid,
            "reason": reason,
            "quality": quality,
            "file": (asset_by_id.get(aid) or {}).get("file"),
        })

    for r in quality_reports:
        if r["quality"] == "LOW":
            add_rec(r["id"], "low_quality:" + ",".join(r.get("reasons") or []), "LOW")
        elif r["quality"] == "LEGACY" and r.get("missing"):
            add_rec(r["id"], "legacy_missing", "LEGACY")

    for group in exact_dupes:
        for aid in group["recommend_quarantine"]:
            add_rec(aid, f"exact_duplicate_of:{group['recommend_keep']}", quality_by_id[aid].quality)

    # Near-dupes: only recommend quarantine when keep is clearly better quality
    for group in near_dupes:
        keep_q = QUALITY_ORDER.get(quality_by_id[group["recommend_keep"]].quality, 0)
        for aid in group["recommend_quarantine"]:
            other_q = QUALITY_ORDER.get(quality_by_id[aid].quality, 0)
            if keep_q > other_q or quality_by_id[aid].quality == "LOW":
                add_rec(aid, f"near_duplicate_of:{group['recommend_keep']}", quality_by_id[aid].quality)

    recent = recent_writes(library, minutes=30.0)
    unstable_ids = []
    for asset in assets:
        rel = asset.get("file") or ""
        if rel in recent or any(rel and r.endswith(Path(rel).name) for r in recent):
            unstable_ids.append(asset["id"])

    review = {
        "version": 1,
        "generated_at": inv["at"],
        "library": str(library),
        "manifest": str(manifest_path),
        "dry_run": True,
        "inventory": inv,
        "quality_counts": dict(quality_counts),
        "exact_duplicate_groups": exact_dupes,
        "perceptual_duplicate_groups": near_dupes,
        "recommended_quarantine": recommend,
        "recommended_quarantine_count": len(recommend),
        "unstable_recent_writes_30m": recent,
        "unstable_asset_ids": unstable_ids,
        "note": "FIRST PASS DRY RUN — status changes not applied. Preserve asset ids.",
        "assets": [
            {
                "id": a["id"],
                "file": a.get("file"),
                "type": a.get("type"),
                "category": a.get("category"),
                "source": a.get("source"),
                "status": a.get("status") or "active",
                "quality": quality_by_id[a["id"]].quality,
                "reasons": quality_by_id[a["id"]].reasons,
                "sha256": next((d for d, ids in sha_groups.items() if a["id"] in ids), None),
                "phash": phash_by_id.get(a["id"]),
                "width": quality_by_id[a["id"]].width,
                "height": quality_by_id[a["id"]].height,
                "bytes": quality_by_id[a["id"]].bytes,
            }
            for a in assets
        ],
    }
    return review


def write_inventory_md(review: dict, dest: Path) -> None:
    inv = review["inventory"]
    qc = review.get("quality_counts") or {}
    lines = [
        "# Media library inventory",
        "",
        f"Generated: `{review.get('generated_at')}`",
        f"Library: `{inv.get('library')}`",
        "",
        "## Counts",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Manifest assets | {inv['manifest_assets']} |",
        f"| Files present | {inv['files_present']} |",
        f"| Files missing | {inv['files_missing']} |",
        f"| Disk files (all) | {inv['disk_files_total']} |",
        f"| Exact SHA duplicate groups | {len(review.get('exact_duplicate_groups') or [])} |",
        f"| Perceptual duplicate groups | {len(review.get('perceptual_duplicate_groups') or [])} |",
        f"| Recommended quarantine (dry-run) | {review.get('recommended_quarantine_count', 0)} |",
        "",
        "## By type",
        "",
        "| Type | Count |",
        "| --- | ---: |",
    ]
    for k, v in (inv.get("by_type") or {}).items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## By source", "", "| Source | Count |", "| --- | ---: |"]
    for k, v in (inv.get("by_source") or {}).items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## By category", "", "| Category | Count |", "| --- | ---: |"]
    for k, v in (inv.get("by_category") or {}).items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Quality (CPU)", "", "| Tier | Count |", "| --- | ---: |"]
    for tier in ("PREMIUM", "GOOD", "ACCEPTABLE", "LOW", "LEGACY", "UNCERTAIN"):
        lines.append(f"| {tier} | {qc.get(tier, 0)} |")
    if inv.get("missing_ids"):
        lines += ["", "## Missing files (ids)", "", ", ".join(f"`{i}`" for i in inv["missing_ids"])]
    lines += ["", "## Status", "", "Dry-run only. No production status mass-apply.", ""]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
