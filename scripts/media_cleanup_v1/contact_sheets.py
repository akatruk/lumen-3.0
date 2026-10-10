"""Build contact-sheets/cleanup/*.jpg for human review."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

NAVY = (14, 26, 43)


def _video_frame(path: Path, dest: Path) -> Path | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return dest
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "0.5", "-i", str(path), "-frames:v", "1", str(dest)],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return dest if dest.is_file() else None


def _placeholder(size: tuple[int, int], label: str) -> Image.Image:
    canvas = Image.new("RGB", size, (30, 48, 72))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, size[1] // 2 - 6), label[:28], fill=(224, 177, 90))
    return canvas


def _load_thumb(library: Path, asset: dict, frames: Path, size: tuple[int, int]) -> Image.Image | None:
    rel = asset.get("file") or ""
    path = library / rel
    if not path.is_file():
        return _placeholder(size, "MISSING")
    ext = path.suffix.lower()
    if ext == ".svg":
        # Light placeholder for vectors — avoid node raster dependency in cleanup pass.
        return _placeholder(size, "SVG")
    if ext in {".mp4", ".webm", ".mov", ".mkv"}:
        frame = frames / f"{asset['id']}.jpg"
        got = _video_frame(path, frame)
        if not got:
            return _placeholder(size, "VIDEO?")
        path = got
    try:
        image = Image.open(path).convert("RGBA")
    except OSError:
        return _placeholder(size, "DECODE?")
    canvas = Image.new("RGBA", size, NAVY + (255,))
    image.thumbnail((size[0] - 8, size[1] - 36), Image.Resampling.LANCZOS)
    canvas.paste(image, ((size[0] - image.width) // 2, 8), image if image.mode == "RGBA" else None)
    return canvas.convert("RGB")


def build_sheet(
    name: str,
    items: list[dict],
    *,
    library: Path,
    out_dir: Path,
    columns: int = 4,
    tile: tuple[int, int] = (270, 420),
    limit: int = 48,
) -> Path | None:
    assets = items[:limit]
    if not assets:
        return None
    frames = out_dir / "_frames"
    rows = (len(assets) + columns - 1) // columns
    image = Image.new("RGB", (columns * tile[0], rows * tile[1]), (8, 16, 24))
    draw = ImageDraw.Draw(image)
    placed = 0
    for index, asset in enumerate(assets):
        column, row = index % columns, index // columns
        thumb = _load_thumb(library, asset, frames, (tile[0] - 12, tile[1] - 8))
        if thumb is None:
            continue
        x, y = column * tile[0] + 6, row * tile[1] + 4
        image.paste(thumb, (x, y))
        label = f"{asset.get('id', '?')}"
        q = asset.get("quality") or asset.get("_quality") or ""
        if q:
            label = f"{label} [{q}]"[:34]
        else:
            label = label[:32]
        draw.text((x + 8, y + tile[1] - 28), label, fill=(224, 177, 90))
        placed += 1
    if placed == 0:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / name
    image.save(dest, quality=85)
    return dest


def build_cleanup_sheets(library: Path, review: dict, out_dir: Path | None = None) -> dict:
    out_dir = out_dir or (library / "contact-sheets" / "cleanup")
    out_dir.mkdir(parents=True, exist_ok=True)
    by_id = {a["id"]: a for a in review.get("assets") or []}
    # Enrich with quality
    for a in by_id.values():
        a["_quality"] = a.get("quality")

    def pick(predicate, limit=48):
        return [a for a in review.get("assets") or [] if predicate(a)][:limit]

    low = pick(lambda a: a.get("quality") == "LOW")
    legacy = pick(lambda a: a.get("quality") == "LEGACY")
    uncertain = pick(lambda a: a.get("quality") == "UNCERTAIN")
    videos = pick(lambda a: a.get("type") in {"video", "motion"} or str(a.get("file") or "").endswith((".mp4", ".webm")))

    dupe_ids = []
    for g in (review.get("exact_duplicate_groups") or []) + (review.get("perceptual_duplicate_groups") or []):
        dupe_ids.extend(g.get("recommend_quarantine") or [])
    # Also fold explicit quarantine recommendations into the duplicates sheet if empty.
    for row in review.get("recommended_quarantine") or []:
        rid = row["id"] if isinstance(row, dict) else row
        dupe_ids.append(rid)
    duplicates = [by_id[i] for i in dict.fromkeys(dupe_ids) if i in by_id][:48]

    # Replacements = keep side of duplicate groups
    keep_ids = []
    for g in (review.get("exact_duplicate_groups") or []) + (review.get("perceptual_duplicate_groups") or []):
        if g.get("recommend_keep"):
            keep_ids.append(g["recommend_keep"])
    replacements = [by_id[i] for i in dict.fromkeys(keep_ids) if i in by_id][:48]

    # Empty LOW/UNCERTAIN sheets still get a one-tile stub so the path exists for review.
    def ensure(items, stub_label):
        if items:
            return items
        return [{"id": stub_label, "file": "", "quality": stub_label}]

    written = {}
    for name, items in (
        ("low-quality.jpg", ensure(low, "NONE_LOW")),
        ("duplicates.jpg", duplicates),
        ("legacy.jpg", ensure(legacy, "NONE_LEGACY")),
        ("replacements.jpg", replacements),
        ("uncertain.jpg", ensure(uncertain, "NONE_UNCERTAIN")),
        ("videos.jpg", videos),
    ):
        path = build_sheet(name, items, library=library, out_dir=out_dir)
        written[name] = str(path) if path else None
    return written
