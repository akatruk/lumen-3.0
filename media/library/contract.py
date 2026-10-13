"""Multilingual publication contract. Legacy rows are reported, not failed."""
from __future__ import annotations

LOCALES = ("en-US", "ru-RU", "zh-CN")
HIDDEN = frozenset({"quarantined", "rejected", "duplicate", "corrupt"})


def _text(block, key):
    if not isinstance(block, dict):
        return ""
    return str(block.get(key) or "").strip()


def strict_row(asset: dict) -> bool:
    if asset.get("multilingualContract") == "required":
        return True
    return (asset.get("qualityStatus") or "") == "production_ready"


def validate_asset(asset: dict) -> list[str]:
    errors = []
    asset_id = asset.get("id") or asset.get("assetId")
    if not asset_id:
        errors.append("missing_id")
    if not asset.get("file") and asset.get("type") not in ("motion_preset", "component"):
        errors.append("missing_storage")
    status = asset.get("status") or ""
    quality = asset.get("qualityStatus") or ""
    if status in HIDDEN and quality == "production_ready":
        errors.append("rejected_marked_production")
    family = asset.get("visualFamily") or ""
    if family == "premium_3d" and quality == "production_ready" and not asset.get("qualityGateApproved"):
        errors.append("unapproved_3d")
    if not strict_row(asset):
        return errors
    if not asset.get("conceptId"):
        errors.append("missing_concept_id")
    locales = asset.get("supportedLocales") or LOCALES
    for locale in LOCALES:
        if locale not in locales:
            errors.append("unsupported_locale:" + locale)
        block = (asset.get("localized") or {}).get(locale) or {}
        if not _text(block, "title") or not _text(block, "description"):
            errors.append("missing_localized:" + locale)
    return errors


def locale_gaps(asset: dict) -> list[str]:
    gaps = []
    localized = asset.get("localized") or {}
    for locale in LOCALES:
        block = localized.get(locale) or {}
        if not _text(block, "title") or not _text(block, "description"):
            gaps.append(locale)
    if not asset.get("conceptId"):
        gaps.append("conceptId")
    return gaps


def validate_library(assets: list[dict]) -> dict:
    seen = {}
    duplicates = []
    legacy = []
    strict_fail = []
    locale_gap_count = 0
    for asset in assets:
        asset_id = asset.get("id") or asset.get("assetId")
        if asset_id:
            if asset_id in seen:
                duplicates.append(asset_id)
            seen[asset_id] = True
        status = asset.get("status") or ""
        if status not in HIDDEN and locale_gaps(asset):
            locale_gap_count += 1
        errors = validate_asset(asset)
        if not errors:
            continue
        row = {"id": asset_id, "errors": errors, "strict": strict_row(asset)}
        if strict_row(asset):
            strict_fail.append(row)
        else:
            legacy.append(row)
    return {
        "assets": len(assets),
        "duplicateIds": duplicates,
        "legacyViolations": len(legacy),
        "legacyLocaleGaps": locale_gap_count,
        "strictFailures": strict_fail,
        "ok": not duplicates and not strict_fail,
    }
