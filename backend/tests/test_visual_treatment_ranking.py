"""Existing layout ranking. No new geometry and no mutation unless mode=apply."""
from __future__ import annotations

from backend.scene_composer_v16 import wrap_lines
from backend.visual_quality_optimizer import apply as apply_optimizer
from backend.visual_treatment_ranking import (
    apply,
    caption_band,
    candidates_for,
    rank_plan,
    rank_treatments,
    region_for,
)


def _timeline(layout='speaker_visual'):
    return {
        'componentId': 'motion.process_timeline.v1',
        'visualIntent': 'process_timeline',
        'layout': layout,
        'mediaSide': 'left',
        'steps': [{'label': '使用场景'}, {'label': '家庭结构'}, {'label': '代价'}],
        'evidence': {'segmentId': 'segment_002', 'sourceQuote': '第一层叫使用场景 第二层叫家庭结构 第三层叫代价'},
        'lifecycle': {
            'evidence_start': 0.0, 'evidence_end': 32.2,
            'display_start': 0.0, 'display_end': 33.432,
            'source_segment_ids': ['segment_001', 'segment_018'],
        },
    }


def test_three_existing_layouts_and_overlay_rejected_for_the_step_stack():
    rows = candidates_for(_timeline())
    assert [row['layout'] for row in rows] == ['speaker_visual', 'full_frame', 'overlay']
    overlay = rows[2]
    assert overlay['valid'] is False
    assert overlay['rejected'] == 'graphic_box_smaller_than_component'
    assert rows[0]['valid'] is True
    assert rows[1]['valid'] is False
    assert rows[1]['rejected'] == 'layout_hits_caption_face_or_speaker'


def test_full_frame_loses_because_the_pip_covers_the_caption():
    first = rank_treatments(_timeline())
    second = rank_treatments(_timeline())
    assert first == second
    assert first['winner'] == 'speaker_visual'
    assert first['changed'] is False
    full = next(row for row in first['candidates'] if row['layout'] == 'full_frame')
    assert full['valid'] is False
    assert full['rejected'] == 'layout_hits_caption_face_or_speaker'
    split = region_for('speaker_visual', 'left')
    assert split['width'] == 504
    assert not _overlaps_caption(split)


def test_comparison_keeps_the_speaker_column_and_range_does_not():
    comparison = {
        'componentId': 'motion.business_comparison.v1',
        'visualIntent': 'business_comparison',
        'layout': 'speaker_visual',
        'left': '法人代表',
        'right': '董事权限',
        'evidence': {'sourceQuote': '中国强调法人代表 泰国更看重的是董事权限'},
    }
    assert rank_treatments(comparison)['winner'] == 'speaker_visual'
    payload = {
        'componentId': 'motion.numeric_range.v1',
        'visualIntent': 'numeric_range',
        'layout': 'speaker_visual',
        'unitOmitted': 'asr_unit_unverified',
        'range': {'lowText': '400', 'highText': '1200', 'unit': '', 'currency': '人民币'},
        'evidence': {'sourceQuote': '那大概在400-1200人民币每天'},
    }
    ranked = rank_treatments(payload)
    assert ranked['winner'] == 'speaker_visual'
    assert ranked['changed'] is False
    assert all(row['rejected'] != 'currency_absent' for row in ranked['candidates'])


def test_unsupported_currency_is_rejected():
    payload = {
        'componentId': 'motion.numeric_range.v1',
        'visualIntent': 'numeric_range',
        'layout': 'speaker_visual',
        'range': {'unit': '泰铢', 'currency': '泰铢', 'lowText': '1', 'highText': '2'},
        'evidence': {'sourceQuote': '月薪差不多在1.5-2.5万泰国左右吧'},
    }
    ranked = rank_treatments(payload)
    assert ranked['changed'] is False
    assert all(row['rejected'] == 'currency_absent' for row in ranked['candidates'])


def test_apply_keeps_evidence_and_off_is_identity():
    scene = {'sceneId': 'layers', 'semanticMotionV14': _timeline()}
    plan = {'language': 'zh-CN', 'audio': {'speech': 'source'}, 'scenes': [scene]}
    assert apply(plan, mode=None) is plan
    shadow = apply(plan, mode='shadow')
    assert shadow['scenes'] is plan['scenes']
    out = apply(plan, mode='apply')
    payload = out['scenes'][0]['semanticMotionV14']
    assert payload['layout'] == 'speaker_visual'
    assert payload['steps'] == scene['semanticMotionV14']['steps']
    assert payload['lifecycle'] == scene['semanticMotionV14']['lifecycle']
    assert payload['evidence'] == scene['semanticMotionV14']['evidence']
    assert out['language'] == 'zh-CN'
    assert out['audio']['speech'] == 'source'
    assert plan['scenes'][0]['semanticMotionV14']['layout'] == 'speaker_visual'


def test_optimizer_off_still_identity():
    plan = {'scenes': [{'sceneId': 's', 'semanticMotionV14': _timeline()}]}
    assert apply_optimizer(plan, mode='off') is plan


def test_caption_wrap_for_three_locales_stays_in_the_band():
    samples = {
        'zh-CN': '第一层叫使用场景，第二层叫家庭结构，第三层叫代价。',
        'en-US': 'The first layer is use, then household, then cost.',
        'ru-RU': 'Первый слой это сценарий, затем семья, затем цена.',
    }
    band = caption_band()
    for locale, text in samples.items():
        lines = wrap_lines(text, locale, 18 if locale.startswith('zh') else 28)
        assert lines
        assert all(not line.startswith(('，', '。', ',', '.')) for line in lines)
        assert band['top'] + band['height'] == 1920
        motion = region_for('speaker_visual')
        assert motion['top'] + motion['height'] <= band['top']


def test_malformed_plan_does_not_raise():
    out = apply({'scenes': 'nope'}, mode='apply')
    assert out['treatmentRanking']['status'] == 'malformed_plan'
    assert out['scenes'] == 'nope'


def test_rank_plan_is_bounded():
    plan = {'scenes': [{'sceneId': f's{i}', 'semanticMotionV14': _timeline()} for i in range(20)]}
    report = rank_plan(plan)
    assert report['elapsed_ms'] < 50
    assert len(report['scenes']) == 20


def _overlaps_caption(rect):
    band = caption_band()
    return not (rect['top'] + rect['height'] <= band['top'] or rect['top'] >= band['top'] + band['height'])
