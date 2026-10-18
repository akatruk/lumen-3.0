"""Evidence gate: stock packs, scene windows, Chinese structures."""
from __future__ import annotations

from backend.director_evidence import apply_evidence_gate, drop_repeated_assets
from backend.director_quality_shadow import diagnose
from backend.director_v11 import apply_semantic_intelligence
from backend.director_v14 import _steps_from_quote, classify_quote


def _zh(pid, start, end, text):
    return {'id': pid, 'start': start, 'end': end, 'original': text, 'zh': text, 'text': text}


def test_stock_cards_drop_when_the_beat_does_not_say_them():
    rows = [
        _zh('a', 0, 3, '很多人第一次来咨询 先会问'),
        _zh('b', 34, 40, '有人关心最终入籍 也有人根本不准备搬家'),
    ]
    plan = {
        'language': 'zh-CN',
        'durationSeconds': 60,
        'beatWeights': [30, 6],
        'scenes': [
            {'sceneId': 'hook', 'typography': {}, 'execution': {'headline': '很多人第一次来咨询 先会问'}, 'background': {}},
            {
                'sceneId': 'beside',
                'typography': {
                    'cards': [
                        {'title': '目标', 'explanation': '迁往哪里以及为何出发'},
                        {'title': '家庭', 'explanation': '同行家人与时间安排'},
                        {'title': '预算', 'explanation': '项目费用是否可承受'},
                    ],
                    'cardMode': 'progressive_one',
                },
                'execution': {'headline': '目标', 'cardText': '目标 | 家庭 | 预算'},
                'background': {},
            },
        ],
    }
    out = apply_evidence_gate(plan, rows, locale='zh-CN')
    beside = out['scenes'][1]
    assert beside['typography']['cards'] == []
    assert beside['execution']['headline'] == ''
    assert out['scenes'][0]['execution']['headline'] == '很多人第一次来咨询 先会问'


def test_future_move_does_not_query_the_opening():
    rows = [
        _zh('a', 0, 2.5, '很多人第一次来咨询'),
        _zh('b', 38, 40, '也有人根本不准备搬家'),
    ]
    plan = {
        'language': 'zh-CN',
        'durationSeconds': 60,
        'beatWeights': [90, 1710],
        'scenes': [
            {
                'sceneId': 'hook',
                'query': 'family home doorway relocation',
                'background': {'assetId': 'people_door_001', 'file': 'static/people/people_door_001.png'},
                'speaker': {}, 'typography': {}, 'execution': {},
            },
            {
                'sceneId': 'context',
                'query': 'family home doorway relocation',
                'background': {'assetId': 'people_door_001'},
                'speaker': {}, 'typography': {}, 'execution': {},
            },
        ],
    }
    out = apply_semantic_intelligence(plan, rows, locale='zh-CN')
    hook = out['scenes'][0]
    assert 'doorway' not in str(hook.get('query') or '')
    assert not (hook.get('background') or {}).get('assetId')
    concepts = hook.get('semanticConcepts') or []
    assert all((c.get('end') or 0) < 10 for c in concepts)


def test_contrast_lands_on_the_scene_that_says_it():
    rows = [
        _zh('a', 0, 3, '很多人第一次来咨询'),
        _zh('b', 9.76, 12.76, '身份规划的第一步不是选国家'),
        _zh('c', 12.76, 16.0, '而是定义问题'),
    ]
    plan = {
        'language': 'zh-CN',
        'durationSeconds': 20,
        'beatWeights': [9, 11],
        'scenes': [
            {'sceneId': 'hook', 'typography': {}, 'execution': {}, 'background': {}},
            {'sceneId': 'problem', 'typography': {}, 'execution': {}, 'background': {}},
        ],
    }
    out = apply_evidence_gate(plan, rows, locale='zh-CN')
    assert out['scenes'][0]['typography'].get('cards') in (None, [])
    titles = [c['title'] for c in out['scenes'][1]['typography']['cards']]
    assert titles == ['选国家', '定义问题']
    assert out['scenes'][1]['typography']['cards'][0]['evidence']['sourceText']


def test_ordinal_layers_are_general_and_not_a_family_count():
    assert _steps_from_quote('三口之家去看房', 'zh') is None
    assert _steps_from_quote('申请费 律师费 和翻译费', 'zh') is None
    labels = _steps_from_quote('第一层叫材料 第二层叫时间 第三层叫费用', 'zh')
    assert labels == ['材料', '时间', '费用']
    assert classify_quote('三口之家', {'id': 'x', 'start': 0, 'end': 1}, locale='zh-CN') == []


