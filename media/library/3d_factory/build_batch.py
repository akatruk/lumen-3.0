#!/usr/bin/env python3
"""Orchestrate Lumen 3D Asset Factory V1 — Blender → PNG α → VP9 + registry.

NOTE (V10.1): On several macOS Homebrew ffmpeg builds, `-pix_fmt yuva420p` with
libvpx-vp9 silently falls back to opaque `yuv420p`. Treat `3d-library/alpha_png/`
as the production alpha master. Remotion V10.1 stages PNG sequences (`png_seq`).
Do not claim WebM alpha until `ffprobe` reports `yuva420p` (or use ProRes 4444).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
FACTORY = Path(__file__).resolve().parent
CATALOG = FACTORY / "catalog_v1.json"
DEFAULT_OUT = ROOT / "3d-library"
BLENDER = "blender"


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_png_alpha(png_dir: Path) -> dict:
    frames = sorted(png_dir.glob("frame_*.png"))
    if not frames:
        return {"ok": False, "reason": "no_frames"}
    sample = frames[min(len(frames) - 1, len(frames) // 3)]
    im = Image.open(sample)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    alphas = [p[3] for p in im.getdata()]
    return {
        "ok": min(alphas) < 250 and max(alphas) > 10,
        "frame": sample.name,
        "minAlpha": min(alphas),
        "maxAlpha": max(alphas),
        "frameCount": len(frames),
    }


def encode_webm(png_dir: Path, dest: Path, fps: int) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    pattern = str(png_dir / "frame_%04d.png")
    # Blender names frame_0001.png — use glob via concat if needed
    frames = sorted(png_dir.glob("frame_*.png"))
    if not frames:
        raise FileNotFoundError(png_dir)
    # Remotion/Blender may use frame_0001 or frame_1 — normalize via list
    with tempfile.TemporaryDirectory(prefix="l3d-enc-") as td:
        td_path = Path(td)
        for i, src in enumerate(frames, start=1):
            (td_path / f"f_{i:04d}.png").write_bytes(src.read_bytes())
        run(
            [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", str(td_path / "f_%04d.png"),
                "-c:v", "libvpx-vp9",
                "-pix_fmt", "yuva420p",
                "-auto-alt-ref", "0",
                "-b:v", "0",
                "-crf", "28",
                "-an",
                str(dest),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    # Verify alpha in encoded webm
    with tempfile.TemporaryDirectory() as td2:
        png = Path(td2) / "a.png"
        subprocess.run(
            [
                "ffmpeg", "-y", "-c:v", "libvpx-vp9", "-ss", "1.0",
                "-i", str(dest), "-frames:v", "1", "-update", "1", str(png),
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        im = Image.open(png)
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        alphas = [p[3] for p in im.getdata()]
        alpha_ok = min(alphas) < 250 and max(alphas) > 10
    return {
        "file": str(dest),
        "sha256": sha256(dest),
        "bytes": dest.stat().st_size,
        "alphaOk": alpha_ok,
        "pixFmt": "yuva420p",
    }


def make_preview(png_dir: Path, dest: Path) -> None:
    frames = sorted(png_dir.glob("frame_*.png"))
    if not frames:
        return
    mid = frames[len(frames) // 2]
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.open(mid).convert("RGBA").save(dest)


def render_one(asset_id: str, motion: str, out: Path, frames: int, fps: int, size: int) -> dict:
    script = FACTORY / "blender_factory.py"
    proc = subprocess.run(
        [
            BLENDER, "-b", "--python", str(script), "--",
            "--asset", asset_id,
            "--motion", motion,
            "--out", str(out),
            "--frames", str(frames),
            "--fps", str(fps),
            "--size", str(size),
        ],
        capture_output=True,
        text=True,
    )
    print(proc.stdout[-2000:] if proc.stdout else "", flush=True)
    if proc.returncode != 0:
        print(proc.stderr[-3000:] if proc.stderr else "", flush=True)
        raise RuntimeError(f"blender failed for {asset_id}/{motion}: exit {proc.returncode}")
    if "FACTORY_OK" not in (proc.stdout or ""):
        raise RuntimeError(f"blender did not confirm FACTORY_OK for {asset_id}/{motion}")
    png_dir = out / "alpha_png" / asset_id / motion
    png_qa = verify_png_alpha(png_dir)
    webm = out / "alpha" / f"{asset_id}_{motion}.webm"
    enc = encode_webm(png_dir, webm, fps)
    preview = out / "previews" / f"{asset_id}_{motion}.png"
    make_preview(png_dir, preview)
    glb = out / "models" / f"{asset_id}_{motion}.glb"
    blend = out / "blender" / f"{asset_id}_{motion}.blend"
    return {
        "assetId": asset_id,
        "motion": motion,
        "pngQa": png_qa,
        "alphaVideo": enc,
        "preview": str(preview.relative_to(out)),
        "glb": str(glb.relative_to(out)) if glb.is_file() else None,
        "glbBytes": glb.stat().st_size if glb.is_file() else 0,
        "blend": str(blend.relative_to(out)) if blend.is_file() else None,
        "pass": bool(png_qa.get("ok") and enc.get("alphaOk") and glb.is_file()),
    }


def contact_sheet(out: Path, rows: list[dict]) -> Path:
    cells = []
    for r in rows:
        prev = out / r["preview"]
        if prev.is_file():
            cells.append((r["assetId"], r["motion"], Image.open(prev).convert("RGBA")))
    if not cells:
        raise SystemExit("no previews for contact sheet")
    w = h = 360
    cols = 5
    grid_rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * w, grid_rows * (h + 40)), (18, 17, 15, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (aid, motion, im) in enumerate(cells):
        im = im.resize((w, h), Image.Resampling.LANCZOS)
        x = (i % cols) * w
        y = (i // cols) * (h + 40)
        sheet.paste(im, (x, y), im)
        label = f"{aid.replace('l3d_', '')} · {motion}"[:42]
        draw.text((x + 8, y + h + 8), label, fill=(244, 239, 230, 255))
    dest = out / "previews" / "3d-contact-sheet.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(dest, quality=92)
    return dest


def build_registry(catalog: dict, results: list[dict], out: Path) -> dict:
    by_asset = {o["assetId"]: o for o in catalog["objects"]}
    assets = []
    for r in results:
        base = dict(by_asset[r["assetId"]])
        assets.append({
            **base,
            "motion": r["motion"],
            "variantId": f"{r['assetId']}__{r['motion']}",
            "modelFile": r.get("glb"),
            "sourceBlend": r.get("blend"),
            "alphaVideoFile": f"alpha/{r['assetId']}_{r['motion']}.webm",
            "previewFile": r.get("preview"),
            "duration": catalog["durationFrames"] / catalog["fps"],
            "fps": catalog["fps"],
            "resolution": catalog["resolution"],
            "supportedLocales": ["ru-RU", "en-US", "zh-CN"],
            "qualityStatus": "approved" if r.get("pass") else "needs_review",
            "alphaVerified": r.get("alphaVideo", {}).get("alphaOk"),
            "sha256": r.get("alphaVideo", {}).get("sha256"),
            "version": "v1",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "generationSource": "blender_procedural_eevee",
            "license": "lumen-internal-procedural",
            "textSafeAreas": ["upper", "center_object"],
            "motionBounds": {"normalized": True, "faceSafeDefault": True},
            "family": "premium_3d",
            "visualFamily": "premium_3d",
            "kind": "3d_motion",
        })
    reg = {
        "version": "v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "objectCount": len({a['assetId'] for a in assets}),
        "animationCount": len(assets),
        "passCount": sum(1 for r in results if r.get("pass")),
        "assets": assets,
        "results": results,
    }
    (out / "3d-asset-registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n")
    (out / "metadata" / "registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n")
    return reg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--jobs", type=int, default=1, help="parallel Blender jobs (1 recommended on laptop)")
    ap.add_argument("--asset", action="append", default=[])
    ap.add_argument("--motion", action="append", default=[])
    args = ap.parse_args()
    catalog = json.loads(CATALOG.read_text())
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for obj in catalog["objects"]:
        if args.asset and obj["assetId"] not in args.asset:
            continue
        for motion in obj["motions"]:
            if args.motion and motion not in args.motion:
                continue
            jobs.append((obj["assetId"], motion))

    results = []
    if args.jobs <= 1:
        for asset_id, motion in jobs:
            print(f"=== {asset_id} / {motion} ===", flush=True)
            results.append(
                render_one(asset_id, motion, out, catalog["durationFrames"], catalog["fps"], catalog["resolution"][0])
            )
    else:
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            futs = {
                ex.submit(
                    render_one, a, m, out, catalog["durationFrames"], catalog["fps"], catalog["resolution"][0]
                ): (a, m)
                for a, m in jobs
            }
            for fut in as_completed(futs):
                results.append(fut.result())

    results.sort(key=lambda r: (r["assetId"], r["motion"]))
    sheet = contact_sheet(out, results)
    reg = build_registry(catalog, results, out)
    summary = {
        "objects": reg["objectCount"],
        "animations": reg["animationCount"],
        "passCount": reg["passCount"],
        "contactSheet": str(sheet),
        "registry": str(out / "3d-asset-registry.json"),
        "allPass": reg["passCount"] == reg["animationCount"],
    }
    (out / "build-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if not summary["allPass"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
