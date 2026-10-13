"""Director V11 — semantic intelligence: investment speech must not get immigration visuals."""
from __future__ import annotations

from backend.director_v11 import (
    apply_semantic_intelligence,
    build_semantic_map,
    detect_topic_domain,
    validate_semantic_alignment,
)
from backend.director_semantics import enrich_plan_from_transcript
from backend.director_v8 import expand_plan_for_duration


ORIGIN1_TRANSCRIPT = [
    {
        'start': 0.0, 'end': 3.333,
        'en': 'Many people think that foreign investment companies only change the language of China',
        'original': 'Many people think that foreign investment companies only change the language of China',
    },
    {
        'start': 3.333, 'end': 6.667,
        'en': 'The first step of a Chinese investment company is completely different',
        'original': 'The first step of a Chinese investment company is completely different',
    },
    {
        'start': 6.667, 'end': 10.0,
        'en': 'The core of Chinese investment companies is the capital investment',
        'original': 'The core of Chinese investment companies is the capital investment',
    },
    {
        'start': 10.0, 'end': 13.333,
        'en': 'Under the leadership of the government no need to pay immediately',
        'original': 'Under the leadership of the government no need to pay immediately',
    },
    {
        'start': 13.333, 'end': 16.667,
        'en': 'The shareholder responsibility and the capital judgment will be around it',
        'original': 'The shareholder responsibility and the capital judgment will be around it',
    },
    {
        'start': 16.667, 'end': 20.0,
        'en': 'The first thing in Thailand is not money but structure',
        'original': 'The first thing in Thailand is not money but structure',
    },
]


def _base_plan(locale='en-US'):
    return {
        'language': locale,
        'visualSeed': 42,
        'scenes': [
            {
                'sceneId': 'hook',
                'speaker': {'layout': 'speaker_closeup', 'framing': 'fullscreen'},
                'background': {}, 'typography': {}, 'execution': {},
            },
            {
                'sceneId': 'beside',
                'speaker': {'layout': 'speaker_split_left', 'framing': 'split'},
                'background': {},
                'typography': {
                    'cards': [
                        {'title': 'Goals', 'explanation': 'where you are going and why'},
                        {'title': 'Family', 'explanation': 'who travels with you and when'},
                        {'title': 'Budget', 'explanation': 'what the program can realistically cost'},
                    ],
                    'cardMode': 'progressive_one',
                },
                'execution': {},
                'query': 'family home doorway relocation',
            },
            {
                'sceneId': 'context',
                'speaker': {'layout': 'speaker_with_foreground', 'framing': 'split'},
                'background': {}, 'typography': {}, 'execution': {},
                'query': 'family home doorway relocation',
                'semanticMotion': {
                    'keyword': 'relocation',
                    'file': 'motion/premium/pm_scene_mobility_001.webm',
                    'assetId': 'pm_scene_mobility_001',
                },
            },
            {
                'sceneId': 'steps',
                'speaker': {'layout': 'speaker_with_diagram', 'framing': 'pip'},
                'background': {},
                'typography': {
                    'stepsTitle': 'Guided process',
                    'steps': ['Consult', 'Program', 'Documents'],
                },
                'execution': {},
            },
            {
                'sceneId': 'return',
                'speaker': {'layout': 'speaker_fullscreen', 'framing': 'fullscreen'},
                'background': {}, 'typography': {}, 'execution': {},
            },
        ],
        'heroObject': 'passport',
    }


def test_origin1_domain_is_investment():
    assert detect_topic_domain(ORIGIN1_TRANSCRIPT, 'en-US') == 'investment'
    sm = build_semantic_map(ORIGIN1_TRANSCRIPT, 'en-US')
    assert 'capital_investment' in sm['conceptIds']
    assert 'thailand_company_structure' in sm['conceptIds']
    assert 'shareholder_responsibility' in sm['conceptIds']
    assert 'passport_document' not in sm['conceptIds']
    assert 'relocation_move' not in sm['conceptIds']


