"""Purpose contact sheets. Each tile is labeled with the asset id."""
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
SHEETS = OUT / "contact-sheets"
RENDER = ROOT / "render_svg.js"
NAVY = (14, 26, 43)


def load():
    data = json.loads((OUT / "manifest.json").read_text())
    return data["assets"]


def raster(path, dest, width=480):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_mtime >= path.stat().st_mtime:
        return dest
    subprocess.run(["node", str(RENDER), str(path), str(dest), str(width)], check=True, cwd=ROOT)
    return dest


def tile_image(asset, size):
    path = OUT / asset["file"]
    if path.suffix.lower() == ".svg":
        png = path.with_suffix(".png")
        raster(path, png, size[0] * 2)
        path = png
    elif path.suffix.lower() in {".mp4", ".webm", ".mov"}:
        png = SHEETS / "_frames" / f"{asset['id']}.jpg"
        png.parent.mkdir(parents=True, exist_ok=True)
        if not png.exists():
            subprocess.run(
                ["ffmpeg", "-y", "-ss", "0.5", "-i", str(path), "-frames:v", "1", str(png)],
                check=True, capture_output=True,
            )
        path = png
    image = Image.open(path).convert("RGBA")
    canvas = Image.new("RGBA", size, NAVY + (255,))
    image.thumbnail((size[0] - 8, size[1] - 36), Image.Resampling.LANCZOS)
    canvas.paste(image, ((size[0] - image.width) // 2, 8), image)
    return canvas.convert("RGB")


def sheet(name, assets):
    if not assets:
        print("empty", name)
        return
    columns = 4
    tile = (270, 420)
    rows = (len(assets) + columns - 1) // columns
    image = Image.new("RGB", (columns * tile[0], rows * tile[1]), (8, 16, 24))
    draw = ImageDraw.Draw(image)
    for index, asset in enumerate(assets):
        column, row = index % columns, index // columns
        try:
            thumb = tile_image(asset, (tile[0] - 12, tile[1] - 8))
        except (OSError, subprocess.CalledProcessError) as exc:
            print("skip", asset["id"], exc)
            continue
        x, y = column * tile[0] + 6, row * tile[1] + 4
        image.paste(thumb, (x, y))
        label = asset["id"]
        draw.text((x + 8, y + tile[1] - 28), label[:32], fill=(224, 177, 90))
    dest = SHEETS / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, quality=85)
    print(name, len(assets))


def main():
    assets = load()
    by_id = {item["id"]: item for item in assets}

    def role(name, limit=12):
        found = [item for item in assets if name in (item.get("sceneRoles") or [])]
        found.sort(key=lambda item: (item.get("visualFamily") != "photography", -(item.get("qualityScore") or 0)))
        return found[:limit]

    def tagged(word, limit=12):
        found = [item for item in assets if word in (item.get("tags") or []) or word in (item.get("domain") or "")]
        found.sort(key=lambda item: (item.get("visualFamily") != "photography", -(item.get("qualityScore") or 0)))
        return found[:limit]

    sheet("hooks.jpg", role("hook"))
    humans = [item for item in assets if item.get("visualFamily") == "photography" and item.get("category") == "people"]
    sheet("human-moments.jpg", humans[:16])
    sheet("detail-inserts.jpg", role("insert"))
    heroes = [item for item in assets if item["id"].startswith("v2_meta_")][:12]
    sheet("hero-visuals.jpg", heroes)
    sheet("relocation.jpg", tagged("relocation"))
    immigration = [
        item for item in assets
        if item.get("visualFamily") == "photography" and "immigration" in (item.get("tags") or [])
    ]
    sheet("immigration.jpg", immigration[:12])
    from search import search_assets
    passport = []
    for hit in search_assets("second passport", limit=12):
        if hit["id"] in by_id:
            passport.append(by_id[hit["id"]])
    sheet("second-passport.jpg", passport[:12])
    estate = [item for item in assets if item.get("domain") == "real_estate" and item.get("visualFamily") == "photography"]
    sheet("real-estate.jpg", estate[:12])
    sheet("transitions.jpg", [item for item in assets if item["id"].startswith("v2_tr_")])
    motion = [item for item in assets if item.get("type") == "video"]
    sheet("micro-motion.jpg", motion[:16])


if __name__ == "__main__":
    main()
