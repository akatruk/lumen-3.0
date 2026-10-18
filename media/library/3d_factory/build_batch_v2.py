#!/usr/bin/env python3
"""Build Lumen 3D Factory V2 — Blender → RGBA PNG → ProRes 4444 + registry rows."""
from __future__ import annotations

import argparse
import json
import subprocess
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FACTORY = Path(__file__).resolve().parent / "blender_factory_v2.py"
CATALOG = Path(__file__).resolve().parent / "catalog_v2.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def encode_prores(png_dir: Path, dest: Path, fps: int = 30) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    pattern = str(png_dir / "frame_%04d.png")
    # Blender writes frame_0001.png via filepath frame_
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", pattern,
        "-c:v", "prores_ks",
        "-profile:v", "4444",
        "-pix_fmt", "yuva444p10le",
        "-an",
        str(dest),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"ok": False, "error": r.stderr[-500:]}
    probe = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=pix_fmt,codec_name,width,height", "-of", "csv=p=0", str(dest)],
        text=True,
    ).strip()
    return {"ok": True, "pix": probe, "bytes": dest.stat().st_size, "sha256": sha256(dest)}


def alpha_bbox_coverage(png_dir: Path, sample_frame: int = 60) -> dict:
    from PIL import Image
    p = png_dir / f"frame_{sample_frame:04d}.png"
    if not p.is_file():
        frames = sorted(png_dir.glob("frame_*.png"))
        if not frames:
            return {"ok": False}
        p = frames[len(frames) // 2]
    im = Image.open(p).convert("RGBA")
    a = im.split()[-1]
    bbox = a.getbbox()
    w, h = im.size
    if not bbox:
        return {"ok": False, "coverage": 0}
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    return {
        "ok": True,
        "coverage": round((bw * bh) / (w * h), 4),
        "bbox": list(bbox),
        "canvas": [w, h],
        "cornerAlpha": im.getpixel((2, 2))[3],
    }


def run_blender(asset: str, motion: str, out: Path, frames: int, engine: str) -> None:
    cmd = [
        "blender", "-b", "--python", str(FACTORY), "--",
        "--asset", asset,
        "--motion", motion,
        "--out", str(out),
        "--frames", str(frames),
        "--engine", engine,
    ]
    print("RUN", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    combined = (r.stdout or "") + "\n" + (r.stderr or "")
    print(combined[-2500:], flush=True)
    png_dir = out / "alpha_png" / asset / motion
    n = len(list(png_dir.glob("frame_*.png"))) if png_dir.is_dir() else 0
    ok_marker = '"ok": true' in combined
    if r.returncode != 0 or (not ok_marker and n < max(10, frames // 4)):
        raise SystemExit(
            f"blender failed for {asset}/{motion}: code={r.returncode} frames={n}\n{combined[-2000:]}"
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "3d-library-v2")
    ap.add_argument("--only", nargs="*", default=None, help="assetId__motion filters")
    ap.add_argument("--hero-only", action="store_true", help="passport_open, suitcase_roll, folder_open")
    ap.add_argument("--frames", type=int, default=120)
    ap.add_argument("--engine", default="EEVEE")
    ap.add_argument("--skip-blender", action="store_true")
    args = ap.parse_args()

    catalog = json.loads(CATALOG.read_text())
    jobs = []
    for obj in catalog["objects"]:
        for motion in obj["motions"]:
            jobs.append((obj["assetId"], motion, obj))

    if args.hero_only:
        heroes = {
            ("l3d_v2_passport", "passport_open"),
            ("l3d_v2_suitcase", "suitcase_roll"),
            ("l3d_v2_folder", "folder_open"),
        }
        jobs = [j for j in jobs if (j[0], j[1]) in heroes]
    if args.only:
        want = set(args.only)
        jobs = [j for j in jobs if f"{j[0]}__{j[1]}" in want or j[0] in want]

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "prores").mkdir(exist_ok=True)
    rows = []
    summary = []

    for asset_id, motion, obj in jobs:
        png_dir = out / "alpha_png" / asset_id / motion
        if not args.skip_blender:
            run_blender(asset_id, motion, out, args.frames, args.engine)
        cov = alpha_bbox_coverage(png_dir)
        mov = out / "prores" / f"{asset_id}_{motion}.mov"
        enc = encode_prores(png_dir, mov) if png_dir.is_dir() else {"ok": False}
        row = {
            "id": f"{asset_id}__{motion}",
            "assetId": asset_id,
            "variantId": f"{asset_id}__{motion}",
            "conceptId": obj["conceptId"],
            "motion": motion,
            "motionPreset": motion,
            "family": "premium_3d",
            "format": "png_seq",
            "file": f"3d-library-v2/alpha_png/{asset_id}/{motion}",
            "prores": f"3d-library-v2/prores/{asset_id}_{motion}.mov" if enc.get("ok") else None,
            "glb": f"3d-library-v2/models/{asset_id}_{motion}.glb",
            "background": "transparent",
            "display": "float",
            "alphaVerified": bool(cov.get("ok") and cov.get("cornerAlpha", 1) == 0),
            "subjectCoverage": cov.get("coverage"),
            "qualityStatus": "experimental",
            "factory": "v2",
            "preferredPlacement": obj.get("preferredPlacement"),
            "scaleProfile": obj.get("scaleProfile", "hero"),
            "tags": obj.get("semanticTags") or [],
            "tags_ru": obj.get("tags_ru") or [],
            "tags_zh": obj.get("tags_zh") or [],
            "proresEncode": enc,
            "bbox": cov,
        }
        rows.append(row)
        summary.append({"id": row["id"], "coverage": cov.get("coverage"), "prores": enc.get("ok"), "pix": enc.get("pix")})
        print("DONE", row["id"], "cov", cov.get("coverage"), "prores", enc.get("ok"), flush=True)

    (out / "3d-asset-registry-v2.json").write_text(json.dumps({"version": "v2", "assets": rows}, indent=2))
    (out / "build-summary-v2.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({"ok": True, "count": len(rows), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
