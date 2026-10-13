"""Register a newly approved asset into the locale overlay. No media copy."""
from __future__ import annotations

import json
from pathlib import Path

from localize import ensure_locales

OVERLAY = Path(__file__).resolve().parent / "localized_overlay.json"


def register_approved(asset: dict) -> dict:
    filled = ensure_locales(dict(asset))
    if not filled.get("id"):
        raise ValueError("asset id required")
    payload = {"version": "multilingual-library-v1", "assets": []}
    if OVERLAY.is_file():
        payload = json.loads(OVERLAY.read_text())
    rows = [row for row in payload.get("assets") or [] if row.get("id") != filled["id"]]
    rows.append({
        "id": filled["id"],
        "conceptId": filled.get("conceptId"),
        "tags_ru": filled.get("tags_ru") or [],
        "tags_zh": filled.get("tags_zh") or [],
        "localized": filled.get("localized") or {},
    })
    payload["assets"] = rows
    OVERLAY.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return filled
