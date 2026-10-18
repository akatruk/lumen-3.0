"""Manifest rows for stills made by the lumen SDXL runner.

One asset is shared across ru-RU, en-US, and zh-CN. The picture has no
baked text. The concept id is what search uses.
"""
import hashlib
import json
import shutil
from pathlib import Path

try:
    from concepts import CONCEPTS
except ImportError:
    from media.library.concepts import CONCEPTS

BY_ID = {item["id"]: item for item in CONCEPTS}

FOLDERS = {
    "photograph": "static/runpod/photographs",
    "detail": "static/runpod/details",
    "object": "static/runpod/objects",
    "foreground": "static/runpod/foreground",
}


def _concept(concept_id):
    return BY_ID.get(concept_id) or {
        "id": concept_id,
        "en": concept_id.replace(".", " "),
        "ru": concept_id.replace(".", " "),
        "zh": concept_id.replace(".", " "),
    }


def _tags(plan, concept):
    words = [part for part in concept["en"].lower().split() if len(part) > 2]
    words.append(plan["kind"])
    return list(dict.fromkeys(words))


def row_for(plan, relative_file, digest, seconds=None):
    concept = _concept(plan["concept"])
    width = int(plan["width"])
    height = int(plan["height"])
    portrait = height > width
    kind = plan["kind"]
    category = {
        "photograph": "people" if any(word in plan["prompt"].lower() for word in ("family", "couple", "advisor", "person", "child", "adult", "traveler")) else "real-estate",
        "detail": "details",
        "object": "objects",
        "foreground": "foreground",
    }[kind]
    return {
        "id": plan["id"],
        "type": "image",
        "category": category,
        "conceptId": concept["id"],
        "tags": _tags(plan, concept),
        "description": {"en": concept["en"], "ru": concept["ru"], "zh": concept["zh"]},
        "file": relative_file,
        "aspectRatio": "9:16" if portrait else "1:1",
        "composition": "negative_space_right" if kind == "foreground" else "center",
        "background": "photographic",
        "qualityScore": 0.84,
        "textSafe": True,
        "textSafeAreas": ["right", "upper_right"] if kind == "foreground" else ["upper_left"],
        "source": "runpod",
        "visualFamily": "photography" if kind == "photograph" else "editorial_object",
        "mood": "calm",
        "energy": "low",
        "sceneRoles": ["explanation"],
        "subjects": _tags(plan, concept)[:4],
        "environment": concept["en"],
        "action": kind,
        "generation": {
            "provider": "runpod",
            "model": plan["model"],
            "checkpoint": plan["checkpoint"],
            "pipeline": plan["pipeline"],
            "seed": plan["seed"],
            "prompt": plan["prompt"],
            "negativePrompt": plan["negative_prompt"],
            "steps": plan["num_inference_steps"],
            "guidance": plan["guidance_scale"],
            "width": width,
            "height": height,
            "gpu": "NVIDIA GeForce RTX 4090",
            "seconds": seconds,
            "sha256": digest,
            "dtype": plan["dtype"],
        },
    }


def _digest(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def apply(library, source_dir, plans):
    """Copy approved stills into the library and append manifest rows.

    An id already in the manifest is left alone. A file already at the
    destination with a different checksum is not replaced.
    """
    library = Path(library)
    source_dir = Path(source_dir)
    manifest_path = library / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assets = manifest["assets"]
    known = {item["id"] for item in assets}
    added = []
    for plan in plans:
        if plan["id"] in known:
            continue
        src = source_dir / (plan["id"] + ".png")
        if not src.is_file():
            continue
        relative = FOLDERS[plan["kind"]] + "/" + plan["id"] + ".png"
        dest = library / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        digest = _digest(src)
        if dest.is_file() and _digest(dest) != digest:
            continue
        if not dest.is_file():
            shutil.copy2(src, dest)
        sidecar = src.with_suffix(".json")
        seconds = None
        if sidecar.is_file():
            seconds = json.loads(sidecar.read_text()).get("seconds")
        assets.append(row_for(plan, relative, digest, seconds))
        known.add(plan["id"])
        added.append(plan["id"])
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return added


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--plans", required=True)
    args = parser.parse_args()
    plans = [json.loads(line) for line in open(args.plans) if line.strip()]
    added = apply(args.library, args.source, plans)
    print("ADDED", len(added))


if __name__ == "__main__":
    main()
