"""Director V4 execution compliance: validate + deterministic repair."""
from backend.director_execution import (
    MIN_PIP_WIDTH_PX,
    enforce_plan,
    is_incomplete_heading,
    is_redundant_stat_pair,
    is_transcript_fragment_card,
    qa_sample_points,
    repair_scene,
    validate_scene,
)
from backend import remotion_engine


def test_incomplete_heading_rejects_look_at():
    assert is_incomplete_heading('Look at')
    assert is_incomplete_heading('but this')
    assert is_incomplete_heading('and the')
    assert not is_incomplete_heading('49%')
    assert not is_incomplete_heading('Foreign investment steps')
    assert not is_incomplete_heading('Look at', kinetic_reveal=True)


def test_fragment_card_vs_caption():
    assert is_transcript_fragment_card('but this number is')
    assert is_transcript_fragment_card(
        'people think that foreign',
        'people think that foreign investment companies only change the language',
    )
    assert not is_transcript_fragment_card('Capital must be paid in before banking')


def test_redundant_stat_pair():
    assert is_redundant_stat_pair('49%', '49%')
    assert is_redundant_stat_pair('Share 49%', '49%')
    assert not is_redundant_stat_pair('49%', 'Foreign share versus local control')


def test_repair_enlarges_or_switches_tiny_pip():
    scene = {
        'sceneId': 'consult',
        'semanticPurpose': 'proof',
        'speaker': {'layout': 'speaker_with_media'},
        'background': {'assetId': 'i2v_consult_001'},
        'typography': {},
        'execution': {
            'speakerFraming': 'pip',
            'pip': {'width': 120, 'height': 120, 'right': 20, 'bottom': 40},
            'headline': '',
            'cardText': '',
        },
    }
    issues = validate_scene(scene)
    assert any(i['code'] == 'speaker_too_small' for i in issues)
    fixed, actions = repair_scene(scene, issues)
    assert 'switch_to_split_screen' in actions or fixed['execution']['pip']['width'] >= MIN_PIP_WIDTH_PX
    assert fixed['execution']['speakerFraming'] in ('split', 'fullscreen', 'pip')
    if fixed['execution']['speakerFraming'] == 'pip':
        assert fixed['execution']['pip']['width'] >= MIN_PIP_WIDTH_PX


def test_repair_drops_fragment_card_and_incomplete_heading():
    scene = {
        'sceneId': 'hook',
        'speaker': {'layout': 'speaker_fullscreen'},
        'background': {},
        'typography': {'headline': 'Look at', 'card': 'but this number is'},
        'execution': {
            'speakerFraming': 'fullscreen',
            'headline': 'Look at',
            'cardText': 'but this number is',
            'caption': 'Look at the capital rules carefully',
        },
    }
    fixed, actions = repair_scene(scene)
    assert fixed['execution']['headline'] == ''
    assert fixed['execution']['cardText'] == ''
    assert any('incomplete' in a or 'fragment' in a or 'drop_' in a for a in actions)
    assert not [i for i in validate_scene(fixed) if i['severity'] == 'blocking']


def test_repair_dedupes_49_percent():
    scene = {
        'sceneId': 'stat',
        'speaker': {'layout': 'speaker_fullscreen'},
        'background': {},
        'execution': {
            'speakerFraming': 'fullscreen',
            'headline': '49%',
            'cardText': '49%',
        },
    }
    fixed, actions = repair_scene(scene)
    assert 'dedupe_stat_keep_headline' in actions
    assert fixed['execution']['headline'] == '49%'
    assert fixed['execution']['cardText'] == ''


def test_enforce_plan_stamps_compliance_block():
    plan = enforce_plan({
        'visualSeed': 1,
        'scenes': [{
            'sceneId': 'x',
            'speaker': {'layout': 'speaker_with_media'},
            'background': {'assetId': 're_inv_laptop'},
            'execution': {
                'speakerFraming': 'pip',
                'pip': {'width': 80, 'height': 80},
                'headline': 'Look at',
                'cardText': 'and the',
            },
        }],
    })
    assert plan['executionCompliance']['version'] == 'director_execution_v4'
    scene = plan['scenes'][0]
    assert scene['execution']['headline'] == ''
    assert scene['execution']['cardText'] == ''
    assert scene['execution']['speakerFraming'] in ('split', 'fullscreen', 'pip')
    if scene['execution']['speakerFraming'] == 'pip':
        assert scene['execution']['pip']['width'] >= MIN_PIP_WIDTH_PX


def test_resolve_scene_plan_runs_execution_compliance():
    plan = remotion_engine.resolve_scene_plan(
        visual_plan={
            'visualSeed': 9,
            'language': 'en-US',
            'scenes': [{
                'sceneId': 'beside',
                'semanticPurpose': 'criteria',
                'speaker': {'layout': 'speaker_with_media'},
                'background': {'assetId': 'people_consult_001'},
                'foreground': {},
                'typography': {'headline': 'Look at', 'card': '49%', 'animate': 'fade'},
                'execution': {
                    'speakerFraming': 'pip',
                    'pip': {'width': 100, 'height': 100},
                    'headline': 'Look at',
                    'cardText': '49%',
                },
                'transition': 'cut',
            }],
        },
        locale='en-US',
        generation_id='exec_compliance_test',
    )
    assert plan['executionCompliance']['version'] == 'director_execution_v4'
    scene = plan['scenes'][0]
    assert 'execution' in scene
    assert scene['execution']['headline'] != 'Look at'
    assert scene['speaker']['layout'] in (
        'speaker_split_right', 'speaker_split_left', 'speaker_fullscreen', 'speaker_with_media',
    )


def test_qa_sample_points_cover_entrance_hold_exit():
    pts = qa_sample_points(20)
    labels = {p['label'] for p in pts}
    assert 'open_entrance' in labels and 'mid_hold' in labels and 'exit' in labels
    assert all(0 <= p['t'] < 20 for p in pts)