def test_layers_stay_on_the_sentence_that_names_them():
    rows = [
        _zh('a', 0, 3, '第一层叫材料'),
        _zh('b', 14, 17, '第二层叫时间'),
        _zh('c', 28, 31, '第三层叫费用'),
    ]
    plan = {
        'language': 'zh-CN',
        'durationSeconds': 33,
        'beatWeights': [1, 1, 1],
        'scenes': [
            {'sceneId': 'early', 'typography': {}, 'execution': {}, 'background': {}},
            {'sceneId': 'mid', 'typography': {}, 'execution': {}, 'background': {}},
            {'sceneId': 'late', 'typography': {}, 'execution': {}, 'background': {}},
        ],
    }
    out = apply_evidence_gate(plan, rows, locale='zh-CN')
    timelines = [
        scene.get('semanticMotionV14')
        for scene in out['scenes']
        if (scene.get('semanticMotionV14') or {}).get('visualIntent') == 'process_timeline'
    ]
    assert len(timelines) == 1
    steps = timelines[0]['steps']
    assert [step['label'] for step in steps] == ['材料', '时间', '费用']
    assert steps[0]['at'] == 0
    assert steps[0]['until'] == 3
    assert steps[2]['at'] == 28
    assert steps[2]['until'] == 31
    assert all(not scene.get('steps') for scene in out['scenes'])
    assert '使用场景' not in json_dump(out)
    assert '步骤' not in json_dump(out)


def test_a_later_thought_is_not_inside_the_previous_layer():
    rows = [
        _zh('a', 2.4, 4.6, '第一层叫使用场景'),
        _zh('b', 16.52, 18.76, '第二层叫家庭结构'),
        _zh('c', 24.92, 27.32, '今天适合三口之家的方案'),
        _zh('d', 30.44, 32.2, '第三层叫代价'),
    ]
    plan = {
        'language': 'zh-CN',
        'durationSeconds': 34,
        'beatWeights': [1, 1, 1],
        'scenes': [
            {'sceneId': 'early', 'typography': {}, 'execution': {}, 'background': {'assetId': 'people_door_001'}},
            {'sceneId': 'mid', 'typography': {}, 'execution': {}, 'background': {}},
            {'sceneId': 'late', 'typography': {}, 'execution': {}, 'background': {'assetId': 'people_consult_001'}},
        ],
    }
    out = apply_evidence_gate(plan, rows, locale='zh-CN')
    payload = out['scenes'][0]['semanticMotionV14']
    by_label = {step['label']: step for step in payload['steps']}
    origin = payload['evidence']['sourceTimestamp'][0]
    family_end = origin + by_label['家庭结构']['until']
    cost_start = origin + by_label['代价']['at']
    assert family_end <= 18.76 + 0.01
    assert cost_start >= 30.44 - 0.01
    assert family_end < 24.92 < cost_start
    assert not out['scenes'][0]['background'].get('assetId')


def json_dump(plan):
    import json
    return json.dumps(plan, ensure_ascii=False)


def test_repeated_plate_is_cleared():
    plan = {
        'scenes': [
            {'sceneId': 'a', 'background': {'assetId': 'people_consult_001'}},
            {'sceneId': 'b', 'background': {'assetId': 'i2v_consult_001'}},
        ],
    }
    out = drop_repeated_assets(plan)
    assert out['scenes'][0]['background']['assetId'] == 'people_consult_001'
    assert not out['scenes'][1]['background'].get('assetId')
    assert 'repeated_asset' in out['scenes'][1]['rejected']


def test_shadow_does_not_change_the_plan():
    plan = {
        'durationSeconds': 10,
        'beatWeights': [1],
        'scenes': [{
            'sceneId': 'beside',
            'typography': {'cards': [{'title': '目标', 'explanation': '迁往哪里以及为何出发'}]},
            'background': {},
        }],
    }
    rows = [_zh('a', 0, 10, '有人关心最终入籍')]
    before = plan['scenes'][0]['typography']['cards'][0]['title']
    report = diagnose(plan, rows)
    assert plan['scenes'][0]['typography']['cards'][0]['title'] == before
    assert report['altersPlan'] is False
    assert any(item['code'] == 'unsupported_card' for item in report['findings'])
