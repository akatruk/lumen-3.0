#!/usr/bin/env python3
"""Idempotent locale overlay from existing English tags. Does not rewrite binaries."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "media" / "library"))
from localize import ensure_locales, locale_complete  # noqa: E402

MANIFEST = ROOT / "media" / "library" / "out" / "manifest.json"
OVERLAY = ROOT / "media" / "library" / "localized_overlay.json"


def main():
    data = json.loads(MANIFEST.read_text())
    assets = data["assets"] if isinstance(data, dict) else data
    rows = []
    complete = 0
    for asset in assets:
        before_ru = bool(asset.get("tags_ru"))
        before_zh = bool(asset.get("tags_zh"))
        filled = ensure_locales(dict(asset))
        if locale_complete(filled):
            complete += 1
        if before_ru and before_zh and asset.get("localized"):
            continue
        extra = {"id": asset["id"]}
        for key in ("tags_ru", "tags_zh", "localized", "conceptId"):
            if filled.get(key) and not asset.get(key):
                extra[key] = filled[key]
        if len(extra) > 1:
            rows.append(extra)
    OVERLAY.write_text(json.dumps({"version": "multilingual-library-v1", "assets": rows}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "manifest": len(assets),
        "overlayRows": len(rows),
        "completeAfterFill": complete,
        "overlay": str(OVERLAY),
    }))


if __name__ == "__main__":
    main()
