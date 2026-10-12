#!/usr/bin/env python3
"""Merge premium-motion V4 calibration assets into manifest.json (idempotent)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
MANIFEST = OUT / "manifest.json"
RECIPE = ROOT / "recipes" / "premium-motion-v4-calibration.json"
REPORT = OUT / "premium-motion-v4-calibration-report.json"


def row(asset: dict, qa: dict | None) -> dict:
    file_rel = asset["file"]
    item = {
        "id": asset["id"],
        "type": "video",
        "category": asset["category"],
        "tags": asset["tags"],
        "tags_ru": asset.get("tags_ru") or [],
        "tags_zh": asset.get("tags_zh") or [],
        "description": {
            "en": f"Premium Remotion motion clip ({asset['role']}), four seconds, no type.",
            "ru": f"Премиальный Remotion-клип ({asset['role']}), четыре секунды, без текста.",
            "zh": f"高级 Remotion 动态素材（{asset['role']}），四秒，无文字。",
        },
        "file": file_rel,
        "aspectRatio": "9:16",
        "composition": "center",
        "background": "opaque" if asset["role"] == "bg" else "transparent",
        "qualityScore": 0.92,
        "textSafe": True,
        "source": "remotion",
        "duration": 4.0,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "loopable": bool(asset.get("loopable")),
        "visualFamily": "deterministic_motion",
        "batch": "premium-motion-v4-calibration",
        "sceneRoles": asset.get("sceneRoles") or [],
        "energy": asset.get("energy") or "medium",
        "emotion": [],
        "motionPotential": "high" if asset["role"] in {"hero", "scene", "concept"} else "low",
        "recommendedTreatments": (
            ["behind_type"] if asset["role"] == "bg"
            else ["kinetic_overlay"] if asset["role"] in {"fg", "concept"}
            else ["cutaway", "kinetic_overlay"]
        ),
        "matchMode": "decorative" if asset["role"] in {"fg", "bg"} else "conceptual",
        "hasAlpha": asset["role"] != "bg",
        "codec": "vp9",
        "pixelFormat": "yuva420p" if asset["role"] != "bg" else "yuv420p",
        "reviewStatus": "approved",
    }
    if qa:
        item["sha256"] = qa.get("sha256")
        item["bytes"] = qa.get("bytes")
    return item


def main():
    recipe = json.loads(RECIPE.read_text())
    report = json.loads(REPORT.read_text()) if REPORT.exists() else {"results": []}
    by_id = {r["id"]: r for r in report.get("results", [])}
    approved = set(report.get("approved") or [a["id"] for a in recipe["assets"]])

    data = json.loads(MANIFEST.read_text())
    assets = data["assets"] if isinstance(data, dict) else data
    existing = {a["id"]: i for i, a in enumerate(assets)}
    added = updated = 0
    for asset in recipe["assets"]:
        if asset["id"] not in approved:
            continue
        item = row(asset, by_id.get(asset["id"]))
        if asset["id"] in existing:
            assets[existing[asset["id"]]] = {**assets[existing[asset["id"]]], **item}
            updated += 1
        else:
            assets.append(item)
            added += 1
    if isinstance(data, dict):
        data["assets"] = assets
        data["version"] = data.get("version") or 1
        MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    else:
        MANIFEST.write_text(json.dumps(assets, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"added": added, "updated": updated, "total": len(assets)}, indent=2))


if __name__ == "__main__":
    main()
