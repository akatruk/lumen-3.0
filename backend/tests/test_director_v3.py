"""Project «e» create-video renders Director V3 and refuses Hypit."""
import json

import pytest

from backend.db import connect, project
from backend.tests.test_studio import client, create, seed_plan


def test_project_e_create_video_queues_the_remotion_file(client, monkeypatch):
    from backend import director_v3
    pid = create(client).json()['id']
    seed_plan(pid)
    monkeypatch.setattr(director_v3, 'PROJECT_ID', pid)

    def refused(*_args, **_kwargs):
        raise AssertionError('hypit prompt')

    monkeypatch.setattr('backend.hypit_prompt.illustration_request', refused)
    started = client.post(f'/api/studio/projects/{pid}/create-video', json={
        'animation_percent': 100, 'intensity_percent': 100, 'motion_percent': 100, 'density_percent': 100,
        'language': 'ru-RU',
    })
    assert started.status_code == 200
    with connect() as db:
        kinds = [row[0] for row in db.execute('SELECT kind FROM jobs WHERE project_id=? AND status=?', (pid, 'queued'))]
        row = db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='director_v3'", (pid,)).fetchone()
    assert kinds == ['director_v3']
    payload = json.loads(row[0])
    assert payload['composition'] == 'DirectorV3Preview'
    assert payload['duration_seconds'] == 20
    assert 'illustration' not in payload and 'manual' not in payload


def test_project_e_duration_follows_the_control(client, monkeypatch):
    from backend import director_v3
    pid = create(client).json()['id']
    seed_plan(pid)
    monkeypatch.setattr(director_v3, 'PROJECT_ID', pid)
    refused = client.post(f'/api/studio/projects/{pid}/create-video', json={
        'animation_percent': 60, 'intensity_percent': 60, 'motion_percent': 80, 'density_percent': 70,
        'duration_seconds': 45,
    })
    assert refused.status_code == 422
    assert refused.json()['detail'] == 'duration_step'
    chosen = client.post(f'/api/studio/projects/{pid}/create-video', json={
        'animation_percent': 60, 'intensity_percent': 60, 'motion_percent': 80, 'density_percent': 70,
        'duration_seconds': 40,
    })
    assert chosen.status_code == 200
    with connect() as db:
        row = db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='director_v3'", (pid,)).fetchone()
    assert json.loads(row[0])['duration_seconds'] == 40


def test_project_e_hypit_render_is_refused(client, monkeypatch):
    from backend import director_v3
    import backend.studio as studio
    import backend.worker as worker
    pid = create(client).json()['id']
    seed_plan(pid)
    monkeypatch.setattr(director_v3, 'PROJECT_ID', pid)
    current = project(pid)
    with pytest.raises(ValueError, match='director_v3_required'):
        studio.render_job(current, {'illustration': True, 'manual': {'clips': []}, 'plan': {}, 'decisions': [], 'revision': 1})
    with pytest.raises(ValueError, match='director_v3_required'):
        worker.render_job(current, {'illustration': True, 'recommendations': [], 'manual': {}})


def test_director_v3_job_renders_a_new_assembly_and_skips_hypit(client, monkeypatch):
    from backend import director_v3
    from backend.config import settings
    pid = create(client).json()['id']
    seed_plan(pid)
    monkeypatch.setattr(director_v3, 'PROJECT_ID', pid)
    body = b'fresh-remotion-assembly-not-a-copied-preview'
    seen = []

    def fake_render(dest, seconds=20, speaker='speaker.mp4', visual_plan=None):
        seen.append((dest, seconds, speaker, visual_plan))
        dest.write_bytes(body)
        return 'fresh-digest'

    meta = {'duration': 20.05, 'width': 1080, 'height': 1920, 'has_audio': True, 'size': len(body), 'codec': 'h264'}
    monkeypatch.setattr(director_v3, 'render_assembly', fake_render)
    monkeypatch.setattr(director_v3.media, 'probe', lambda path: meta)
    called = []
    monkeypatch.setattr('backend.media.render', lambda *_a, **_k: called.append('media'))
    monkeypatch.setattr('backend.hypit_picture.render_picture', lambda *_a, **_k: called.append('hypit'))
    result = director_v3.run_job(project(pid), {'composition': 'DirectorV3Preview'})
    video = settings.data_dir / pid / 'renders' / result['render_id'] / 'result.mp4'
    assert seen == [(video, 20, 'speaker.mp4', None)]
    assert video.read_bytes() == body
    assert called == []
    saved = project(pid)
    assert saved['status'] == 'complete'
    assert saved['result']['assembled'] is True
    assert saved['result']['picture_engine'] == 'remotion'
    assert saved['result']['composition'] == 'DirectorV3Preview'
    assert saved['result']['duration_seconds'] == 20
    assert saved['result']['delivery_sha256'] == 'fresh-digest'
    assert saved['result']['metadata']['width'] == 1080
    assert saved['result']['metadata']['height'] == 1920


def test_director_v3_source_does_not_copy_the_frozen_preview():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / 'director_v3.py').read_text(encoding='utf-8')
    assert 'shutil' not in source
    assert 'preview-v3.mp4' not in source
    assert 'render_assembly' in source
