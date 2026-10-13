import json

import pytest

from backend.director_v14 import apply_semantic_motion
from backend.motion_quality_v17 import (
    MIN_EVIDENCE,
    advise,
    apply_advice,
    benchmark,
    component_cards,
    enabled,
    layout_after_advice,
    record_completed,
    retrieve_components,
)


def test_flag_off_does_not_touch_storage(monkeypatch):
    monkeypatch.delenv('MOTION_QUALITY_V17_ENABLED', raising=False)
    assert enabled() is False
    assert record_completed('p', 'g', {'scenes': []})['reason'] == 'flag_off'


def test_cards_cover_fifteen_components_in_three_locales():
    cards = component_cards()
    assert len(cards) == 45
    assert len({card['componentId'] for card in cards}) == 15
    assert {card['locale'] for card in cards} == {'en-US', 'ru-RU', 'zh-CN'}
    for card in cards:
        assert 'visual purpose:' in card['body']
        assert 'input requirements:' in card['body']
        assert 'visual limitations:' in card['body']
        assert 'layout capabilities:' in card['body']
        assert card['body'].strip() != card['componentId']


def test_same_concept_retrieves_the_same_component():
    en = retrieve_components('shareholders ownership network', 'en-US')
    ru = retrieve_components('акционеры структура владения', 'ru-RU')
    zh = retrieve_components('股东 股权结构', 'zh-CN')
    assert en[0]['componentId'] == ru[0]['componentId'] == zh[0]['componentId'] == 'motion.shareholder_network.v1'


def test_one_review_does_not_change_rank(monkeypatch):
    monkeypatch.setenv('MOTION_QUALITY_V17_ENABLED', '1')
    proposals = [
        (5, 0, {'componentId': 'motion.ownership_split.v1', 'evidence': {'sourceQuote': '49%'}}),
        (4, 1, {'componentId': 'motion.shareholder_network.v1', 'evidence': {'sourceQuote': 'shareholders'}}),
    ]
    evidence = [{
        'component_id': 'motion.ownership_split.v1',
        'component_version': 'v14.1',
        'layout': 'overlay',
        'concepts': 'ownership',
        'generation_id': 'g1',
        'issue_category': 'poor_animation',
    }]
    advice = advise({}, proposals, 'en-US', evidence=evidence)
    assert advice['demoteComponents'] == []
    assert apply_advice(proposals, advice)[0][2]['componentId'] == 'motion.ownership_split.v1'
    assert advice['humanReviewsUsed'] < MIN_EVIDENCE


def test_five_implementation_failures_demote_only_that_component(monkeypatch):
    monkeypatch.setenv('MOTION_QUALITY_V17_ENABLED', '1')
    proposals = [
        (5, 0, {'componentId': 'motion.ownership_split.v1', 'evidence': {'sourceQuote': '49%'}}),
        (5, 1, {'componentId': 'motion.shareholder_network.v1', 'evidence': {'sourceQuote': 'shareholders'}}),
    ]
    evidence = [
        {
            'component_id': 'motion.ownership_split.v1',
            'layout': 'overlay',
            'concepts': 'ownership',
            'generation_id': f'g{i}',
            'issue_category': 'poor_animation',
        }
        for i in range(5)
    ]
    advice = advise({}, proposals, 'en-US', evidence=evidence)
    ranked = apply_advice(proposals, advice)
    assert ranked[0][2]['componentId'] == 'motion.shareholder_network.v1'
    assert 'motion.ownership_split.v1' in advice['demoteComponents']


def test_fact_mismatch_does_not_demote_the_component(monkeypatch):
    monkeypatch.setenv('MOTION_QUALITY_V17_ENABLED', '1')
    proposals = [(5, 0, {'componentId': 'motion.ownership_split.v1', 'evidence': {'sourceQuote': '49%'}})]
    evidence = [
        {
            'component_id': 'motion.ownership_split.v1',
            'layout': 'full_frame',
            'concepts': '49',
            'generation_id': f'g{i}',
            'issue_category': 'factual_error',
        }
        for i in range(6)
    ]
    advice = advise({}, proposals, 'en-US', evidence=evidence)
    assert advice['demoteComponents'] == []
    assert advice['knownDefects'][0]['class'] == 'fact'
    assert apply_advice(proposals, advice)[0][2]['componentId'] == 'motion.ownership_split.v1'


