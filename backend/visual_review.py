"""What a reviewed asset actually shows.

Search can suggest an asset. This module decides whether the picture is
allowed for a quote. A query string that also appears in the quote is not
evidence. An unreviewed asset is not eligible.
"""
from __future__ import annotations

import json
from pathlib import Path

_PATH = Path(__file__).with_name("visual_reviews.json")


def _rows() -> dict:
    rows = json.loads(_PATH.read_text(encoding="utf-8"))["assets"]
    index = _library_index()
    for asset_id, row in index.items():
        rows.setdefault(asset_id, row)
    return rows


def _library_index() -> dict:
    try:
        from .library_clips import library_root
        path = library_root() / "visual-index.json"
    except Exception:
        return {}
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    assets = payload.get("assets") if isinstance(payload, dict) else None
    return assets if isinstance(assets, dict) else {}


def _fires(terms: list[str], quote: str) -> bool:
    folded = quote.lower()
    return any(term.lower() in folded for term in terms)


def _clause_ok(clause: dict, quote: str) -> bool:
    required = clause.get("all") or []
    if not required:
        return False
    return _fires(required, quote) and all(term.lower() in quote.lower() for term in required)


def review_of(asset_id: str | None) -> dict | None:
    if not asset_id:
        return None
    return _rows().get(asset_id)


def picture_supports(asset_id: str | None, quote: str) -> bool:
    row = review_of(asset_id)
    if not row or row.get("status") != "accepted":
        return False
    if "frameReviewed" in row and not row.get("frameReviewed"):
        return False
    for concept, terms in (row.get("exclude") or {}).items():
        if _fires(terms, quote or ""):
            return False
    return any(_clause_ok(clause, quote or "") for clause in row.get("support") or [])


def _matching_clause(row: dict, quote: str) -> dict | None:
    for clause in row.get("support") or []:
        if _clause_ok(clause, quote):
            return clause
    return None


def passage_query(quote: str) -> dict | None:
    """Search text for this quote, taken from the reviewed clause, not the template beat."""
    for asset_id, row in _rows().items():
        if row.get("status") != "accepted":
            continue
        clause = _matching_clause(row, quote or "")
        if not clause:
            continue
        return {
            "assetId": asset_id,
            "visualRole": clause.get("id") or "",
            "query": clause.get("query") or "",
        }
    return None


def select_reviewed(quote: str, seen: set[str]) -> dict | None:
    """One accepted picture whose reviewed content matches this quote."""
    for asset_id, row in _rows().items():
        if asset_id in seen or row.get("status") != "accepted":
            continue
        return_file = row.get("file")
        if not return_file or str(return_file).endswith(".tsx"):
            continue
        clause = _matching_clause(row, quote or "")
        if clause is None:
            continue
        return {
            "assetId": asset_id,
            "file": return_file,
            "type": row.get("type") or "video",
            "kind": row.get("kind"),
            "visualConcept": clause.get("id") or "",
            "visualGrounding": {
                "reviewed": True,
                "roles": [clause.get("id")] if clause.get("id") else [],
                "observed": row.get("visible") or "",
                "marks": list(row.get("marks") or []),
            },
        }
    return None
