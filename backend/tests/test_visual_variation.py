"""A visual seed is resolved before render and stays reproducible."""
import json

from backend.tests.test_studio import client, create, seed_plan
from backend.visual_variation import resolve_plan


def _signature(plan):
    return [
        (
            scene['sceneId'],
            scene['speaker']['layout'],
            scene['background']['treatment'],
            scene['background'].get('assetId'),
            scene['typography']['treatment'],
            scene['transition'],
            scene['artDirection'] if False else plan['artDirection'],
        )
        for scene in plan['scenes']
    ]


def test_recent_generations_move_the_next_plan_off_the_same_assets():
    first = resolve_plan(839204, 'balanced')
    used = [scene['background']['assetId'] for scene in first['scenes'] if scene['background'].get('assetId')]
    assert used
    second = resolve_plan(839204, 'balanced', recent_ids=used)
    again = [scene['background']['assetId'] for scene in second['scenes'] if scene['background'].get('assetId')]
    assert again
    assert set(used).isdisjoint(set(again)) or len(set(used) - set(again)) >= 1


def test_same_seed_reproduces_the_plan():
    first = resolve_plan(839204, 'balanced')
    second = resolve_plan(839204, 'balanced')
    assert first == second
    assert first['artDirection'] in {
        'cinematic_editorial', 'dynamic_social', 'premium_motion_graphics',
        'documentary', 'modern_explainer', 'luxury_minimal',
    }
    assert len({scene['sceneId'] for scene in first['scenes']}) == 6


def test_different_seeds_change_the_treatment_when_alternatives_exist():
    plans = [resolve_plan(seed, 'dynamic') for seed in (11, 839204, 550773)]
    signatures = {json.dumps(_signature(plan), sort_keys=True) for plan in plans}
    assert len(signatures) >= 2
    for plan in plans:
        layouts = [scene['speaker']['layout'] for scene in plan['scenes']]
        assert layouts[0] in ('speaker_fullscreen', 'speaker_closeup', 'speaker_medium', 'speaker_punch_in')
        assert plan['scenes'][2]['background']['treatment'] == 'ambient_loop' or plan['scenes'][2]['background'].get('file')


def test_create_video_stores_one_plan_and_keep_reuses_it(client, monkeypatch):
    from backend import director_v3
    from backend.db import connect
    pid = create(client).json()['id']
    seed_plan(pid)
    monkeypatch.setattr(director_v3, 'PROJECT_ID', pid)
    body = {
        'animation_percent': 60, 'intensity_percent': 60, 'motion_percent': 80, 'density_percent': 70,
        'duration_seconds': 20, 'visual_variation': 'automatic', 'visual_energy': 'balanced',
    }
    assert client.post(f'/api/studio/projects/{pid}/create-video', json=body).status_code == 200
    with connect() as db:
        first = json.loads(db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='director_v3'", (pid,)).fetchone()[0])
        db.execute("DELETE FROM jobs WHERE project_id=?", (pid,))
    kept = dict(body, visual_variation='keep')
    assert client.post(f'/api/studio/projects/{pid}/create-video', json=kept).status_code == 200
    with connect() as db:
        second = json.loads(db.execute(
            "SELECT payload FROM jobs WHERE project_id=? AND kind='director_v3' ORDER BY created DESC",
            (pid,),
        ).fetchone()[0])
    assert first['visual_plan']['visualSeed'] == second['visual_plan']['visualSeed']
    assert first['visual_plan']['scenes'] == second['visual_plan']['scenes']


def test_language_switch_keeps_the_visual_plan(client, monkeypatch):
    from backend import director_v3
    from backend.db import connect
    pid = create(client).json()['id']
    seed_plan(pid)
    monkeypatch.setattr(director_v3, 'PROJECT_ID', pid)
    body = {
        'animation_percent': 60, 'intensity_percent': 60, 'motion_percent': 80, 'density_percent': 70,
        'duration_seconds': 20, 'visual_variation': 'automatic', 'visual_energy': 'balanced',
        'language': 'ru-RU',
    }
    assert client.post(f'/api/studio/projects/{pid}/create-video', json=body).status_code == 200
    with connect() as db:
        first = json.loads(db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='director_v3'", (pid,)).fetchone()[0])
        db.execute("DELETE FROM jobs WHERE project_id=?", (pid,))
    switched = dict(body, language='zh-CN')
    assert client.post(f'/api/studio/projects/{pid}/create-video', json=switched).status_code == 200
    with connect() as db:
        second = json.loads(db.execute(
            "SELECT payload FROM jobs WHERE project_id=? AND kind='director_v3' ORDER BY created DESC",
            (pid,),
        ).fetchone()[0])
    assert first['visual_plan']['visualSeed'] == second['visual_plan']['visualSeed']
    assert first['visual_plan']['scenes'] == second['visual_plan']['scenes']
