"""Hybrid search stays off by default and still applies the quality gate."""
import json

from backend.config import settings
from media.library.search import search_assets


def _manifest(tmp_path):
    assets = [
        {
            'id': 'plate_office',
            'type': 'image',
            'status': 'active',
            'qualityScore': 0.8,
            'tags': ['office'],
            'file': 'a.png',
            'visualFamily': 'photography',
            'sceneRoles': ['background'],
            'composition': 'left_weighted',
            'textSafeAreas': ['right'],
        },
        {
            'id': 'bad_rejected',
            'type': 'image',
            'status': 'rejected',
            'qualityScore': 0.95,
            'tags': ['family', 'relocation'],
            'file': 'b.png',
            'visualFamily': 'photography',
        },
        {
            'id': 'held_quarantine',
            'type': 'image',
            'status': 'quarantined',
            'qualityScore': 0.95,
            'tags': ['family'],
            'file': 'c.png',
        },
        {
            'id': 'l3d_passport',
            'type': 'video',
            'status': 'active',
            'qualityScore': 0.9,
            'tags': ['family', 'passport'],
            'file': 'd.webm',
            'visualFamily': 'premium_3d',
        },
    ]
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps({'assets': assets}), encoding='utf-8')
    return path


def test_flag_off_keeps_keyword_results(tmp_path, monkeypatch):
    path = _manifest(tmp_path)
    monkeypatch.setattr(settings, 'visual_intelligence_enabled', False)
    monkeypatch.setattr('media.library.search._vector_bonuses', lambda query: {'plate_office': 0.99})
    hits = search_assets('family relocation', limit=5, path=path)
    ids = [hit['id'] for hit in hits]
    assert 'bad_rejected' not in ids
    assert 'held_quarantine' not in ids
    assert 'l3d_passport' in ids
    assert 'plate_office' not in ids


def test_hybrid_blocks_rejected_experimental_3d_and_cosine_only_hits(tmp_path, monkeypatch):
    path = _manifest(tmp_path)
    monkeypatch.setattr(settings, 'visual_intelligence_enabled', True)
    monkeypatch.setattr('media.library.search._vector_bonuses', lambda query: {
        'plate_office': 0.99,
        'bad_rejected': 0.99,
        'held_quarantine': 0.99,
        'l3d_passport': 0.99,
    })
    hits = search_assets('family planning relocation', limit=5, path=path)
    ids = [hit['id'] for hit in hits]
    assert ids == []
