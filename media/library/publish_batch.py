"""Fold the calibration stills and clips into the vector library."""
import json
import shutil
from pathlib import Path

from PIL import Image

from build_vector import ROOT, main as build

STILLS = Path("/tmp/batch1")
CLIPS = Path("/tmp/lumen-clips")

PEOPLE = {
    "people_consult_001": (["consultation", "advice", "guidance", "meeting", "trust"], "subject_right", 0.86),
    "people_couple_001": (["couple", "planning", "documents", "future", "home"], "subject_left", 0.84),
    "people_review_001": (["documents", "review", "planning", "desk", "focus"], "negative_space_top", 0.88),
    "people_meeting_001": (["meeting", "business", "consultation", "advice"], "negative_space_top", 0.8),
    "people_door_001": (["family", "home", "arrival", "relocation", "residence"], "subject_left", 0.9),
    "people_phone_001": (["phone", "consultation", "professional", "communication"], "subject_right", 0.82),
    "people_packing_001": (["packing", "relocation", "travel", "luggage", "moving"], "subject_center", 0.9),
    "people_apartment_001": (["apartment", "home", "architecture", "interior"], "negative_space_left", 0.84),
}

OBJECTS = {
    # concept_house_001 and concept_path_001 are line assets from build_vector.
    # The plastic and elevation stills stay in rejected/.
    "concept_shield_001": ("concepts", ["security", "protection", "trust"], 0.86),
    "concept_growth_001": ("business", ["growth", "business", "progress", "finance"], 0.84),
    "doc_book_001": ("documents", ["passport", "document", "identity", "booklet"], 0.82),
    "doc_folder_001": ("documents", ["folder", "documents", "filing"], 0.88),
    "doc_calendar_001": ("documents", ["calendar", "time", "planning"], 0.9),
    "doc_seal_001": ("documents", ["certificate", "approval", "document", "seal"], 0.86),
    "still_luggage_001": ("global", ["luggage", "travel", "relocation", "packing"], 0.88),
    "still_city_001": ("global", ["city", "arrival", "skyline", "destination"], 0.86),
}

CLIPS_META = [
    ("target_hit_001", "target-hit.webm", "conceptual", ["goal", "target", "success", "decision", "planning"], False, 0.9),
    ("global_route_001", "GlobalRoute.webm", "global", ["international", "route", "travel", "relocation", "global"], False, 0.9),
    ("location_pins_001", "LocationPins.webm", "global", ["destination", "location", "options", "international"], False, 0.86),
    ("document_approval_001", "DocumentApproval.webm", "documents", ["approval", "document", "filing", "completion"], False, 0.88),
    ("abstract_drift_001", "AbstractDrift.webm", "backgrounds", ["background", "transition", "atmosphere", "abstract"], True, 0.84),
]


def key_white(src, dest):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    sp = im.load()
    seen = bytearray(w * h)

    def chroma(r, g, b):
        return max(r, g, b) - min(r, g, b)

    def bg(x, y):
        r, g, b = sp[x, y]
        return chroma(r, g, b) < 14 and (r + g + b) / 3 > 236

    stack = []
    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))
    while stack:
        x, y = stack.pop()
        i = y * w + x
        if seen[i] or not bg(x, y):
            continue
        seen[i] = 1
        if x > 0:
            stack.append((x - 1, y))
        if x + 1 < w:
            stack.append((x + 1, y))
        if y > 0:
            stack.append((x, y - 1))
        if y + 1 < h:
            stack.append((x, y + 1))
    out = Image.new("RGBA", im.size)
    dp = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = sp[x, y]
            dp[x, y] = (r, g, b, 0 if seen[y * w + x] else 255)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)


def thumb(src, dest, width=320):
    im = Image.open(src).convert("RGBA")
    im.thumbnail((width, width * 2))
    plate = Image.new("RGBA", im.size, (14, 26, 43, 255))
    plate.alpha_composite(im)
    dest.parent.mkdir(parents=True, exist_ok=True)
    plate.convert("RGB").save(dest, quality=85)


def row(ident, kind, category, tags, file, aspect, composition, background, score, description, **extra):
    item = {
        "id": ident,
        "type": kind,
        "category": category,
        "tags": tags,
        "description": description,
        "file": file,
        "aspectRatio": aspect,
        "composition": composition,
        "background": background,
        "qualityScore": score,
        "textSafe": True,
        "source": extra.pop("source", "generated"),
    }
    item.update(extra)
    return item


def main():
    build()
    manifest = json.loads((ROOT / "manifest.json").read_text())
    assets = manifest["assets"]
    rejected = ROOT / "rejected"
    rejected.mkdir(exist_ok=True)
    shutil.copy(STILLS / "people_airport_001.png", rejected / "people_airport_001.png")

    for ident, (tags, composition, score) in PEOPLE.items():
        dest = ROOT / "static" / "people" / f"{ident}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(STILLS / f"{ident}.png", dest)
        thumb(dest, ROOT / "thumbnails" / "people" / f"{ident}.jpg")
        assets.append(row(
            ident, "image", "people", tags, f"static/people/{ident}.png", "9:16", composition,
            "photographic", score, "Editorial photograph with room for type.",
        ))

    for ident, (category, tags, score) in OBJECTS.items():
        dest = ROOT / "static" / category / f"{ident}.png"
        if ident == "still_city_001":
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(STILLS / f"{ident}.png", dest)
        else:
            key_white(STILLS / f"{ident}.png", dest)
        thumb(dest, ROOT / "thumbnails" / category / f"{ident}.jpg")
        full_frame = ident == "still_city_001"
        aspect = "16:9" if full_frame else "1:1"
        assets.append(row(
            ident, "image", category, tags, f"static/{category}/{ident}.png", aspect, "center",
            "photographic" if full_frame else "transparent", score,
            "Full-frame plate with open sky." if full_frame else "Isolated object. Type is added later.",
        ))

    for ident, filename, category, tags, loopable, score in CLIPS_META:
        folder = ROOT / "motion" / category
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy(CLIPS / filename, folder / f"{ident}.webm")
        assets.append(row(
            ident, "video", category, tags, f"motion/{category}/{ident}.webm", "9:16", "center",
            "transparent", score, "Short motion block, four seconds, no type.",
            source="remotion", duration=4.0, fps=30, width=1080, height=1920, loopable=loopable,
        ))

    (ROOT / "manifest.json").write_text(json.dumps({"version": 1, "assets": assets}, indent=2) + "\n")
    sheets = ROOT / "contact-sheets"
    sheets.mkdir(exist_ok=True)
    for name in ("contact-people.jpg", "contact-objects.jpg", "contact-motion.jpg", "contact-icons.jpg"):
        src = Path("/tmp") / name
        if src.exists():
            shutil.copy(src, sheets / name)
    print("total", len(assets))


if __name__ == "__main__":
    main()
