"""Visual quality optimizer: evidence findings, shadow non-mutation, safe apply."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from backend.visual_quality_optimizer import apply, evaluate, rank_candidates, recall_experience

ROOT = Path(__file__).resolve().parents[2]
PLANS = ROOT / 'reports/semantic-motion-webstudio/isolated'
ORIGINAL1 = PLANS / 'aa292ac6830c49afa4cf7c2f4f72f6da/remotion-plans/gen_289082071.json'
ORIGINAL2 = PLANS / '14dd4a24d3f043e595395cd7dc02f55a/remotion-plans/gen_856109875.json'
ORIGINAL3 = PLANS / 'bbfc523bb22c4c21b7075a6a3c76eade/remotion-plans/gen_631280367.json'


def _scene(scene_id, payload, **extra):
    scene = {
        'sceneId': scene_id,
        'speaker': {'layout': 'speaker_fullscreen'},
        'typography': {'cards': []},
        'semanticMotionV14': payload,
    }
    scene.update(extra)
    return scene


def _timeline(quote, labels):
    return {
        'componentId': 'motion.process_timeline.v1',
        'visualIntent': 'process_timeline',
        'steps': [{'label': label} for label in labels],
        'evidence': {'segmentId': 'segment_006', 'sourceQuote': quote, 'sourceTimestamp': [21.0, 27.6]},
        'lifecycle': {
            'evidence_start': 21.0, 'evidence_end': 27.6,
            'display_start': 21.0, 'display_end': 27.6,
            'source_segment_ids': ['segment_006'],
        },
    }


def test_shadow_does_not_mutate_scenes():
    plan = {'language': 'zh-CN', 'scenes': [_scene('s', _timeline('银行开户工作证签证申请都会盯着资金到位情况', ['银行开户', '工作证', '签证申请']))]}
    before = copy.deepcopy(plan)
    out = apply(plan, [], mode='shadow', experience={'available': False, 'reason': 'test', 'hits': [], 'queries': 0})
    assert plan == before
    assert out['scenes'] is plan['scenes']
    assert out['visualOptimizerMode'] == 'shadow'
    kinds = [item['finding_type'] for item in out['visualQualityReport']['findings']]
    assert 'UNJUSTIFIED_PROCESS_TIMELINE' in kinds


def test_off_is_identity():
    plan = {'scenes': []}
    assert apply(plan, [], mode=None) is plan
    assert apply(plan, [], mode='off') is plan


def test_invalid_timeline_and_ordered_layers():
    noun = evaluate({'scenes': [_scene('noun', _timeline('银行开户、工作证、签证申请都会盯着资金到位情况', ['银行开户', '工作证', '签证申请']))]})
    assert any(item['finding_type'] == 'UNJUSTIFIED_PROCESS_TIMELINE' for item in noun['findings'])
    ordered_quote = '第一层叫使用场景 第二层叫家庭结构 第三层叫代价'
    ordered = evaluate({'scenes': [_scene('layers', _timeline(ordered_quote, ['使用场景', '家庭结构', '代价']))]})
    assert all(item['finding_type'] != 'UNJUSTIFIED_PROCESS_TIMELINE' for item in ordered['findings'])
    assert ordered['decisions'][0]['decision'] == 'NO_CHANGE'


def test_unsupported_claim_and_cross_scene_leak():
    leaked = {
        'componentId': 'motion.business_comparison.v1',
        'visualIntent': 'business_comparison',
        'left': '中国',
        'right': '泰国',
        'evidence': {'segmentId': 'segment_007', 'sourceQuote': '中国强调法人代表 泰国更看重的是董事权限', 'sourceTimestamp': [27.6, 36.0]},
        'lifecycle': {'evidence_start': 27.6, 'evidence_end': 36.0, 'display_start': 27.6, 'display_end': 36.0, 'source_segment_ids': ['segment_007']},
    }
    # The active quote does not contain 中国/泰国. An earlier scene does.
    earlier = {
        'componentId': 'motion.business_comparison.v1',
        'visualIntent': 'business_comparison',
        'left': '中国',
        'right': '泰国',
        'evidence': {'sourceQuote': '中国认缴时间弹性很大 泰国则要求实缴', 'sourceTimestamp': [15, 21]},
        'lifecycle': {'evidence_start': 15, 'evidence_end': 21, 'display_start': 15, 'display_end': 21, 'source_segment_ids': ['segment_005']},
    }
    late = dict(leaked)
    late['evidence'] = {'segmentId': 'segment_007', 'sourceQuote': '管理逻辑也不同 法人代表和董事权限', 'sourceTimestamp': [27.6, 36.0]}
    report = evaluate({'scenes': [_scene('early', earlier), _scene('late', late)]})
    kinds = {(item['scene_id'], item['finding_type']) for item in report['findings']}
    assert ('late', 'CROSS_SCENE_SEMANTIC_LEAK') in kinds


def test_omitted_currency_is_not_an_unsupported_claim():
    payload = {
        'componentId': 'motion.numeric_range.v1',
        'visualIntent': 'numeric_range',
        'unitOmitted': 'asr_unit_unverified',
        'range': {'lowText': '400', 'highText': '1200', 'unit': '', 'currency': '人民币'},
        'evidence': {'sourceQuote': '那大概在400-1200人民币每天', 'sourceTimestamp': [28.6, 33.0]},
        'lifecycle': {'evidence_start': 28.6, 'evidence_end': 33.0, 'display_start': 28.6, 'display_end': 33.0, 'source_segment_ids': ['segment_008']},
    }
    invented = dict(payload)
    invented['unitOmitted'] = None
    invented['range'] = {'unit': '泰铢', 'currency': '泰铢'}
    report = evaluate({'scenes': [_scene('ok', payload), _scene('bad', invented)]})
    bad = [item for item in report['findings'] if item['scene_id'] == 'bad']
    ok = [item for item in report['findings'] if item['scene_id'] == 'ok']
    assert any(item['finding_type'] == 'UNSUPPORTED_VISIBLE_CLAIM' for item in bad)
    assert not any(item['finding_type'] == 'UNSUPPORTED_VISIBLE_CLAIM' for item in ok)


def test_repeated_broll_does_not_force_diversity():
    def plate(scene_id, quote, asset='people_door_001'):
        return _scene(scene_id, {
            'visualIntent': 'business_comparison',
            'left': '门', 'right': '门',
            'evidence': {'sourceQuote': quote},
            'lifecycle': {'evidence_start': 0, 'evidence_end': 1, 'display_start': 0, 'display_end': 1, 'source_segment_ids': [scene_id]},
        }, foreground={'assetId': asset, 'query': quote})
    recurring = evaluate({'scenes': [plate('a', '客户进门咨询'), plate('b', '客户进门之后')]})
    assert any(item['evaluation_status'] == 'justified_reuse' for item in recurring['findings'])
    barren = evaluate({'scenes': [plate('a', '银行开户材料'), plate('b', '海边日落')]})
    assert any(item['finding_type'] == 'NO_SAFE_ALTERNATIVE' for item in barren['findings'])
    replaced = apply(
        {'scenes': [plate('a', '银行开户材料'), plate('b', '海边日落')]},
        mode='apply_safe',
        experience={'available': False, 'hits': [], 'queries': 0},
        alternatives=[{'asset_id': 'coast_002', 'approved': True, 'label': '海边日落'}],
    )
    assert replaced['scenes'][1]['foreground']['assetId'] == 'coast_002'
    assert replaced['scenes'][0]['foreground']['assetId'] == 'people_door_001'


def test_apply_safe_drops_only_the_bad_timeline():
    plan = {'language': 'zh-CN', 'audio': {'speech': 'source'}, 'scenes': [
        _scene('good', _timeline('第一层叫使用场景 第二层叫家庭结构 第三层叫代价', ['使用场景', '家庭结构', '代价'])),
        _scene('bad', _timeline('银行开户工作证签证申请都会盯着资金到位情况', ['银行开户', '工作证', '签证申请'])),
    ]}
    out = apply(plan, [{'id': 'segment_006', 'text': '银行开户'}], mode='apply_safe', experience={'available': False, 'hits': [], 'queries': 0})
    assert out['language'] == 'zh-CN'
    assert out['audio']['speech'] == 'source'
    assert out['scenes'][0]['semanticMotionV14']['visualIntent'] == 'process_timeline'
    assert 'semanticMotionV14' not in out['scenes'][1]
    assert plan['scenes'][1]['semanticMotionV14']['visualIntent'] == 'process_timeline'


def test_ranking_rejects_unapproved_and_irrelevant():
    ranked, log = rank_candidates([
        {'asset_id': 'nope', 'approved': False, 'label': '银行开户'},
        {'asset_id': 'beach', 'approved': True, 'label': '海边日落'},
        {'asset_id': 'desk', 'approved': True, 'label': '银行开户柜台', 'review_source': 'automated', 'user_quality_rating': 9},
    ], '银行开户材料')
    assert [item[0]['asset_id'] for item in ranked] == ['desk']
    assert any(row['reason'] == 'not_approved' for row in log)
    assert any(row['reason'] == 'no_source_overlap' for row in log)
    assert any('no_verified_user_rating' in row['reason'] for row in log)


def test_missing_feedback_and_dimension_mismatch(monkeypatch):
    monkeypatch.setattr('backend.experience_memory.settings.visual_experience_memory_enabled', False)
    monkeypatch.setattr('backend.experience_memory.settings.visual_intelligence_enabled', False)
    empty = recall_experience(None)
    assert empty['available'] is False
    assert empty['reason'] == 'no_query_embedding'
    mismatch = recall_experience([0.1, 0.2])
    assert mismatch['reason'] == 'embedding_dimension_mismatch'
    disabled = recall_experience([0.0] * 512)
    assert disabled['reason'] == 'experience_memory_disabled'
    assert disabled['queries'] == 0

    class _Sqlite:
        postgres = False

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr('backend.experience_memory.settings.visual_experience_memory_enabled', True)
    monkeypatch.setattr('backend.database.connect', lambda: _Sqlite())
    offline = recall_experience([0.0] * 512)
    assert offline['reason'] == 'postgres_unavailable'
    assert offline['queries'] == 0


def test_malformed_plan_and_optimizer_failure_leave_the_plan():
    plan = {'scenes': 'nope', 'language': 'zh-CN'}
    out = apply(plan, [], mode='shadow', experience={'available': False, 'hits': [], 'queries': 0})
    assert out['scenes'] == 'nope'
    assert out['visualQualityReport']['status'] == 'malformed_plan'
    assert out['language'] == 'zh-CN'


def test_stale_graphic_is_shortened_not_rewritten():
    payload = _timeline('第一层叫使用场景 第二层叫家庭结构 第三层叫代价', ['使用场景', '家庭结构', '代价'])
    payload['lifecycle']['display_end'] = 40
    payload['outputTime'] = [21.0, 40]
    plan = {'scenes': [_scene('stale', payload)]}
    out = apply(plan, [], mode='apply_safe', experience={'available': False, 'hits': [], 'queries': 0})
    life = out['scenes'][0]['semanticMotionV14']['lifecycle']
    assert life['display_end'] == 28.8
    assert life['evidence_end'] == 27.6


def test_persisted_director_plans_match_the_labeled_examples():
    if not (ORIGINAL1.exists() and ORIGINAL2.exists() and ORIGINAL3.exists()):
        return
    first = json.loads(ORIGINAL1.read_text(encoding='utf-8'))
    second = json.loads(ORIGINAL2.read_text(encoding='utf-8'))
    third = json.loads(ORIGINAL3.read_text(encoding='utf-8'))
    shadow = apply(first, [], mode='shadow', experience={'available': False, 'reason': 'sqlite_isolated', 'hits': [], 'queries': 0})
    assert shadow['scenes'] is first['scenes']
    kinds = {item['finding_type'] for item in shadow['visualQualityReport']['findings']}
    assert kinds == {'UNJUSTIFIED_PROCESS_TIMELINE'}
    range_report = evaluate(second)
    assert not any(item['finding_type'] == 'UNSUPPORTED_VISIBLE_CLAIM' for item in range_report['findings'])
    layers = evaluate(third)
    assert not any(item['finding_type'] == 'UNJUSTIFIED_PROCESS_TIMELINE' for item in layers['findings'])
