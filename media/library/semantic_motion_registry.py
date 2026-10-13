"""Motion-component registry inside the existing media library.

Components are not binary assets. Selection is deterministic keyword match on
en / ru / zh tags. pgvector stays off (VISUAL_INTELLIGENCE_ENABLED=0). Do not
write these descriptions into asset_embeddings — that table is the CLIP space.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

CATALOG = Path(__file__).resolve().parent / "catalogs" / "semantic_motion_v14.json"
LOCALES = ("en-US", "ru-RU", "zh-CN")
LAYOUTS = ("full_frame", "speaker_visual", "overlay")


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def components() -> list[dict]:
    return list(load_catalog().get("components") or [])


def by_intent(intent: str) -> dict | None:
    for row in components():
        if row.get("visualIntent") == intent or row.get("componentId") == intent:
            return row
    return None


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").casefold()).strip()


def search_motion_components(query: str, *, locale: str | None = None, limit: int = 5) -> list[dict]:
    """Deterministic concept match. Works with pgvector disabled."""
    q = _fold(query)
    if not q:
        return []
    bucket = "tags_zh" if str(locale or "").startswith("zh") else "tags_ru" if str(locale or "").startswith("ru") else "tags"
    ranked: list[tuple[int, dict]] = []
    for row in components():
        score = 0
        fields = [row.get("description") or "", row.get("visualIntent") or ""]
        fields.extend(row.get("supportedConcepts") or [])
        fields.extend(row.get(bucket) or [])
        fields.extend(row.get("tags") or [])
        if bucket != "tags":
            fields.extend(row.get("tags_ru") or [])
            fields.extend(row.get("tags_zh") or [])
        for field in fields:
            folded = _fold(str(field))
            if not folded:
                continue
            if folded in q or q in folded:
                score += 3
            else:
                for token in folded.split():
                    if len(token) >= 2 and token in q:
                        score += 1
        if score:
            ranked.append((score, row))
    ranked.sort(key=lambda item: (-item[0], item[1].get("componentId") or ""))
    return [row for _, row in ranked[:limit]]
