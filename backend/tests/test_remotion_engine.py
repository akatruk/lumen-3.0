"""Remotion engine V1: feature flag, resolveScenePlan, Hypit fallback."""
from backend import remotion_engine


def test_flag_defaults_off():
    assert remotion_engine.enabled() is False


def test_resolve_scene_plan_strips_illegal_keys_and_is_deterministic():
    visual = {
        'generationId': 'gen_test',
        'visualSeed': 42,
        'artDirection': 'modern_explainer',
        'visualEnergy': 'balanced',
        'scenes': [
            {
                'sceneId': 'hook',
                'semanticPurpose': 'hook',
                'speaker': {'layout': 'speaker_fullscreen', 'x': 99, 'css': 'bad'},
                'background': {'treatment': 'slow_zoom_in', 'fontSize': 80},
                'foreground': {'treatment': 'scale_reveal'},
                'typography': {'animate': 'fade', 'color': '#fff'},
                'transition': 'cut',
                'motionIntensity': 'high',
            }
        ],
    }
    first = remotion_engine.resolve_scene_plan(
        visual_plan=visual, locale='ru-RU', duration_seconds=20, speaker_file='speaker.mp4',
    )
    second = remotion_engine.resolve_scene_plan(
        visual_plan=visual, locale='ru-RU', duration_seconds=20, speaker_file='speaker.mp4',
        generation_id='gen_test',
    )
    assert first['engine'] == 'remotion'
    assert first['fps'] == 30
    assert first['width'] == 1080
    assert first['height'] == 1920
    assert first['visualSeed'] == 42
    assert 'animated_diagram' in first['motionRegistry']
    assert 'x' not in first['scenes'][0]['speaker']
    assert 'css' not in first['scenes'][0]['speaker']
    assert 'fontSize' not in first['scenes'][0]['background']
    assert 'color' not in first['scenes'][0]['typography']
    assert first['scenes'] == second['scenes']
    assert first['audio']['speechDominant'] is True


def test_store_and_reload_render_plan(tmp_path):
    plan = remotion_engine.resolve_scene_plan(
        visual_plan={'visualSeed': 7, 'scenes': []},
        generation_id='gen_store',
    )
    dest = remotion_engine.store_render_plan(tmp_path, 'proj', plan)
    assert dest.is_file()
    latest = (tmp_path / 'proj' / 'remotion-plans' / 'latest.json')
    assert latest.is_file()
    assert '"gen_store"' in latest.read_text(encoding='utf-8')


def test_project_e_uses_remotion_even_when_flag_off(monkeypatch):
    from backend import director_v3
    monkeypatch.setattr(remotion_engine.settings, 'remotion_engine_enabled', False)
    assert remotion_engine.should_use_remotion(director_v3.PROJECT_ID) is True
    assert remotion_engine.should_use_remotion('other') is False
    monkeypatch.setattr(remotion_engine.settings, 'remotion_engine_enabled', True)
    assert remotion_engine.should_use_remotion('other') is True
