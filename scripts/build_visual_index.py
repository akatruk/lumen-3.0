"""Probe the production library and write a staged visual index.

Frame text is copied only from an existing visualGrounding field. Other rows
stay unreviewed. The script does not delete media and does not replace
manifest.json. It writes visual-index.staged.json, then renames it onto
visual-index.json and keeps the previous file as visual-index.previous.json.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/volume_nyc1_1791446889637/app-library")
MANIFEST = ROOT / "manifest.json"
STAGED = ROOT / "visual-index.staged.json"
LIVE = ROOT / "visual-index.json"
PREVIOUS = ROOT / "visual-index.previous.json"
PLAYABLE = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mov", ".svg"}
SKIP_PARTS = ("thumbnail", "contact-sheet", "contact_sheet", "/models/", "weights")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    if path.suffix.lower() == ".svg":
        return {"width": None, "height": None, "duration": None, "fps": None, "corrupt": False}
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=width,height,codec_type,avg_frame_rate,r_frame_rate",
        "-of", "json", str(path),
    ]
    try:
        raw = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return {"corrupt": True, "error": "ffprobe_timeout"}
    if raw.returncode != 0:
        return {"corrupt": True, "error": (raw.stderr or "ffprobe_failed")[:180]}
    data = json.loads(raw.stdout or "{}")
    streams = data.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), streams[0] if streams else {})
    rate = video.get("avg_frame_rate") or video.get("r_frame_rate") or ""
    fps = None
    if isinstance(rate, str) and "/" in rate:
        num, den = rate.split("/", 1)
        if den not in ("0", ""):
            fps = round(float(num) / float(den), 3)
    duration = (data.get("format") or {}).get("duration")
    return {
        "width": video.get("width"),
        "height": video.get("height"),
        "duration": float(duration) if duration else None,
        "fps": fps,
        "corrupt": False,
    }


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = manifest["assets"] if isinstance(manifest, dict) else manifest
    rows = {}
    summary = {
        "manifest": len(assets),
        "playable": 0,
        "excluded": 0,
        "missing": 0,
        "corrupt": 0,
        "stub": 0,
        "frameReviewed": 0,
        "unreviewed": 0,
        "bytes": 0,
    }
    failures = []
    for asset in assets:
        asset_id = asset.get("id")
        rel = asset.get("file") or ""
        path = ROOT / rel
        suffix = Path(rel).suffix.lower()
        row = {
            "id": asset_id,
            "file": rel,
            "type": asset.get("type"),
            "status": "unreviewed",
            "frameReviewed": False,
            "visible": None,
            "kind": "contextual" if asset.get("type") in ("image", "video") else asset.get("type"),
            "support": [],
            "exclude": {},
            "retrieval": {},
            "exclusionReason": None,
        }
        lowered = rel.lower()
        if suffix == ".tsx" or rel.startswith("motion/src/") or rel.endswith("scenes.tsx"):
            row["status"] = "excluded"
            row["exclusionReason"] = "component_stub"
            summary["stub"] += 1
            summary["excluded"] += 1
        elif any(part in lowered for part in SKIP_PARTS):
            row["status"] = "excluded"
            row["exclusionReason"] = "not_usable_media"
            summary["excluded"] += 1
        elif suffix not in PLAYABLE:
            row["status"] = "excluded"
            row["exclusionReason"] = f"unsupported_format:{suffix or 'none'}"
            summary["excluded"] += 1
        elif not path.is_file():
            row["status"] = "excluded"
            row["exclusionReason"] = "missing_file"
            summary["missing"] += 1
            summary["excluded"] += 1
            failures.append({"id": asset_id, "reason": "missing_file", "file": rel})
        else:
            info = probe(path)
            row.update(info)
            if info.get("corrupt"):
                row["status"] = "excluded"
                row["exclusionReason"] = "corrupt"
                summary["corrupt"] += 1
                summary["excluded"] += 1
                failures.append({"id": asset_id, "reason": info.get("error") or "corrupt", "file": rel})
            else:
                row["bytes"] = path.stat().st_size
                row["sha256"] = sha256(path)
                summary["bytes"] += row["bytes"]
                summary["playable"] += 1
                grounding = asset.get("visualGrounding")
                observed = ""
                if isinstance(grounding, dict) and grounding.get("reviewed") is True:
                    observed = str(grounding.get("observed") or "").strip()
                elif isinstance(grounding, str):
                    observed = grounding.strip()
                if observed:
                    row["frameReviewed"] = True
                    row["status"] = "described"
                    row["visible"] = observed
                    row["visibleSource"] = "visualGrounding"
                    summary["frameReviewed"] += 1
                else:
                    summary["unreviewed"] += 1
                    row["catalogDescription"] = asset.get("description")
                    row["descriptionSource"] = "manifest_unverified"
        if asset.get("status") in ("rejected", "quarantined", "duplicate", "corrupt"):
            row["status"] = "excluded"
            row["exclusionReason"] = "manifest_" + str(asset.get("status"))
            row["frameReviewed"] = False
        rows[asset_id] = row
    payload = {
        "version": "visual-index-v1",
        "builtAt": datetime.now(timezone.utc).isoformat(),
        "library": str(ROOT),
        "summary": summary,
        "failures": failures,
        "assets": rows,
    }
    STAGED.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    if LIVE.is_file():
        LIVE.replace(PREVIOUS)
    STAGED.replace(LIVE)
    print(json.dumps({"summary": summary, "failures": len(failures), "index": str(LIVE)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
