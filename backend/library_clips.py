"""Name the existing library in the Hypit prompt and place a matching file on each shot."""
from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path

_PLAYABLE = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mov"}
_RANK = {
    "generative_motion": 0,
    "photography": 1,
    "editorial_object": 2,
    "deterministic_motion": 3,
    "line": 5,
}
_PLACEHOLDER = re.compile(r"^\[(segment\s+\d+|audio|no speech)\]$", re.I)
_STOP = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "is", "are",
    "this", "that", "it", "we", "you", "i", "my", "our", "your", "be", "as", "at",
}


def library_root() -> Path:
    """Prefer the DigitalOcean app-library volume when mounted; else repo out/."""
    for raw in (
        os.environ.get("LUMEN_APP_LIBRARY"),
        os.environ.get("LUMEN_MEDIA_LIBRARY"),
        "/mnt/volume_nyc1_1791446889637/app-library",
    ):
        if not raw:
            continue
        path = Path(raw)
        if (path / "manifest.json").is_file():
            return path
    return Path(__file__).resolve().parents[1] / "media" / "library" / "out"


def _search():
    root = library_root()
    # search.py lives next to out/ in the repo package, or beside the volume copy.
    candidates = [
        root.parent / "search.py",
        Path(__file__).resolve().parents[1] / "media" / "library" / "search.py",
    ]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None or not (root / "manifest.json").is_file():
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
    load = getattr(module, "load", None)
    if load is None:
        return []
    # Prefer load(path=manifest) when supported.
    try:
        assets = load(path=library_root() / "manifest.json")
    except TypeError:
        assets = load()
    for asset in assets or []:
        if _listed(asset):
            found.append(asset)
    return found


def media_block():
    """Tell Hypit to use staged ./motion clips — not DO absolute paths or search.py."""
    rows = catalog()
    if not rows:
        return (
            "--- MEDIA LIBRARY ---\n"
            "No playable library files were found on this host. Keep the host and speech; "
            "do not invent substitute assets.\n"
            "--- END MEDIA LIBRARY ---"
        )
    lines = [
        "--- MEDIA LIBRARY ---",
        "Lumen searches this library before the render and stages matches as ./motion/N.mp4.",
        "In this Hypit workspace only relative staged paths are valid. Do not call search.py.",
        "Do not use DigitalOcean absolute paths. If a beat has no ./motion file, keep the host.",
        f"Catalog size on host: {len(rows)} playable files (manifest-backed).",
        "--- END MEDIA LIBRARY ---",
    ]
    return "\n".join(lines)


def staged_media_block(shots) -> str:
    """Exact Hypit-resolvable paths for this render (written into the prompt artifacts)."""
    lines = [
        "--- STAGED LIBRARY FILES ---",
        "Use only these relative paths inside the Hypit workspace:",
    ]
    used = 0
    gaps = 0
    for shot in shots or []:
        at = shot.get("at")
        label = shot.get("fragment_label") or " ".join(shot.get("parts") or [])
        lib_id = shot.get("library_id") or ""
        name = shot.get("file") or ""
        role = shot.get("format") or shot.get("kind") or "object"
        if shot.get("library") and name:
            used += 1
            lines.append(
                f"- ./motion/{name} | id={lib_id} | at={at}s | role={role} | phrase={label!r}"
            )
        else:
            gaps += 1
            lines.append(
                f"- MEDIA GAP | at={at}s | role={role} | phrase={label!r} | keep host+speech"
            )
    if used == 0 and gaps == 0:
        lines.append("(no graphic shots in this run)")
    lines.append("--- END STAGED LIBRARY FILES ---")
    return "\n".join(lines)


def _rank(asset):
    family = asset.get("visualFamily") or ""
    if asset.get("type") in ("video", "motion") and family == "generative_motion":
        return 0
    return _RANK.get(family, 4)


def _usable_query(query: str) -> str:
    text = " ".join(str(query or "").split())
    if not text or _PLACEHOLDER.match(text):
        return ""
    words = [w for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", text) if w.lower() not in _STOP]
    return " ".join(words[:12]) if words else text


def pick(query, used=(), scene_role=None, energy=None):
    """One playable file for this phrase. A line icon loses to a photo or a clip with the same words."""
    cleaned = _usable_query(query)
    if not cleaned:
        return None
    module = _search()
    if module is None:
        return None
    kwargs = {
        "limit": 12,
        "exclude_ids": used,
        "preferred_scene_role": scene_role,
        "preferred_energy": energy,
    }
    try:
        hits = module.search_assets(cleaned, path=library_root() / "manifest.json", **kwargs)
    except TypeError:
        hits = module.search_assets(cleaned, **kwargs)
    best = None
    for asset in hits or []:
        if not _listed(asset):
            continue
        path = library_root() / asset["file"]
        if path.suffix.lower() not in _PLAYABLE:
            continue
        key = (-_rank(asset), asset.get("qualityScore") or 0)
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
            shot["library"] = False
            continue
        dest = folder / name
        seconds = max(0.2, min(5.0, float(shot.get("fragment_s") or 4)))
        chain = (
            f"scale={int(width)}:{int(height)}:force_original_aspect_ratio=increase,"
            f"crop={int(width)}:{int(height)},fps=30,format=yuv420p"
        )
        source = Path(src)
        if not source.is_file():
            shot["library"] = False
            shot["library_path"] = ""
            continue
        if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            args = ["-loop", "1", "-i", source, "-t", f"{seconds:.3f}", "-vf", chain, "-an"]
        else:
            args = ["-i", source, "-t", f"{seconds:.3f}", "-vf", chain, "-an"]
        try:
            encode(*args, "-c:v", "libx264", "-pix_fmt", "yuv420p", dest, timeout=120)
        except (OSError, RuntimeError):
            if dest.is_file():
                dest.unlink()
            shot["library"] = False
            continue
        if dest.is_file() and dest.stat().st_size > 32:
            shot["library"] = True
            shot["staged_path"] = f"./motion/{name}"
        else:
            shot["library"] = False
    return shots


def write_assets_manifest(folder, shots, *, prompt_text: str = "") -> Path:
    """Persist staged asset map + prompt hash for the next job's diagnostics."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for shot in shots or []:
        rows.append({
            "shot_id": shot.get("id"),
            "library_id": shot.get("library_id") or "",
            "source_path": shot.get("library_path") or "",
            "staged_path": shot.get("staged_path") or (f"./motion/{shot['file']}" if shot.get("file") else ""),
            "used": bool(shot.get("library")),
            "phrase": shot.get("fragment_label") or "",
            "role": shot.get("format") or shot.get("kind") or "",
            "at": shot.get("at"),
            "span": shot.get("span"),
        })
    payload = {
        "library_root": str(library_root()),
        "shots": rows,
        "prompt_chars": len(prompt_text or ""),
    }
    path = folder / "assets_manifest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path
