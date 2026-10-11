"""Canonical same-source ban for Director media layers."""
from backend.director_media_rules import (
    canonical_media_identity,
    same_media_source,
    sanitize_scene_layers,
)
from backend import remotion_engine


def test_canonical_identity_groups_still_and_i2v():
    assert canonical_media_identity('people_consult_001') == 'consult'
    assert canonical_media_identity('i2v_consult_001') == 'consult'
    assert same_media_source('people_door_001', 'i2v_door_001')
    assert not same_media_source('people_door_001', 'people_consult_001')


def test_sanitize_clears_same_source_foreground():
    scene = sanitize_scene_layers({
        'sceneId': 'residency',
        'background': {'assetId': 'people_consult_001', 'file': 'static/people/people_consult_001.png'},
        'foreground': {'assetId': 'i2v_consult_001', 'file': 'motion/people/i2v_consult_001.mp4'},
        'rejected': [],
    })
    assert scene['foreground']['assetId'] is None
    assert scene['foreground']['file'] is None
    assert 'same_source_inset' in scene['rejected']


def test_resolve_scene_plan_enforces_same_source_ban():
    plan = remotion_engine.resolve_scene_plan(
        visual_plan={
            'visualSeed': 1,
            'scenes': [
                {
                    'sceneId': 'consult',
                    'semanticPurpose': 'proof',
                    'speaker': {'layout': 'speaker_with_media'},
                    'background': {'assetId': 'i2v_consult_001', 'treatment': 'ambient_loop'},
                    'foreground': {'assetId': 'people_consult_001', 'treatment': 'reveal_and_hold'},
                    'typography': {'animate': 'fade'},
                    'transition': 'cut',
                }
            ],
        },
        generation_id='same_source_test',
    )
    scene = plan['scenes'][0]
    assert scene['background']['assetId'] == 'i2v_consult_001'
    assert scene['foreground']['assetId'] is None
    assert 'same_source_inset' in scene['rejected']
