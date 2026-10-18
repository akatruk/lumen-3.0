"""Stage a versioned library manifest, then switch it atomically.

Reads the manifest the Director searches (media/library/out/manifest.json,
which on lumen-fix is the app-library volume). Adds accepted clips that are
already on disk. Does not delete media. Rejected pictures stay out of the
active set. Assets without a frame review are listed, not described.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

VERSION = "visual-index-20261018a"
ROOT = Path(__file__).resolve().parents[1]
REVIEWS = ROOT / "backend" / "visual_reviews.json"


def _load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"version": 1, "assets": data}
    return data


def _relative(asset_id: str, source: str) -> str:
    if source == "runpod-sdxl-svd":
        return f"re-residency/ai/{asset_id}.mp4"
    return f"re-residency/clips/{asset_id}.mp4"


def _row(asset: dict, relative: str) -> dict:
    row = dict(asset)
    row["file"] = relative
    row["status"] = "active"
    row["qualityStatus"] = row.get("qualityStatus") or "reviewed_local"
    row.pop("library", None)
    return row


def stage(library: Path, accepted: Path) -> tuple[dict, dict]:
    current_path = library / "manifest.json"
    current = _load(current_path)
    reviews = json.loads(REVIEWS.read_text(encoding="utf-8"))["assets"]
    incoming = json.loads(accepted.read_text(encoding="utf-8"))
    by_id = {asset.get("id"): asset for asset in current.get("assets") or []}
    report = {
        "version": VERSION,
        "added": [],
        "updated": [],
        "excluded": [],
        "unreviewed": [],
    }
    for asset in incoming.get("assets") or []:
        asset_id = asset.get("id")
        review = reviews.get(asset_id) or {}
        if review.get("status") == "rejected":
            report["excluded"].append({"id": asset_id, "reason": "rejected picture"})
            continue
        relative = _relative(asset_id, str(asset.get("source") or ""))
        if not (library / relative).is_file():
            report["excluded"].append({"id": asset_id, "reason": "file missing at " + relative})
            continue
        row = _row(asset, relative)
        if asset_id in by_id:
            by_id[asset_id] = {**by_id[asset_id], **row}
            report["updated"].append(asset_id)
        else:
            by_id[asset_id] = row
            report["added"].append(asset_id)
    for asset_id, review in reviews.items():
        if review.get("status") != "rejected":
            continue
        if asset_id in by_id and by_id[asset_id].get("status") != "rejected":
            # Keep the bytes. Search already hides status=rejected.
            if asset_id.startswith("re_neg_"):
                by_id[asset_id]["status"] = "rejected"
                by_id[asset_id]["qualityStatus"] = "rejected"
    assets = list(by_id.values())
    for asset in assets:
        asset_id = asset.get("id")
        rel = str(asset.get("file") or "")
        review = reviews.get(asset_id)
        if rel.endswith(".tsx") or rel.startswith("motion/src/"):
            report["excluded"].append({"id": asset_id, "reason": "tsx stub"})
            continue
        if not review:
            report["unreviewed"].append({"id": asset_id, "reason": "no frame review in this pass"})
        elif review.get("status") == "rejected":
            report["excluded"].append({"id": asset_id, "reason": "reviewed picture rejected: " + ",".join(review.get("marks") or [])})
    staged = dict(current)
    staged["assets"] = assets
    staged["visualIndex"] = {
        "version": VERSION,
        "acceptedAdded": report["added"],
        "unreviewedCount": len(report["unreviewed"]),
        "excludedCount": len(report["excluded"]),
    }
    report["assetCount"] = len(assets)
    report["previousCount"] = len(current.get("assets") or [])
    return staged, report


def publish(library: Path, staged: dict, report: dict) -> Path:
    folder = library / "indexes" / VERSION
    folder.mkdir(parents=True, exist_ok=True)
    previous = library / "manifest.json"
    backup = folder / "manifest-previous.json"
    if previous.is_file() and not backup.is_file():
        backup.write_bytes(previous.read_bytes())
    staged_path = folder / "manifest.json"
    payload = json.dumps(staged, ensure_ascii=False, indent=2) + "\n"
    staged_path.write_text(payload, encoding="utf-8")
    (folder / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Verify before the switch: every added id is present, negatives are not active.
    check = json.loads(staged_path.read_text(encoding="utf-8"))
    ids = {asset.get("id"): asset for asset in check["assets"]}
    missing = [asset_id for asset_id in report["added"] if asset_id not in ids]
    active_negatives = [
        asset_id for asset_id, asset in ids.items()
        if str(asset_id).startswith("re_neg_") and asset.get("status") != "rejected"
    ]
    if missing or active_negatives or check.get("visualIndex", {}).get("version") != VERSION:
        raise SystemExit(f"index verify failed missing={missing} negatives={active_negatives}")
    temporary = library / "manifest.json.staged"
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, previous)
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--accepted", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    staged, report = stage(args.library, args.accepted)
    print(json.dumps({
        "version": VERSION,
        "previousCount": report["previousCount"],
        "assetCount": report["assetCount"],
        "added": report["added"],
        "updated": report["updated"],
        "excluded": report["excluded"],
        "unreviewedCount": len(report["unreviewed"]),
    }, ensure_ascii=False, indent=2))
    if args.apply:
        backup = publish(args.library, staged, report)
        print("backup", backup)


if __name__ == "__main__":
    main()
