#!/usr/bin/env python3
"""Index approved 3D factory assets into media/library/out/manifest.json (additive)."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REG = ROOT / "3d-library" / "3d-asset-registry.json"
OUT = ROOT / "media" / "library" / "out"
MANIFEST = OUT / "manifest.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=DEFAULT_REG)
    ap.add_argument("--library-out", type=Path, default=OUT)
    ap.add_argument("--publish-binaries", action="store_true", help="copy alpha/glb/previews into library out")
    args = ap.parse_args()
    reg = json.loads(args.registry.read_text())
    lib = args.library_out
    dest_motion = lib / "motion" / "premium3d"
    dest_models = lib / "models" / "premium3d"
    dest_prev = lib / "thumbnails" / "premium3d"
    if args.publish_binaries:
        for d in (dest_motion, dest_models, dest_prev):
            d.mkdir(parents=True, exist_ok=True)
        src_root = args.registry.parent
        for asset in reg.get("assets") or []:
            for key, dest_dir, field in (
                ("alphaVideoFile", dest_motion, "file"),
                ("modelFile", dest_models, "modelFile"),
                ("previewFile", dest_prev, "preview"),
            ):
                rel = asset.get(key)
                if not rel:
                    continue
                src = src_root / rel
                if not src.is_file():
                    continue
                target = dest_dir / src.name
                if not target.exists() or target.stat().st_size != src.stat().st_size:
                    tmp = target.with_suffix(target.suffix + ".partial")
                    shutil.copy2(src, tmp)
                    tmp.replace(target)
                if key == "alphaVideoFile":
                    asset["file"] = f"motion/premium3d/{src.name}"
                elif key == "modelFile":
                    asset["modelPath"] = f"models/premium3d/{src.name}"
                elif key == "previewFile":
                    asset["thumbnail"] = f"thumbnails/premium3d/{src.name}"

    rows = []
    for asset in reg.get("assets") or []:
        if asset.get("qualityStatus") != "approved":
            continue
        row = {
            "id": asset["variantId"],
            "conceptId": asset.get("conceptId"),
            "category": asset.get("category"),
            "family": "premium_3d",
            "visualFamily": "premium_3d",
            "kind": "3d_motion",
            "file": asset.get("file") or f"motion/premium3d/{Path(asset.get('alphaVideoFile') or '').name}",
            "modelFile": asset.get("modelPath") or asset.get("modelFile"),
            "sourceBlend": asset.get("sourceBlend"),
            "preview": asset.get("thumbnail") or asset.get("previewFile"),
            "tags": list(asset.get("semanticTags") or []),
            "tags_ru": list(asset.get("tags_ru") or []),
            "tags_zh": list(asset.get("tags_zh") or []),
            "supportedLocales": asset.get("supportedLocales") or ["ru-RU", "en-US", "zh-CN"],
            "duration": asset.get("duration"),
            "fps": asset.get("fps"),
            "resolution": asset.get("resolution"),
            "preferredPlacement": asset.get("preferredPlacement"),
            "motionPreset": asset.get("motion"),
            "alpha": True,
            "pixFmt": "yuva420p",
            "qualityStatus": "approved",
            "qualityScore": 0.92,
            "sceneRoles": ["foreground_object", "semantic_object", "cutaway"],
            "textSafeAreas": asset.get("textSafeAreas") or [],
            "sha256": asset.get("sha256"),
            "version": asset.get("version"),
            "provenance": {
                "source": asset.get("generationSource"),
                "license": asset.get("license"),
                "factory": "3d_asset_factory_v1",
            },
        }
        rows.append(row)

    rows_path = lib / "premium-3d-v1-rows.json"
    rows_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")

    # Merge into manifest if present
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text())
        assets = list(manifest.get("assets") or [])
        existing = {a.get("id") for a in assets}
        added = 0
        for row in rows:
            if row["id"] in existing:
                # replace in place
                assets = [row if a.get("id") == row["id"] else a for a in assets]
            else:
                assets.append(row)
                added += 1
        manifest["assets"] = assets
        backup = MANIFEST.with_suffix(".json.bak-3d-v1")
        if not backup.exists():
            shutil.copy2(MANIFEST, backup)
        tmp = MANIFEST.with_suffix(".json.partial")
        tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        tmp.replace(MANIFEST)
        print(json.dumps({"rows": len(rows), "manifestAdded": added, "manifestTotal": len(assets), "rowsPath": str(rows_path)}))
    else:
        print(json.dumps({"rows": len(rows), "rowsPath": str(rows_path), "manifest": "missing"}))


if __name__ == "__main__":
    main()
