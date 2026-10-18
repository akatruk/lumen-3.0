from backend.director_v9 import (
    apply_composition_intelligence,
    score_scene_complexity,
    simplify_scene_composition,
)


def test_simplify_omits_opaque_motion_on_speaker():
    scene = {
        'sceneId': 'hook',
        'speaker': {'layout': 'speaker_punch_in', 'framing': 'fullscreen'},
        'background': {},
        'foreground': {},
        'typography': {'headline': 'Планируете переезд'},
        'semanticMotion': {
            'file': 'motion/premium/pm_scene_mobility_001.webm',
            'staged': 'picked/pm_scene_mobility_001.webm',
            'keyword': 'relocation',
        },
        'shotPlan': {'keywords': [{'id': 'relocation'}]},
    }
    out = simplify_scene_composition(scene, used_silhouettes=set(), used_assets=set())
    assert out['composition']['containerPolicy'] == 'minimal'
    assert out['semanticMotion'].get('display') == 'omit'
    assert out['composition'].get('floatObject')
    assert out['composition']['floatObject']['background'] == 'transparent'
    assert out['speakerProtection'] is True


def test_infographic_drops_float():
    scene = {
        'sceneId': 'beside',
        'speaker': {'layout': 'speaker_split_left', 'framing': 'split'},
        'background': {},
        'typography': {'cardMode': 'progressive_one', 'cards': [{'title': 'A', 'explanation': 'B'}]},
        'shotPlan': {'keywords': [{'id': 'family'}]},
        'semanticMotion': {'file': 'x.webm', 'staged': 'picked/x.webm'},
    }
    out = simplify_scene_composition(scene, used_silhouettes=set(), used_assets=set())
    assert out['primaryVisualRole'] == 'infographic'
    assert out['composition'].get('floatObject') in (None, {})
    assert out['semanticMotion'].get('display') == 'omit'


def test_apply_composition_intelligence_plan():
    plan = {
        'language': 'ru-RU',
        'heroObject': 'globe',
        'scenes': [
            {
                'sceneId': 'hook',
                'speaker': {'layout': 'speaker_punch_in', 'framing': 'fullscreen'},
                'background': {},
                'foreground': {},
                'typography': {'headline': 'Hi'},
                'semanticMotion': {
                    'file': 'motion/premium/pm_scene_mobility_001.webm',
                    'staged': 'picked/pm.webm',
                    'keyword': 'relocation',
                },
                'shotPlan': {'keywords': [{'id': 'relocation'}]},
            },
            {
                'sceneId': 'problem',
                'speaker': {'layout': 'speaker_closeup', 'framing': 'fullscreen'},
                'background': {},
                'foreground': {},
                'typography': {},
                'semanticMotion': {
                    'file': 'motion/documents/document_approval_001.webm',
                    'keyword': 'residency',
                },
                'shotPlan': {'keywords': [{'id': 'residency'}]},
            },
            {
                'sceneId': 'consult',
                'speaker': {'layout': 'speaker_with_media', 'framing': 'pip'},
                'background': {'assetId': 're_agent_docs'},
                'foreground': {},
                'typography': {},
                'shotPlan': {'keywords': [{'id': 'consult'}]},
            },
        ],
    }
    out = apply_composition_intelligence(plan)
    assert out['shotPlanVersion'] == 'v9'
    assert out['compositionPolicy'] == 'v9_clean'
    assert out['conceptTriggers'] is False
    assert out['heroObject'] is None
    assert out['compositionAudit']['pass'] is True
    floats = [
        ((s.get('composition') or {}).get('floatObject') or {}).get('silhouette')
        for s in out['scenes']
    ]
    # hook suitcase + problem passport — distinct silhouettes
    assert floats[0] == 'suitcase'
    assert floats[1] == 'passport'
    assert floats[0] != floats[1]


def test_dedupe_looping_captions():
    from backend.director_v9 import dedupe_looping_captions
    caps = [
        {'start': 0, 'end': 5, 'text': 'Планируете переезд'},
        {'start': 6, 'end': 8, 'text': 'с чего начать?'},
        {'start': 40, 'end': 45, 'text': 'Планируете переезд'},
        {'start': 46, 'end': 48, 'text': 'с чего начать?'},
    ]
    out = dedupe_looping_captions(caps)
    assert len(out) == 2
    assert out[0]['start'] == 0


def test_score_flags_motion_box():
    metrics = score_scene_complexity({
        'primaryVisualRole': 'speaker',
        'semanticMotion': {'staged': 'picked/x.webm', 'display': 'box'},
        'typography': {'headline': 'X'},
        'composition': {},
    })
    assert metrics['overBudget'] is True
    assert 'motion_box' in metrics['reasons']