def test_layout_failures_block_only_that_layout(monkeypatch):
    monkeypatch.setenv('MOTION_QUALITY_V17_ENABLED', '1')
    evidence = [
        {
            'component_id': 'motion.capital_flow.v1',
            'layout': 'full_frame',
            'concepts': 'capital',
            'generation_id': f'g{i}',
            'issue_category': 'face_overlap',
        }
        for i in range(5)
    ]
    advice = advise({}, [], 'en-US', evidence=evidence)
    assert layout_after_advice('motion.capital_flow.v1', 'full_frame', advice) == 'overlay'
    assert layout_after_advice('motion.capital_flow.v1', 'speaker_visual', advice) == 'speaker_visual'
    assert layout_after_advice('motion.shareholder_network.v1', 'full_frame', advice) == 'full_frame'


def test_database_failure_falls_back(monkeypatch):
    monkeypatch.setenv('MOTION_QUALITY_V17_ENABLED', '1')

    def boom():
        raise RuntimeError('postgres://lumen:secret@db/lumen down')

    monkeypatch.setattr('backend.motion_quality_v17._evidence_rows', boom)
    advice = advise({}, [], 'en-US')
    assert advice['fallback'] == 'deterministic'
    assert 'secret' not in advice['error']
    proposals = [(3, 0, {'componentId': 'motion.business_comparison.v1'})]
    assert apply_advice(proposals, advice) == proposals


def test_flag_off_keeps_v14_selection(monkeypatch):
    monkeypatch.setenv('SEMANTIC_MOTION_V14_ENABLED', '1')
    monkeypatch.delenv('MOTION_QUALITY_V17_ENABLED', raising=False)
    plan = {
        'language': 'en-US',
        'durationSeconds': 10,
        'beatWeights': [1],
        'scenes': [{'sceneId': 's', 'speaker': {'layout': 'speaker_fullscreen'}}],
        'transcript': [{'id': 'seg', 'start': 0, 'end': 8, 'text': 'foreign capital ratio is less than 49%'}],
    }
    out = apply_semantic_motion(plan, plan['transcript'], locale='en-US')
    assert out['motionQualityV17'] is None
    assert out['scenes'][0]['semanticMotionV14']['values'][0]['value'] == 49


def test_benchmark_has_no_human_score_and_matches_lexicon():
    rows = benchmark()
    assert len(rows) == 10
    assert all(row['humanJudgment'] is None for row in rows)
    failed = [
        f"{row['id']}:{locale}"
        for row in rows
        for locale, item in row['locales'].items()
        if not item['match']
    ]
    assert failed == [], json.dumps(rows, ensure_ascii=False)


def test_v17_on_without_reviews_matches_deterministic(monkeypatch):
    monkeypatch.setenv('SEMANTIC_MOTION_V14_ENABLED', '1')
    monkeypatch.setenv('MOTION_QUALITY_V17_ENABLED', '1')
    monkeypatch.setattr('backend.motion_quality_v17._evidence_rows', lambda: [])
    plan = {
        'language': 'en-US',
        'durationSeconds': 10,
        'beatWeights': [1, 1],
        'scenes': [
            {'sceneId': 'a', 'speaker': {'layout': 'speaker_fullscreen'}},
            {'sceneId': 'b', 'speaker': {'layout': 'speaker_fullscreen'}},
        ],
        'transcript': [
            {'id': 's1', 'start': 0, 'end': 4, 'text': 'The core is the capital investment'},
            {'id': 's2', 'start': 4, 'end': 8, 'text': 'at least three shareholders'},
        ],
    }
    out = apply_semantic_motion(plan, plan['transcript'], locale='en-US')
    assert out['motionQualityV17']['fallback'] is None
    assert out['motionQualityV17']['demoteComponents'] == []
    ids = [row['componentId'] for row in out['semanticMotionV14Usage']]
    assert 'motion.shareholder_network.v1' in ids
    assert 'motion.capital_flow.v1' in ids
