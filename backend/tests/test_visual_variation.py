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


def test_director_can_retrieve_runpod_prefixes(monkeypatch, tmp_path):
    """hypit_/v2_/rp_ stills must be eligible — editorial_object is not filtered out."""
    import json
    from pathlib import Path

    from backend import visual_variation as vv

    manifest = {
        'assets': [
            {
                'id': 'rp_photo_001', 'type': 'image', 'visualFamily': 'photography',
                'source': 'runpod', 'qualityScore': 0.9, 'file': 'static/runpod/photographs/rp_photo_001.png',
                'conceptId': 'immigration.approval', 'tags': ['passport', 'document', 'approval'],
                'description': {'en': 'passport document approval'}, 'sceneRoles': ['explanation'],
                'category': 'people', 'energy': 'low',
            },
            {
                'id': 'hypit_detail_001', 'type': 'image', 'visualFamily': 'editorial_object',
                'source': 'runpod', 'qualityScore': 0.9, 'file': 'static/runpod/details/hypit_detail_001.png',
                'conceptId': 'immigration.document_consultation', 'tags': ['document', 'review', 'desk', 'detail'],
                'description': {'en': 'document review desk'}, 'sceneRoles': ['explanation'],
                'category': 'details', 'energy': 'low', 'action': 'detail',
            },
            {
                'id': 'v2_object_001', 'type': 'image', 'visualFamily': 'editorial_object',
                'source': 'runpod', 'qualityScore': 0.9, 'file': 'static/runpod/objects/v2_object_001.png',
                'conceptId': 'immigration.second_passport', 'tags': ['passport', 'document', 'object'],
                'description': {'en': 'passport document object'}, 'sceneRoles': ['explanation'],
                'category': 'objects', 'energy': 'low', 'action': 'object',
            },
            {
                'id': 'i2v_consult_001', 'type': 'video', 'visualFamily': 'generative_motion',
                'source': 'generated', 'qualityScore': 0.8, 'file': 'motion/people/i2v_consult_001.mp4',
                'conceptId': 'immigration.document_consultation',
                'tags': ['consultation', 'meeting', 'advisor'],
                'description': {'en': 'consultation meeting'}, 'sceneRoles': ['explanation'],
                'category': 'people', 'energy': 'medium',
            },
        ]
    }
    lib = tmp_path / 'out'
    lib.mkdir()
    (lib / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    for asset in manifest['assets']:
        path = lib / asset['file']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'x' * 2048)
    monkeypatch.setattr(vv, 'LIBRARY', lib)
    plan = vv.resolve_plan(424242, 'balanced')
    ids = {
        (scene.get('background') or {}).get('assetId')
        for scene in plan['scenes']
        if (scene.get('background') or {}).get('assetId')
    }
    ids |= {
        (scene.get('foreground') or {}).get('assetId')
        for scene in plan['scenes']
        if (scene.get('foreground') or {}).get('assetId') not in (None, 'passport.png')
    }
    assert ids & {'rp_photo_001', 'hypit_detail_001', 'v2_object_001', 'i2v_consult_001'}
    # Same seed stays reproducible after the eligibility fix.
    assert vv.resolve_plan(424242, 'balanced') == plan


def test_cross_seed_plans_diversify_background_assets(monkeypatch, tmp_path):
    import json

    from backend import visual_variation as vv

    assets = []
    for i, prefix in enumerate(('rp_photo', 'hypit_photo', 'v2_photo', 'rp_detail', 'v2_object')):
        for n in range(1, 5):
            aid = f'{prefix}_{n:03d}'
            assets.append({
                'id': aid, 'type': 'image',
                'visualFamily': 'photography' if 'photo' in prefix else 'editorial_object',
                'source': 'runpod', 'qualityScore': 0.84,
                'file': f'static/runpod/{aid}.png',
                'conceptId': f'concept.{i}.{n}',
                'tags': ['passport', 'document', 'approval', 'consultation', 'meeting', 'advisor'],
                'description': {'en': 'passport document approval consultation meeting'},
                'sceneRoles': ['explanation'],
                'category': 'objects' if 'object' in prefix else ('details' if 'detail' in prefix else 'people'),
                'energy': 'low', 'action': 'object' if 'object' in prefix else 'photograph',
            })
    lib = tmp_path / 'out'
    lib.mkdir()
    (lib / 'manifest.json').write_text(json.dumps({'assets': assets}), encoding='utf-8')
    for asset in assets:
        path = lib / asset['file']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'x' * 2048)
    monkeypatch.setattr(vv, 'LIBRARY', lib)
    picked = []
    for seed in (11, 22, 33, 44, 55, 66):
        plan = vv.resolve_plan(seed, 'balanced', recent_ids=picked[-8:])
        for scene in plan['scenes']:
            for key in ('background', 'foreground'):
                aid = (scene.get(key) or {}).get('assetId')
                if aid and aid != 'passport.png':
                    picked.append(aid)
    assert len(set(picked)) >= 6


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