def test_origin1_no_immigration_cards_or_queries():
    plan = _base_plan()
    out = apply_semantic_intelligence(plan, ORIGIN1_TRANSCRIPT, locale='en-US')
    assert out['semanticIntelligence']['primaryDomain'] == 'investment'
    beside = next(s for s in out['scenes'] if s['sceneId'] == 'beside')
    cards = (beside.get('typography') or {}).get('cards') or []
    assert cards
    blob = ' '.join(f"{c['title']} {c['explanation']}" for c in cards).lower()
    assert 'travels with you' not in blob
    assert 'where you are going' not in blob
    assert any('capital' in c['title'].lower() or 'shareholder' in c['title'].lower()
               or 'control' in c['title'].lower() for c in cards)
    for scene in out['scenes']:
        q = str(scene.get('query') or '').lower()
        assert 'relocation' not in q
        assert 'residence permit' not in q
        sm = scene.get('semanticMotion') or {}
        assert sm.get('keyword') != 'relocation'
    assert out.get('heroObject') != 'passport'
    validation = out['semanticValidation']
    assert validation['ok'] is True
    assert validation['issueCount'] == 0


def test_immigration_speech_keeps_immigration_cards():
    transcript = [{
        'start': 0, 'end': 8,
        'en': 'Planning a relocation? You need a passport and residence permit for your family.',
        'original': 'Planning a relocation? You need a passport and residence permit for your family.',
    }]
    assert detect_topic_domain(transcript, 'en-US') == 'immigration'
    plan = _base_plan()
    out = apply_semantic_intelligence(plan, transcript, locale='en-US')
    beside = next(s for s in out['scenes'] if s['sceneId'] == 'beside')
    cards = (beside.get('typography') or {}).get('cards') or []
    assert any('Family' in c['title'] or 'Goals' in c['title'] for c in cards)


def test_enrich_plus_expand_origin1_no_relocation_query():
    plan = {
        'language': 'en-US',
        'visualSeed': 42,
        'scenes': [
            {'sceneId': sid, 'speaker': {}, 'background': {}, 'typography': {}, 'execution': {}}
            for sid in ('hook', 'residency', 'consult', 'beside', 'steps', 'return')
        ],
    }
    enriched = enrich_plan_from_transcript(plan, ORIGIN1_TRANSCRIPT, locale='en-US')
    beside = next(s for s in enriched['scenes'] if s['sceneId'] == 'beside')
    cards = (beside.get('typography') or {}).get('cards') or []
    blob = ' '.join(f"{c.get('title')} {c.get('explanation')}" for c in cards).lower()
    assert 'travels with you' not in blob

    expanded = expand_plan_for_duration(
        enriched, duration_seconds=60, transcript=ORIGIN1_TRANSCRIPT, locale='en-US',
    )
    assert expanded.get('topicDomain') == 'investment'
    assert len(expanded['scenes']) == 10
    for scene in expanded['scenes']:
        q = str(scene.get('query') or '').lower()
        assert 'relocation' not in q, scene.get('sceneId')
        assert 'family home doorway' not in q
    final = apply_semantic_intelligence(expanded, ORIGIN1_TRANSCRIPT, locale='en-US')
    assert final['semanticValidation']['ok'] is True


def test_ru_zh_locale_packs():
    for locale, title in (('ru-RU', 'Капитал'), ('zh-CN', '资本')):
        out = apply_semantic_intelligence(_base_plan(locale), ORIGIN1_TRANSCRIPT, locale=locale)
        beside = next(s for s in out['scenes'] if s['sceneId'] == 'beside')
        cards = (beside.get('typography') or {}).get('cards') or []
        assert cards[0]['title'] == title


def test_residency_id_does_not_keep_an_immigration_query_on_investment_speech():
    from backend.director_v8 import query_respecting_source
    scene = {
        'sceneId': 'residency',
        'query': 'family home doorway relocation',
        'semanticConcepts': [{
            'conceptId': 'thailand_company_structure',
            'domain': 'investment',
            'evidence': 'Thailand company shareholder structure',
        }],
    }
    assert query_respecting_source(scene) == 'Thailand company shareholder structure'
    assert query_respecting_source({
        'sceneId': 'residency',
        'query': 'corporate boardroom shareholders meeting',
        'semanticConcepts': [{'domain': 'investment', 'evidence': 'ignored once the query is already corporate'}],
    }) == 'corporate boardroom shareholders meeting'


def test_validate_flags_contaminated_plan():
    sm = build_semantic_map(ORIGIN1_TRANSCRIPT, 'en-US')
    dirty = {
        'scenes': [{
            'sceneId': 'beside',
            'query': 'family home doorway relocation',
            'typography': {
                'cards': [{'title': 'Family', 'explanation': 'who travels with you and when'}],
            },
            'semanticMotion': {'keyword': 'relocation', 'file': 'static/immigration/imm_obj_suitcase.svg'},
        }],
        'heroObject': 'passport',
    }
    report = validate_semantic_alignment(dirty, sm)
    assert report['ok'] is False
    assert report['issueCount'] >= 3
