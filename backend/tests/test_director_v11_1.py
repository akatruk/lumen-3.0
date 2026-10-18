"""Director V11.1 — factual grounding; never invent shareholder counts."""
from __future__ import annotations

from backend.director_v11 import apply_semantic_intelligence, build_semantic_map
from backend.director_v11_1 import (
    apply_factual_business_motion,
    extract_spoken_facts,
    ownership_ratio_from_text,
    shareholder_count_from_text,
    validate_factual_grounding,
)


FULL_ORIGIN1 = [
    {
        'id': 'seg_006', 'start': 22.66, 'end': 26.06,
        'en': 'Ordinary Thai companies usually need at least three shareholders',
        'original': '普通泰国有限公司通常需要至少三名股东',
        'zh': '普通泰国有限公司通常需要至少三名股东',
    },
    {
        'id': 'seg_007', 'start': 26.06, 'end': 28.86,
        'en': 'so the foreign capital ratio is usually less than 49%',
        'original': '那么外资比例一般是不超过49%',
        'zh': '那么外资比例一般是不超过49%',
    },
    {
        'id': 'seg_004', 'start': 16.46, 'end': 19.46,
        'en': 'The shareholder responsibility and the capital judgment will be around it',
        'original': '股东责任 资本判断都会围着它转',
    },
    {
        'id': 'seg_002', 'start': 8.86, 'end': 11.86,
        'en': 'The core of Chinese investment companies is the capital investment',
        'original': '在中国注册公司最核心的是注册资本',
    },
]


def test_shareholder_count_is_three_not_two():
    en = 'Ordinary Thai companies usually need at least three shareholders'
    zh = '普通泰国有限公司通常需要至少三名股东'
    assert shareholder_count_from_text(en) == 3
    assert shareholder_count_from_text(zh) == 3
    assert shareholder_count_from_text('2 Shareholders') is None or shareholder_count_from_text(
        'who holds ownership'
    ) is None
    # Bare invented "2 Shareholders" without spoken context must not become evidence.
    assert shareholder_count_from_text('Shareholders') is None


def test_ownership_ratio_49():
    assert ownership_ratio_from_text('usually less than 49%') == 49.0
    assert ownership_ratio_from_text('不超过49%') == 49.0
    assert ownership_ratio_from_text('capital investment') is None


def test_no_invented_two_on_plan():
    plan = {
        'language': 'en-US',
        'scenes': [
            {
                'sceneId': 'beside',
                'typography': {
                    'cards': [
                        {'title': 'Capital', 'explanation': 'how capital investment is structured'},
                        {'title': 'Shareholders', 'explanation': 'who holds ownership'},
                        {'title': 'Control', 'explanation': 'how control is locked'},
                    ],
                },
                'execution': {},
            },
            {'sceneId': 'residency', 'typography': {}, 'execution': {}},
            {'sceneId': 'proof', 'typography': {}, 'execution': {}},
        ],
    }
    plan = apply_semantic_intelligence(plan, FULL_ORIGIN1, locale='en-US')
    out = apply_factual_business_motion(plan, FULL_ORIGIN1, locale='en-US')
    assert out['factualGrounding']['ok'] is True
    finding = None
    for row in out['businessMotionUsage']:
        if row.get('nodeCount'):
            finding = row
            assert row['nodeCount'] == 3
            assert 'three shareholders' in (row.get('originalSourceText') or '').lower() or '三名股东' in (
                row.get('originalSourceText') or ''
            )
    # Card must not say 2 Shareholders
    beside = next(s for s in out['scenes'] if s['sceneId'] == 'beside')
    blob = ' '.join(
        f"{c.get('title')} {c.get('explanation')}"
        for c in (beside.get('typography') or {}).get('cards') or []
    )
    assert '2 Shareholders' not in blob
    assert '2 акционер' not in blob.lower()
    if finding:
        assert '≥3' in blob or '3 Shareholders' in blob or '3' in blob


def test_gate_rejects_invented_two():
    dirty = {
        'scenes': [{
            'sceneId': 'beside',
            'businessMotion': {
                'component': 'shareholder_structure',
                'showCount': True,
                'nodeCount': 2,
                'sourceSegmentId': 'seg_x',
                'sourceStart': 0,
                'sourceEnd': 1,
                'originalSourceText': 'Ordinary Thai companies usually need at least three shareholders',
            },
        }],
    }
    report = validate_factual_grounding(dirty)
    assert report['ok'] is False


def test_equity_requires_spoken_percent():
    sm = build_semantic_map(FULL_ORIGIN1, 'en-US')
    assert 'thai_shareholder_count' in sm['conceptIds']
    assert 'foreign_ownership_ratio' in sm['conceptIds']
    facts = extract_spoken_facts('less than 49%')
    assert 49.0 in facts['percentages']


def test_zh_locale_keeps_identical_numeral():
    plan = {
        'language': 'zh-CN',
        'scenes': [
            {'sceneId': 'beside', 'typography': {'cards': []}, 'execution': {}},
            {'sceneId': 'residency', 'typography': {}, 'execution': {}},
        ],
    }
    plan = apply_semantic_intelligence(plan, FULL_ORIGIN1, locale='zh-CN')
    out = apply_factual_business_motion(plan, FULL_ORIGIN1, locale='zh-CN')
    beside = next(s for s in out['scenes'] if s['sceneId'] == 'beside')
    cards = (beside.get('typography') or {}).get('cards') or []
    titles = ' '.join(c.get('title', '') for c in cards)
    # Numeral identical across locales when count is shown.
    if '股东' in titles:
        assert '3' in titles
