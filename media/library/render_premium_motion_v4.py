#!/usr/bin/env python3
"""Render premium-motion V4 calibration clips → VP9+alpha WebM + contact sheets.

Remotion PNG sequence → ffmpeg libvpx-vp9 yuva420p (true alpha). H.264 is never claimed as alpha.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
MOTION = ROOT / "motion"
RECIPE = Path(__file__).resolve().parent / "recipes" / "premium-motion-v4-calibration.json"
OUT = Path(__file__).resolve().parent / "out"
PREMIUM = OUT / "motion" / "premium"
SHEETS = OUT / "contact-sheets" / "premium-motion"
ENTRY = "src/clips/index.ts"


def run(cmd, cwd=None):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def has_alpha(webm: Path) -> bool:
    """Decode a mid frame with libvpx-vp9; require both transparent and opaque pixels.

    Frame 0 is often a full fade-in (all alpha 0) — sample ~2s instead.
    """
    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "a.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-c:v",
                "libvpx-vp9",
                "-ss",
                "2.0",
                "-i",
                str(webm),
                "-frames:v",
                "1",
                "-update",
                "1",
                str(png),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        im = Image.open(png)
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        alphas = [p[3] for p in im.getdata()]
        return min(alphas) < 250 and max(alphas) > 10


def render_one(comp: str, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pmv4-") as td:
        frames = Path(td) / "frames"
        frames.mkdir()
        run(
            [
                "npx",
                "remotion",
                "render",
                ENTRY,
                comp,
                str(frames),
                "--sequence",
                "--image-format=png",
                "--overwrite",
            ],
            cwd=MOTION,
        )
        pngs = sorted(frames.glob("*.png"))
        if not pngs:
            raise RuntimeError(f"no frames for {comp}")
        normalized = []
        for i, src in enumerate(pngs):
            target = frames / f"frame_{i:05d}.png"
            if src.resolve() != target.resolve():
                src.rename(target)
            normalized.append(target)
        tmp = Path(td) / "out.webm"
        run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                "30",
                "-i",
                str(frames / "frame_%05d.png"),
                "-c:v",
                "libvpx-vp9",
                "-pix_fmt",
                "yuva420p",
                "-auto-alt-ref",
                "0",
                "-b:v",
                "2M",
                str(tmp),
            ]
        )
        partial = dest.with_suffix(".webm.partial")
        shutil.copy2(tmp, partial)
        partial.replace(dest)
        mid = normalized[len(normalized) // 2]
        preview = dest.with_suffix(".preview.jpg")
        plate = Image.new("RGBA", (1080, 1920), (14, 26, 43, 255))
        fg = Image.open(mid).convert("RGBA")
        if fg.size != plate.size:
            fg = fg.resize(plate.size)
        plate.alpha_composite(fg)
        plate.convert("RGB").resize((270, 480)).save(preview, quality=88)
        alpha_ok = has_alpha(dest) if dest.stat().st_size > 0 else False
        return {
            "file": str(dest.relative_to(OUT)),
            "bytes": dest.stat().st_size,
            "sha256": sha256(dest),
            "alphaProbe": alpha_ok,
            "preview": str(preview.relative_to(OUT)),
        }


def contact_sheet(previews: list[Path], title: str, dest: Path, cols=5):
    if not previews:
        return
    tw, th = 270, 480
    rows = (len(previews) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th + 40), (14, 26, 43))
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 10), title, fill=(244, 239, 230))
    for i, p in enumerate(previews):
        im = Image.open(p).convert("RGB").resize((tw, th))
        r, c = divmod(i, cols)
        sheet.paste(im, (c * tw, 40 + r * th))
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest, quality=90)


def main():
    recipe = json.loads(RECIPE.read_text())
    assets = recipe["assets"]
    only = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    results = []
    PREMIUM.mkdir(parents=True, exist_ok=True)
    SHEETS.mkdir(parents=True, exist_ok=True)

    for asset in assets:
        if only and asset["id"] not in only and asset["composition"] not in only:
            continue
        dest = OUT / asset["file"]
        print(f"=== {asset['id']} ({asset['composition']}) ===", flush=True)
        meta = render_one(asset["composition"], dest)
        meta.update({k: asset[k] for k in ("id", "role", "composition", "category", "tags")})
        if asset["role"] == "bg":
            meta["alphaRequired"] = False
            meta["qa"] = "pass" if meta["bytes"] > 5000 else "reject_tiny"
        else:
            meta["alphaRequired"] = True
            meta["qa"] = "pass" if meta["alphaProbe"] and meta["bytes"] > 5000 else "reject_alpha_or_tiny"
        results.append(meta)

    by_role = {}
    for r in results:
        by_role.setdefault(r["role"], []).append(OUT / r["preview"])
    for role, prevs in by_role.items():
        contact_sheet(prevs, f"premium-motion V4 — {role}", SHEETS / f"{role}.jpg")
    contact_sheet(
        [OUT / r["preview"] for r in results],
        "premium-motion V4 — calibration 18",
        SHEETS / "calibration-18.jpg",
        cols=6,
    )

    report = {
        "batch": recipe["batch"],
        "model": recipe["model"],
        "results": results,
        "approved": [r["id"] for r in results if r["qa"] == "pass"],
        "rejected": [r["id"] for r in results if r["qa"] != "pass"],
    }
    (OUT / "premium-motion-v4-calibration-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"approved": len(report["approved"]), "rejected": len(report["rejected"])}, indent=2))
    return 0 if not report["rejected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
