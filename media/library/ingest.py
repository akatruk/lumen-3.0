"""Register a new asset. Incomplete locales stay PENDING_LOCALIZATION."""
from __future__ import annotations

import json
from pathlib import Path

from contract import validate_asset
from localize import ensure_locales

OVERLAY = Path(__file__).resolve().parent / "localized_overlay.json"


def register_approved(asset: dict) -> dict:
    filled = ensure_locales(dict(asset))
    if not filled.get("id"):
        raise ValueError("asset id required")
    filled["multilingualContract"] = "required"
    filled.setdefault("supportedLocales", ["en-US", "ru-RU", "zh-CN"])
    errors = validate_asset(filled)
    if errors:
        filled["qualityStatus"] = "PENDING_LOCALIZATION"
        filled["contractErrors"] = errors
        return filled
    filled["qualityStatus"] = filled.get("qualityStatus") or "production_ready"
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
        "supportedLocales": filled.get("supportedLocales"),
        "qualityStatus": filled.get("qualityStatus"),
    })
    payload["assets"] = rows
    OVERLAY.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    filled.pop("contractErrors", None)
    return filled
