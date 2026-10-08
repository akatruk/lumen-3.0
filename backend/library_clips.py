"""Name the existing library in the Hypit prompt and place a matching file on each shot."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_PLAYABLE = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mov"}
_RANK = {
    "generative_motion": 0,
    "photography": 1,
    "editorial_object": 2,
    "deterministic_motion": 3,
    "line": 5,
}


def library_root():
    return Path(__file__).resolve().parents[1] / "media" / "library" / "out"


def _search():
    path = library_root().parent / "search.py"
    if not path.is_file() or not (library_root() / "manifest.json").is_file():
        return None
    spec = importlib.util.spec_from_file_location("lumen_library_search", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _listed(asset):
    file = asset.get("file") or ""
    path = library_root() / file
    if path.suffix.lower() == ".tsx" or not path.is_file():
        return None
    return asset


def catalog():
    """Every real library file, in manifest order. Missing entries stay out."""
    module = _search()
    if module is None:
        return []
    found = []
    for asset in module.load():
        if _listed(asset):
            found.append(asset)
    return found


def media_block():
    """The files the prompt may use. Spoken lines are not copied into this list."""
    rows = catalog()
    if not rows:
        return ""
    lines = [
        "--- MEDIA LIBRARY ---",
        "These files already exist. Place the matching file on the spoken thought. "
        "Do not draw a substitute and do not ask for a new file.",
    ]
    for asset in rows:
        lines.append(f"{asset['id']} ./{asset['file']}")
    lines.append("--- END MEDIA LIBRARY ---")
    return "\n".join(lines)


def _rank(asset):
    family = asset.get("visualFamily") or ""
    if asset.get("type") in ("video", "motion") and family == "generative_motion":
        return 0
    return _RANK.get(family, 4)


def pick(query, used=()):
    """One playable file for this phrase. A line icon loses to a photo or a clip with the same words."""
    module = _search()
    if module is None:
        return None
    words = module._tokens(query)
    if not words:
        return None
    used = set(used)
    best = None
    for asset in module.load():
        if asset.get("id") in used or not _listed(asset):
            continue
        path = library_root() / asset["file"]
        if path.suffix.lower() not in _PLAYABLE:
            continue
        overlap = sum(1 for word in words if word in module._hay(asset))
        if overlap == 0:
            continue
        key = (overlap, -_rank(asset), asset.get("qualityScore") or 0)
        if best is None or key > best[0]:
            best = (key, asset, path)
    if not best:
        return None
    _key, asset, path = best
    return {"id": asset["id"], "file": asset["file"], "path": path}


def stage(folder, shots, width, height, encode):
    """Copy a matched library file into ./motion/N.mp4. A failed encode leaves the shot to be drawn."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for shot in shots:
        src = shot.get("library_path")
        name = shot.get("file")
        if not src or not name:
            continue
        dest = folder / name
        seconds = max(0.2, min(5.0, float(shot.get("fragment_s") or 4)))
        chain = (
            f"scale={int(width)}:{int(height)}:force_original_aspect_ratio=increase,"
            f"crop={int(width)}:{int(height)},fps=30,format=yuv420p"
        )
        source = Path(src)
        if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            args = ["-loop", "1", "-i", source, "-t", f"{seconds:.3f}", "-vf", chain, "-an"]
        else:
            args = ["-i", source, "-t", f"{seconds:.3f}", "-vf", chain, "-an"]
        try:
            encode(*args, "-c:v", "libx264", "-pix_fmt", "yuv420p", dest, timeout=120)
        except (OSError, RuntimeError):
            if dest.is_file():
                dest.unlink()
            continue
        if dest.is_file() and dest.stat().st_size > 32:
            shot["library"] = True
    return shots
