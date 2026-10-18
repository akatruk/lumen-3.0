"""editing_controls module + plan stamps for low/mid/high sliders."""
from backend.prompt_modules import assemble_hypit_prompt
from backend.prompt_modules.editing_controls import (
    PRESETS,
    VERSION,
    apply_editing_controls,
    detect_preset,
    levels_from_manual,
)


def _bare_plan():
    return {
        'visualSeed': 1,
        'artDirection': 'modern_explainer',
        'visualEnergy': 'balanced',
        'conceptTriggers': True,
        'scenes': [
            {
                'sceneId': f'scene_{index}',
                'motionIntensity': 'medium',
                'typography': {'animate': 'pop'},
                'background': {'treatment': 'slow_zoom_in'},
                'foreground': {},
                'speaker': {'layout': 'speaker_fullscreen'},
                'transition': 'cut',
            }
            for index in range(6)
        ],
    }


def test_editing_controls_module_always_attaches():
    bundle = assemble_hypit_prompt({'card_motion': 60})
    assert any(m['id'] == 'editing_controls' and m['version'] == VERSION for m in bundle.modules)
    assert 'MODULE EDITING CONTROLS RULES' in bundle.text
    assert 'editingControls' in bundle.run_params
    assert bundle.run_params['editingControls']['preset'] == 'balanced'


def test_presets_and_custom_detection():
    assert detect_preset(PRESETS['calm']) == 'calm'
    assert detect_preset(PRESETS['dynamic']) == 'dynamic'
    assert detect_preset({**PRESETS['balanced'], 'motion': 50}) == 'custom'


def test_slider_bands_change_plan_distinctly():
    base = _bare_plan()
    low = apply_editing_controls(base, {'animation': 20, 'intensity': 20, 'motion': 20, 'density': 20, 'visualEnergy': 'custom'})
    mid = apply_editing_controls(base, {'animation': 60, 'intensity': 60, 'motion': 60, 'density': 60, 'visualEnergy': 'custom'})
    high = apply_editing_controls(base, {'animation': 100, 'intensity': 100, 'motion': 100, 'density': 100, 'visualEnergy': 'custom'})

    assert low['editingControls']['motion'] == 20
    assert high['editingControls']['motion'] == 100
    assert low['motionIntensity'] == 'low'
    assert high['motionIntensity'] == 'high'
    assert mid['motionIntensity'] == 'medium'

    # Animation share: fewer scenes animate at low %
    assert sum(1 for s in low['scenes'] if s['animateGraphics']) < sum(1 for s in high['scenes'] if s['animateGraphics'])
    assert sum(1 for s in high['scenes'] if s['animateGraphics']) == 6

    # Density gates overlays / concept triggers
    assert low['conceptTriggers'] is False
    assert high['conceptTriggers'] is True
    assert max(s['overlayBudget'] for s in low['scenes']) == 0
    assert max(s['overlayBudget'] for s in high['scenes']) == 3

    # Low density quiets pop typography
    assert low['scenes'][0]['typography']['animate'] == 'fade'
    assert high['scenes'][0]['typography']['animate'] == 'pop'


def test_each_slider_isolated_low_mid_high():
    base = _bare_plan()
    for key in ('animation', 'intensity', 'motion', 'density'):
        samples = []
        for value in (20, 60, 100):
            controls = {'animation': 60, 'intensity': 60, 'motion': 80, 'density': 70, 'visualEnergy': 'custom'}
            controls[key] = value
            plan = apply_editing_controls(base, controls)
            samples.append(plan)
        assert samples[0]['editingControls'][key] == 20
        assert samples[1]['editingControls'][key] == 60
        assert samples[2]['editingControls'][key] == 100
        if key == 'animation':
            assert sum(s['animateGraphics'] for s in samples[0]['scenes']) < sum(
                s['animateGraphics'] for s in samples[2]['scenes']
            )
        if key == 'motion':
            assert samples[0]['motionIntensity'] != samples[2]['motionIntensity']
        if key == 'density':
            assert samples[0]['conceptTriggers'] is False
            assert samples[2]['conceptTriggers'] is True


def test_levels_from_manual_snaps_to_five():
    levels = levels_from_manual({'card_motion': 62, 'animation_intensity': 7, 'animation_motion': 83, 'animation_density': 71})
    assert levels == {'animation': 60, 'intensity': 5, 'motion': 80, 'density': 70}


def test_localization_still_attaches_with_editing():
    calm = PRESETS['calm']
    bundle = assemble_hypit_prompt({
        'language': 'en',
        'card_motion': calm['animation'],
        'animation_intensity': calm['intensity'],
        'animation_motion': calm['motion'],
        'animation_density': calm['density'],
        'visual_energy': 'calm',
    })
    ids = [m['id'] for m in bundle.modules]
    assert ids == ['editing_controls', 'localization']
    assert bundle.run_params['editingControls']['preset'] == 'calm'
    assert bundle.run_params['targetLocale'] == 'en-US'
    assert 'QUALITY ENFORCEMENT' in bundle.text or 'assembly' in bundle.main_prompt_version
