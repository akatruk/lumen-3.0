"""Query-time visual retrieval. Asset vectors are precomputed; this encodes the query only."""
from __future__ import annotations

from .experience_embeddings import content_hash, embed_text
from .experience_memory import similar_library_assets

_QUERY_CACHE: dict[str, dict[str, float]] = {}
_CACHE_LIMIT = 64


def asset_similarities(query: str, limit: int = 48) -> dict[str, float]:
    cleaned = ' '.join((query or '').split())
    if not cleaned:
        return {}
    key = content_hash(cleaned.casefold())
    cached = _QUERY_CACHE.get(key)
    if cached is not None:
        return cached
    spec = embed_text(cleaned)
    found = similar_library_assets(spec['embedding'], limit=limit)
    if len(_QUERY_CACHE) >= _CACHE_LIMIT:
        _QUERY_CACHE.pop(next(iter(_QUERY_CACHE)))
    _QUERY_CACHE[key] = found
    return found
