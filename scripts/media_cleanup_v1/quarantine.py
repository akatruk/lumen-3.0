"""Quarantine / restore via manifest status. Never deletes files.

Dry-run is the default. Apply only writes status (+ optional history note).
Physical moves are opt-in and still refuse unstable files.
"""
from __future__ import annotations

import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from .stability import is_stable

HIDDEN = frozenset({"quarantined", "rejected"})


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"version": 1, "assets": data}
    return data


def save_manifest(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _history_append(asset: dict, action: str, reason: str) -> None:
    hist = asset.get("statusHistory")
    if not isinstance(hist, list):
        hist = []
    hist.append({"at": _now(), "action": action, "reason": reason, "from": asset.get("status")})
    asset["statusHistory"] = hist[-20:]


def set_status(
    manifest: dict,
    asset_ids: list[str],
    status: str,
    *,
    reason: str = "",
    library: Path | None = None,
    move_files: bool = False,
    quarantine_dir: str = "quarantine",
    require_stable: bool = True,
    min_age_sec: float = 120.0,
) -> dict:
    """Return a result dict. Mutates manifest assets in place."""
    by_id = {a["id"]: a for a in manifest.get("assets") or []}
    changed, skipped, errors = [], [], []
    for aid in asset_ids:
        asset = by_id.get(aid)
        if not asset:
            errors.append({"id": aid, "error": "not_in_manifest"})
            continue
        rel = asset.get("file") or ""
        if move_files and library is not None and rel:
            src = library / rel
            ok, why = (True, "skip_stable_check") if not require_stable else is_stable(
                src, min_age_sec=min_age_sec, settle_sec=1.0
            )
            if not ok:
                skipped.append({"id": aid, "reason": why})
                continue
            if status == "quarantined":
                dest = library / quarantine_dir / Path(rel).name
                dest.parent.mkdir(parents=True, exist_ok=True)
                if src.is_file() and not dest.exists():
                    shutil.move(str(src), str(dest))
                    asset["fileOriginal"] = asset.get("fileOriginal") or rel
                    asset["file"] = str(Path(quarantine_dir) / dest.name)
            elif status in {"active", "approved"} and asset.get("fileOriginal"):
                original = asset["fileOriginal"]
                src = library / rel
                dest = library / original
                dest.parent.mkdir(parents=True, exist_ok=True)
                if src.is_file():
                    shutil.move(str(src), str(dest))
                asset["file"] = original
        _history_append(asset, f"set:{status}", reason)
        asset["status"] = status
        if reason:
            asset["statusReason"] = reason
        changed.append(aid)
    return {
        "changed": changed,
        "skipped": skipped,
        "errors": errors,
        "status": status,
        "move_files": move_files,
    }


def quarantine_ids(manifest: dict, asset_ids: list[str], reason: str = "cleanup_v1", **kwargs) -> dict:
    return set_status(manifest, asset_ids, "quarantined", reason=reason, **kwargs)


def reject_ids(manifest: dict, asset_ids: list[str], reason: str = "cleanup_v1", **kwargs) -> dict:
    return set_status(manifest, asset_ids, "rejected", reason=reason, **kwargs)


def restore_ids(manifest: dict, asset_ids: list[str], reason: str = "restore_v1", **kwargs) -> dict:
    return set_status(manifest, asset_ids, "active", reason=reason, **kwargs)


def apply_review(
    manifest_path: Path,
    review: dict,
    *,
    dry_run: bool = True,
    library: Path | None = None,
    move_files: bool = False,
) -> dict:
    """Apply recommended quarantine from media-cleanup-review.json."""
    data = load_manifest(manifest_path)
    before = deepcopy(data)
    recommended = review.get("recommended_quarantine") or []
    ids = [row["id"] if isinstance(row, dict) else row for row in recommended]
    result = quarantine_ids(
        data,
        ids,
        reason="cleanup_v1_review",
        library=library,
        move_files=move_files and not dry_run,
    )
    result["dry_run"] = dry_run
    result["count"] = len(ids)
    if dry_run:
        result["would_change"] = result["changed"]
        result["changed"] = []
        # do not write
        return result
    # backup then write
    bak = manifest_path.with_suffix(manifest_path.suffix + f".bak-cleanup-{_now().replace(':', '')}")
    bak.write_text(json.dumps(before, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    save_manifest(manifest_path, data)
    result["backup"] = str(bak)
    return result


def is_searchable(asset: dict, *, include_hidden: bool = False) -> bool:
    if include_hidden:
        return True
    status = asset.get("status")
    if status in HIDDEN:
        return False
    return True
