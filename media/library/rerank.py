"""Stage-2 semantic rerank.

Stage 1 already collected keyword hits plus a few vector-only candidates.
This pass keeps spoken-concept matches and rejects a domain clash.
Cosine does not outrank a keyword hit.
"""
from __future__ import annotations

_INVESTMENT = frozenset({
    'shareholder', 'shareholders', 'capital', 'equity', 'ownership', 'boardroom',
    'dividend', 'shares', 'investor', 'investment',
})
_IMMIGRATION = frozenset({
    'passport', 'visa', 'suitcase', 'luggage', 'immigration', 'relocation', 'doorway',
})
_REAL_ESTATE = frozenset({
    'apartment', 'condo', 'doorway', 'balcony', 'interior', 'keys',
})
_BUSINESS = _INVESTMENT | frozenset({
    'meeting', 'boardroom', 'office', 'contract', 'document', 'documents', 'company',
})


def _tokens(asset: dict) -> set[str]:
    parts = [
        asset.get('id') or '',
        asset.get('category') or '',
        asset.get('conceptId') or '',
        asset.get('description') or '',
        ' '.join(asset.get('tags') or []),
        ' '.join(asset.get('tags_ru') or []),
        ' '.join(asset.get('tags_zh') or []),
        ' '.join(asset.get('situations') or []),
        ' '.join(asset.get('actions') or []),
    ]
    blob = ' '.join(str(part) for part in parts).casefold().replace('_', ' ').replace('-', ' ')
    return {word for word in blob.split() if word}


def domain_conflict(words, asset: dict) -> bool:
    """Investment speech does not take a passport, a suitcase, or an empty flat."""
    query = {str(word).casefold() for word in words or ()}
    asset_words = _tokens(asset)
    asset_id = str(asset.get('id') or '')
    query_investment = bool(query & _INVESTMENT)
    query_immigration = bool(query & _IMMIGRATION)
    asset_immigration = bool(asset_words & _IMMIGRATION) or 'passport' in asset_id or 'suitcase' in asset_id
    asset_investment = bool(asset_words & _INVESTMENT)
    if query_investment and not query_immigration and asset_immigration and not asset_investment:
        return True
    query_property = bool(query & _REAL_ESTATE)
    asset_property = bool(asset_words & _REAL_ESTATE)
    if query_investment and not query_property and not query_immigration and asset_property and not (asset_words & _BUSINESS):
        return True
    return False


def rerank_candidates(pool, *, words, bonuses=None, limit=8, penalties=None):
    """Return assets in semantic order. `pool` items are (stage_score, lexical, asset)."""
    bonuses = bonuses or {}
    penalties = penalties or {}
    ranked = []
    for stage_score, lexical, asset in pool:
        if domain_conflict(words, asset):
            continue
        penalty = float(penalties.get(asset.get('id')) or 0.0)
        if not lexical:
            # A neighbor in CLIP space is not evidence the asset explains the line.
            continue
        # Keyword score already includes quality, role, composition, text-safe area, recent use.
        score = float(stage_score) - penalty
        ranked.append((score, asset.get('qualityScore') or 0, 0.0, asset))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [asset for _, _, _, asset in ranked[:limit]]
