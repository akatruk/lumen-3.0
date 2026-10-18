"""Existing layout ranking. No new geometry and no mutation unless mode=apply."""
from __future__ import annotations

from backend.scene_composer_v16 import wrap_lines
from backend.visual_quality_optimizer import apply as apply_optimizer
from backend.visual_treatment_ranking import (
    apply,
    caption_band,
    candidates_for,
    editorial_focus_rects,
    rank_plan,
    rank_treatments,
    region_for,
    speaker_rect_for,
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


def test_editorial_focus_clears_the_caption_and_the_old_pip_does_not():
    rows = candidates_for(_timeline())
    assert [row['layout'] for row in rows] == ['editorial_focus', 'speaker_visual', 'full_frame', 'overlay']
    graphic, speaker = editorial_focus_rects()
    assert graphic['width'] == 952
    assert graphic['height'] == 582
    assert speaker == {'left': 656, 'top': 730, 'width': 360, 'height': 640}
    assert speaker['width'] * 16 == speaker['height'] * 9
    assert graphic['width'] / 1080 >= 0.65
    assert not _overlaps(graphic, speaker)
    assert not _overlaps(speaker, caption_band())
    assert not _overlaps(graphic, caption_band())
    assert rows[0]['valid'] is True
    assert rows[2]['valid'] is False
    assert rows[3]['rejected'] == 'graphic_box_smaller_than_component'
    # Source aspect does not change the output box.
    assert editorial_focus_rects() == editorial_focus_rects()


def test_ranking_selects_editorial_focus_and_falls_back():
    first = rank_treatments(_timeline())
    assert first == rank_treatments(_timeline())
    assert first['winner'] == 'editorial_focus'
    assert first['changed'] is True
    broken = _timeline()
    broken['steps'] = []
    broken['evidence'] = {'sourceQuote': '没有步骤'}
    fallback = rank_treatments(broken)
    assert fallback['winner'] == 'speaker_visual'
    assert fallback['changed'] is False


def test_comparison_and_range_can_use_editorial_focus():
    comparison = {
        'componentId': 'motion.business_comparison.v1',
        'visualIntent': 'business_comparison',
        'layout': 'speaker_visual',
        'left': '法人代表',
        'right': '董事权限',
        'evidence': {'sourceQuote': '中国强调法人代表 泰国更看重的是董事权限'},
    }
    assert rank_treatments(comparison)['winner'] == 'editorial_focus'
    payload = {
        'componentId': 'motion.numeric_range.v1',
        'visualIntent': 'numeric_range',
        'layout': 'speaker_visual',
        'unitOmitted': 'asr_unit_unverified',
        'range': {'lowText': '400', 'highText': '1200', 'unit': '', 'currency': '人民币'},
        'evidence': {'sourceQuote': '那大概在400-1200人民币每天'},
    }
    ranked = rank_treatments(payload)
    assert ranked['winner'] == 'editorial_focus'
    assert ranked['changed'] is True
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
    assert payload['layout'] == 'editorial_focus'
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
        motion = region_for('editorial_focus')
        assert motion['top'] + motion['height'] <= band['top']
        assert speaker_rect_for('editorial_focus')['top'] + speaker_rect_for('editorial_focus')['height'] <= band['top']


def test_malformed_plan_does_not_raise():
    out = apply({'scenes': 'nope'}, mode='apply')
    assert out['treatmentRanking']['status'] == 'malformed_plan'
    assert out['scenes'] == 'nope'


def test_rank_plan_is_bounded():
    plan = {'scenes': [{'sceneId': f's{i}', 'semanticMotionV14': _timeline()} for i in range(20)]}
    report = rank_plan(plan)
    assert report['elapsed_ms'] < 50
    assert len(report['scenes']) == 20


def _overlaps(a, b):
    return not (
        a['top'] + a['height'] <= b['top']
        or b['top'] + b['height'] <= a['top']
        or a['left'] + a['width'] <= b['left']
        or b['left'] + b['width'] <= a['left']
    )
