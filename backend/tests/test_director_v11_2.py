"""Director V11.2 — scrub invented '2 Shareholders' + face-safe composition."""
from __future__ import annotations

from backend.director_v11 import apply_semantic_intelligence, _steps_for_domain
from backend.director_v11_1 import apply_factual_business_motion
from backend.director_v11_2 import (
    apply_composition_repair,
    scrub_fake_headcount_labels,
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


def test_investment_steps_never_shareholders_noun():
    steps = _steps_for_domain('investment', 'en-US')
    assert steps is not None
    assert 'Shareholders' not in steps['steps']
    assert 'Structure' in steps['steps']
    ru = _steps_for_domain('investment', 'ru-RU')
    assert ru and 'Акционеры' not in ru['steps']
    zh = _steps_for_domain('investment', 'zh-CN')
    assert zh and '股东' not in zh['steps']


def test_scrub_removes_numbered_shareholders_step():
    plan = {
        'language': 'en-US',
        'scenes': [{
            'sceneId': 'steps',
            'typography': {
                'stepsTitle': 'Formation path',
                'steps': ['Capital', 'Shareholders', 'Control'],
            },
        }],
        'businessMotionUsage': [],
    }
    out = scrub_fake_headcount_labels(plan, locale='en-US')
    steps = (out['scenes'][0].get('typography') or {}).get('steps') or []
    assert 'Shareholders' not in steps
    assert steps[1] == 'Structure'
    assert any(r.get('from') == 'Shareholders' for r in out.get('headcountScrub') or [])


def test_no_two_shareholders_after_v11_2():
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
            {
                'sceneId': 'steps',
                'typography': {
                    'stepsTitle': 'Formation path',
                    'steps': ['Capital', 'Shareholders', 'Control'],
                },
                'execution': {},
            },
            {'sceneId': 'residency', 'typography': {}, 'execution': {}, 'speaker': {'layout': 'speaker_split_right'}},
            {'sceneId': 'proof', 'typography': {}, 'execution': {}},
        ],
    }
    plan = apply_semantic_intelligence(plan, FULL_ORIGIN1, locale='en-US')
    plan = apply_factual_business_motion(plan, FULL_ORIGIN1, locale='en-US')
    out = apply_composition_repair(plan, FULL_ORIGIN1, locale='en-US')
    blob = json_blob(out)
    assert '2 Shareholders' not in blob
    assert '2 акционер' not in blob.lower()
    assert '两名股东' not in blob
    # Evidenced ≥3 remains.
    beside = next(s for s in out['scenes'] if s['sceneId'] == 'beside')
    titles = ' '.join(c.get('title', '') for c in (beside.get('typography') or {}).get('cards') or [])
    assert '≥3' in titles or '3' in titles
    # Face-safe stamps present on risk overlays.
    residency = next(s for s in out['scenes'] if s['sceneId'] == 'residency')
    bm = residency.get('businessMotion') or {}
    if bm:
        assert bm.get('faceSafe') is True
        assert bm.get('placement') in ('media_column', 'side_rail', 'below_face_band', 'upper_band_cutaway')
        assert bm.get('mediaSide') in ('left', 'right')
        # speaker_split_right → graphics on left
        if 'split_right' in ((residency.get('speaker') or {}).get('layout') or ''):
            assert bm.get('mediaSide') == 'left'
    assert out.get('factualGrounding', {}).get('ok') is True


def test_zh_ru_steps_scrub():
    for locale, bad, good in (
        ('ru-RU', 'Акционеры', 'Структура'),
        ('zh-CN', '股东', '结构'),
    ):
        plan = {
            'language': locale,
            'scenes': [{
                'sceneId': 'steps',
                'typography': {'steps': ['X', bad, 'Y']},
            }],
        }
        out = scrub_fake_headcount_labels(plan, locale=locale)
        steps = (out['scenes'][0].get('typography') or {}).get('steps') or []
        assert bad not in steps
        assert good in steps


def json_blob(plan: dict) -> str:
    import json
    return json.dumps(plan, ensure_ascii=False)
