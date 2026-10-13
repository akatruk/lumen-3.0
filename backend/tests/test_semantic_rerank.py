"""Semantic rerank keeps the spoken concept ahead of cosine."""
import json

from backend.config import settings
from media.library.rerank import domain_conflict, rerank_candidates
from media.library.search import search_assets


def _asset(asset_id, tags, quality=0.8, family='photography'):
    return {
        'id': asset_id,
        'type': 'image',
        'status': 'active',
        'qualityScore': quality,
        'tags': tags,
        'file': f'{asset_id}.png',
        'visualFamily': family,
        'sceneRoles': ['background'],
    }


def test_investment_speech_rejects_passport_and_empty_apartment():
    assert domain_conflict(['shareholder', 'capital', 'thailand'], _asset('passport_open', ['passport', 'visa']))
    assert domain_conflict(['shareholder', 'boardroom'], _asset('empty_flat', ['apartment', 'interior', 'empty']))
    assert not domain_conflict(
        ['shareholder', 'boardroom'],
        _asset('board_meeting', ['shareholder', 'boardroom', 'meeting']),
    )


def test_cosine_does_not_outrank_a_keyword_hit():
    board = _asset('board_meeting', ['shareholder', 'boardroom'])
    deadline = _asset('deadline_motion', ['deadline', 'timeline'], family='deterministic_motion')
    ranked = rerank_candidates(
        [(4.2, True, board), (0.0, False, deadline)],
        words=['shareholder', 'capital'],
        bonuses={'deadline_motion': 0.91, 'board_meeting': 0.2},
        limit=5,
    )
    assert [item['id'] for item in ranked] == ['board_meeting']


def test_one_irrelevant_flag_does_not_bury_the_asset():
    board = _asset('board_meeting', ['shareholder'])
    other = _asset('other_meeting', ['shareholder', 'meeting'])
    ranked = rerank_candidates(
        [(4.0, True, board), (3.2, True, other)],
        words=['shareholder'],
        penalties={'board_meeting': 0.0},
        limit=2,
    )
    assert ranked[0]['id'] == 'board_meeting'


def test_repeated_asset_failure_can_reorder_close_scores():
    board = _asset('board_meeting', ['shareholder'])
    other = _asset('other_meeting', ['shareholder'])
    ranked = rerank_candidates(
        [(4.0, True, board), (3.8, True, other)],
        words=['shareholder'],
        penalties={'board_meeting': 0.35},
        limit=2,
    )
    assert ranked[0]['id'] == 'other_meeting'


def test_hybrid_search_drops_passport_for_shareholder_query(tmp_path, monkeypatch):
    assets = [
        _asset('passport_open', ['passport', 'visa', 'family']),
        _asset('board_meeting', ['shareholder', 'boardroom', 'meeting']),
        {
            'id': 'l3d_passport',
            'type': 'video',
            'status': 'active',
            'qualityScore': 0.99,
            'tags': ['passport', 'shareholder'],
            'file': 'p.webm',
            'visualFamily': 'premium_3d',
        },
    ]
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps({'assets': assets}), encoding='utf-8')
    monkeypatch.setattr(settings, 'visual_intelligence_enabled', True)
    monkeypatch.setattr('media.library.search._vector_bonuses', lambda query: {
        'passport_open': 0.95,
        'board_meeting': 0.1,
        'l3d_passport': 0.99,
    })
    monkeypatch.setattr('backend.experience_memory.asset_relevance_penalties', lambda **kwargs: {})
    hits = search_assets('shareholder capital boardroom', limit=5, path=path)
    ids = [hit['id'] for hit in hits]
    assert ids[0] == 'board_meeting'
    assert 'passport_open' not in ids
    assert 'l3d_passport' not in ids
