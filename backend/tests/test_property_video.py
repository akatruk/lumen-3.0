import json
import subprocess
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app import app, limits
from backend.auth import current_user
from backend.config import settings
from backend.db import connect, project
from backend.hypit_package import _owned
from backend.media import ffmpeg, probe
from backend.worker import run_once
from backend import studio


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    limits.clear()
    app.dependency_overrides[current_user] = lambda: {'id': 'u', 'email': 'test@example.com'}
    with TestClient(app) as api:
        with connect() as db:
            db.execute('INSERT INTO users VALUES(?,?,?,?)', ('u', 'test@example.com', 'disabled', time.time()))
            ref = dict(aweme_id='1234567890123456789', title='Reference', author='Author', share_url='https://www.douyin.com/video/1234567890123456789', duration=20)
            db.execute('INSERT INTO douyin_results VALUES(?,?,?,?)', ('a' * 32, 'u', json.dumps(ref), time.time()))
        monkeypatch.setattr(studio.media, 'probe', lambda _: dict(duration=40, width=320, height=568, has_audio=False, size=16))
        yield api
    app.dependency_overrides.clear()


def _video(path, seconds=6):
    subprocess.run(
        ['ffmpeg', '-hide_banner', '-nostdin', '-y', '-f', 'lavfi', '-i', f'color=c=0x223322:s=320x568:d={seconds}:r=30',
         '-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}', '-shortest',
         '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-f', 'mp4', str(path)],
        check=True, capture_output=True,
    )


def _brief(**overrides):
    body = {
        'audience': 'Families comparing homes',
        'language': 'en',
        'facts': [{'key': 'bedrooms', 'value': '3', 'source': 'Owner sheet', 'status': 'verified'}],
        'highlights': ['bedrooms'],
        'hook': 'A quiet home',
        'brand': 'North Line',
        'cta': {'text': 'Ask for a viewing', 'contact': 'desk@example.com'},
        'destinations': ['youtube_shorts'],
    }
    body.update(overrides)
    return body


def _ready(client, pid):
    _video(settings.data_dir / pid / 'source')
    (settings.data_dir / pid / 'reference_source').write_bytes(b'reference-must-stay-out')
    meta = probe(settings.data_dir / pid / 'source')
    with connect() as db:
        db.execute("UPDATE jobs SET status='complete' WHERE project_id=?", (pid,))
        db.execute('UPDATE projects SET metadata=?,status=? WHERE id=?', (json.dumps(meta), 'ready', pid))
    return meta


def test_reference_media_cannot_enter_the_package(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    pid = 'a' * 32
    folder = tmp_path / pid / 'references' / 'clip'
    folder.mkdir(parents=True)
    (folder / 'source').write_bytes(b'x' * 64)
    try:
        _owned(pid, 'references/clip/source')
    except ValueError as exc:
        assert str(exc) == 'reference_media_blocked'
    else:
        raise AssertionError('reference path was accepted')


def test_property_plan_rejects_unsupplied_numbers(client):
    from backend.tests.test_studio import create
    pid = create(client, creator={'topic': 'real_estate', 'audience': 'Buyers', 'tone': 'Calm', 'rules': 'No invented facts'}).json()['id']
    _ready(client, pid)
    invented = _brief(hook='Only 9 homes left')
    rejected = client.put(f'/api/studio/projects/{pid}/property', json=invented)
    assert rejected.status_code == 422 and rejected.json()['detail'] == 'unverified_claim'
    saved = client.put(f'/api/studio/projects/{pid}/property', json=_brief())
    assert saved.status_code == 200, saved.text
    plan = client.post(f'/api/studio/projects/{pid}/property/plan')
    assert plan.status_code == 200, plan.text
    body = plan.json()
    assert body['plan']['show_location'] is False
    assert all('location' not in scene for scene in body['plan']['scenes'])
    assert body['plan']['reference_media'] == 'technique_only'
    assert body['plan']['illustrative_in_picture'] is False
    scenes = [{'id': scene['id'], 'caption': scene['caption']} for scene in body['plan']['scenes']]
    scenes[1]['caption'] = 'Bedrooms: 9'
    edited = client.put(f'/api/studio/projects/{pid}/property/plan', json={'revision': body['plan_revision'], 'scenes': scenes})
    assert edited.status_code == 422 and edited.json()['detail'] == 'unverified_claim'
    scenes[1]['caption'] = 'Bedrooms: 3, as supplied'
    edited = client.put(f'/api/studio/projects/{pid}/property/plan', json={'revision': body['plan_revision'], 'scenes': scenes})
    assert edited.status_code == 200
    assert client.post(f'/api/studio/projects/{pid}/property/render', json={'revision': edited.json()['plan_revision'], 'request_id': uuid.uuid4().hex}).status_code == 409


def test_property_render_keeps_the_selected_file(client, monkeypatch):
    from backend.tests.test_studio import create
    pid = create(client, creator={'topic': 'real_estate', 'audience': 'Buyers', 'tone': 'Calm', 'rules': 'No invented facts'}).json()['id']
    _ready(client, pid)
    assert client.put(f'/api/studio/projects/{pid}/property', json=_brief(language='ru')).status_code == 200
    planned = client.post(f'/api/studio/projects/{pid}/property/plan')
    assert planned.status_code == 200, planned.text
    revision = planned.json()['plan_revision']
    assert 'Спальни: 3' in planned.json()['plan']['scenes'][1]['caption']
    assert client.post(f'/api/studio/projects/{pid}/property/approve', json={'revision': revision}).status_code == 200
    request_id = uuid.uuid4().hex

    def fake_deliver(work):
        page = (work / 'main.svml').read_text()
        assert 'Спальни: 3' in page
        assert 'desk@example.com' in page
        assert 'reference_source' not in page
        assert 'data-hypit-start-frame' not in page
        assert not (work / 'index.html').exists()
        ffmpeg('-i', work / 'cut.mp4', '-c', 'copy', work / 'visual.mp4')
        return work / 'visual.mp4'

    monkeypatch.setattr('backend.hypit_picture.deliver', fake_deliver)
    queued = client.post(f'/api/studio/projects/{pid}/property/render', json={'revision': revision, 'request_id': request_id})
    assert queued.status_code == 200, queued.text
    render_id = queued.json()['render_id']
    assert run_once() is True
    package = json.loads((settings.data_dir / pid / 'renders' / render_id / 'package.json').read_text())
    assert package['schema'] == 'lumen.hypit.package.v1'
    assert package['reference_media_included'] is False
    assert package['inputs'] == [{'role': 'owned_footage', 'path': 'source', 'bytes': package['inputs'][0]['bytes'], 'media_type': 'video/mp4', 'sha256': package['inputs'][0]['sha256']}]
    assert package['cost']['external_model_usd'] == 0
    assert 'Hypit is Apache License 2.0' in package['notices'][0]
    media = probe(settings.data_dir / pid / 'renders' / render_id / 'result.mp4')
    assert media['has_audio'] is True
    assert abs(media['duration'] - package['canvas']['frame_count'] / 30) < 0.45
    assert project(pid)['result'] is None
    preview = client.get(f'/api/projects/{pid}/media/result?render={render_id}')
    assert preview.status_code == 200
    assert preview.content[4:8] == b'ftyp'
    assert client.get(f'/api/projects/{pid}/media/result').status_code == 404
    approved = client.post(f'/api/studio/projects/{pid}/property/delivery', json={'render_id': render_id})
    assert approved.status_code == 200, approved.text
    saved = project(pid)['result']
    assert saved['render_id'] == render_id
    assert saved['generated_clips'] == 0
    assert saved['qa_status'] == 'unavailable'
    assert saved['metadata']['duration'] == media['duration']
    assert saved['metadata']['has_audio'] is True
    downloaded = client.get(f'/api/projects/{pid}/media/result')
    assert downloaded.status_code == 200
    assert downloaded.content == preview.content
    again = client.post(f'/api/studio/projects/{pid}/property/render', json={'revision': revision, 'request_id': request_id})
    assert again.json()['duplicate'] is True and again.json()['render_id'] == render_id

    kept = (settings.data_dir / pid / 'renders' / render_id / 'result.mp4').read_bytes()
    edited = client.get(f'/api/studio/projects/{pid}/property').json()
    scenes = [{'id': scene['id'], 'caption': scene['caption']} for scene in edited['plan']['scenes']]
    scenes[1]['caption'] = 'Спальни: 3. Светлая комната'
    changed = client.put(f'/api/studio/projects/{pid}/property/plan', json={'revision': edited['plan_revision'], 'scenes': scenes})
    assert changed.status_code == 200, changed.text
    next_revision = changed.json()['plan_revision']
    assert client.post(f'/api/studio/projects/{pid}/property/approve', json={'revision': next_revision}).status_code == 200

    def fail_deliver(work):
        raise RuntimeError('hypit_unavailable')

    monkeypatch.setattr('backend.hypit_picture.deliver', fail_deliver)
    failed = client.post(f'/api/studio/projects/{pid}/property/render', json={'revision': next_revision, 'request_id': uuid.uuid4().hex})
    assert failed.status_code == 200, failed.text
    failed_id = failed.json()['render_id']
    assert run_once() is True
    current = project(pid)
    assert current['error'] == 'hypit_unavailable'
    assert current['result']['render_id'] == render_id
    assert (settings.data_dir / pid / 'renders' / render_id / 'result.mp4').read_bytes() == kept
    assert not (settings.data_dir / pid / 'renders' / failed_id).exists()
    reloaded = client.get(f'/api/projects/{pid}/media/result')
    assert reloaded.content == kept
    with connect() as db:
        analyze_jobs = db.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND kind='studio_analyze'", (pid,)).fetchone()[0]
    blocked = client.post(f'/api/projects/{pid}/retry')
    assert blocked.status_code == 409 and blocked.json()['detail'] == 'property_workflow'
    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND kind='studio_analyze'", (pid,)).fetchone()[0] == analyze_jobs
        assert db.execute("SELECT 1 FROM jobs WHERE project_id=? AND kind='studio_analyze' AND status IN ('queued','running')", (pid,)).fetchone() is None
    current = project(pid)
    assert current['error'] == 'hypit_unavailable'
    assert current['topic'] == 'real_estate'
    assert current['result']['render_id'] == render_id
    assert (settings.data_dir / pid / 'renders' / render_id / 'result.mp4').read_bytes() == kept


def _png(path):
    subprocess.run(
        ['ffmpeg', '-hide_banner', '-nostdin', '-y', '-f', 'lavfi', '-i', 'color=c=white:s=32x32', '-frames:v', '1', '-f', 'image2', '-c:v', 'png', str(path)],
        check=True, capture_output=True,
    )


def _wav(path):
    subprocess.run(
        ['ffmpeg', '-hide_banner', '-nostdin', '-y', '-f', 'lavfi', '-i', 'sine=frequency=220:duration=2', '-f', 'wav', str(path)],
        check=True, capture_output=True,
    )


def _library(pid, ident, title, meta, writer):
    folder = settings.data_dir / pid / 'assets'
    folder.mkdir(parents=True, exist_ok=True)
    writer(folder / ident)
    with connect() as db:
        db.execute(
            'INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)',
            (ident, pid, uuid.uuid4().hex, title, 'Owner', json.dumps(meta), time.time()),
        )


def test_owned_music_logo_and_photo_reach_the_picture_and_an_illustration_does_not(client, monkeypatch):
    from backend.tests.test_studio import create
    pid = create(client, creator={'topic': 'real_estate', 'audience': 'Buyers', 'tone': 'Calm', 'rules': 'No invented facts'}).json()['id']
    _ready(client, pid)
    music, logo, photo, drawing = (uuid.uuid4().hex for _ in range(4))
    _library(pid, music, 'Bed track', {'kind': 'music', 'duration': 2, 'mime': 'audio/wav'}, _wav)
    _library(pid, logo, 'North Line mark', {'kind': 'image', 'role': 'logo', 'mime': 'image/png', 'width': 32, 'height': 32}, _png)
    _library(pid, photo, 'Living room', {'kind': 'image', 'role': 'photo', 'mime': 'image/png', 'width': 32, 'height': 32}, _png)
    _library(pid, drawing, 'Sketch', {'kind': 'image', 'role': 'illustration', 'mime': 'image/png', 'width': 32, 'height': 32}, _png)
    rejected = client.put(f'/api/studio/projects/{pid}/property', json=_brief(music_asset_id=logo))
    assert rejected.status_code == 422 and rejected.json()['detail'] == 'invalid_media_path'
    saved = client.put(f'/api/studio/projects/{pid}/property', json=_brief(
        music_asset_id=music, logo_asset_id=logo, photo_asset_ids=[photo], illustrative_asset_ids=[drawing],
    ))
    assert saved.status_code == 200, saved.text
    planned = client.post(f'/api/studio/projects/{pid}/property/plan')
    assert planned.status_code == 200, planned.text
    plan = planned.json()['plan']
    assert plan['illustrative_in_picture'] is False
    assert plan['music_asset_id'] == music and plan['logo_asset_id'] == logo and plan['photo_asset_ids'] == [photo]
    revision = planned.json()['plan_revision']
    assert client.post(f'/api/studio/projects/{pid}/property/approve', json={'revision': revision}).status_code == 200

    def fake_deliver(work):
        page = (work / 'main.svml').read_text()
        assert 'logo.png' in page and 'photo.png' in page
        assert drawing not in page and 'Sketch' not in page
        assert (work / 'logo.png').is_file() and (work / 'photo.png').is_file()
        assert not (work / drawing).exists()
        assert not (work / 'index.html').exists()
        ffmpeg('-i', work / 'cut.mp4', '-c', 'copy', work / 'visual.mp4')
        return work / 'visual.mp4'

    monkeypatch.setattr('backend.hypit_picture.deliver', fake_deliver)
    queued = client.post(f'/api/studio/projects/{pid}/property/render', json={'revision': revision, 'request_id': uuid.uuid4().hex})
    assert queued.status_code == 200, queued.text
    render_id = queued.json()['render_id']
    assert run_once() is True
    package = json.loads((settings.data_dir / pid / 'renders' / render_id / 'package.json').read_text())
    assert [item['role'] for item in package['inputs']] == ['owned_footage', 'logo', 'owned_photo', 'music']
    assert package['illustrative'] == [{
        'asset_id': drawing, 'title': 'Sketch', 'in_picture': False, 'label': 'illustration_not_the_property',
    }]
    assert package['illustrative'][0]['in_picture'] is False
    media = probe(settings.data_dir / pid / 'renders' / render_id / 'result.mp4')
    assert media['has_audio'] is True


def test_capture_failure_note_omits_the_command_and_secrets(monkeypatch):
    from backend.hypit_picture import spawn
    from backend.worker import failure_detail

    def boom(*_args, **_kwargs):
        err = subprocess.CalledProcessError(2, ['node', 'DO-NOT-LOG-ARGV'])
        err.stderr = 'Error: browser closed before Chrome\napi_key=sk-abcdefghijklmnop'
        err.stdout = ''
        raise err

    monkeypatch.setattr('backend.hypit_picture.subprocess.run', boom)
    try:
        spawn(['node', 'job.json'], {})
    except subprocess.CalledProcessError as exc:
        wrapped = RuntimeError('hypit_unavailable')
        wrapped.__cause__ = exc
        text = failure_detail(wrapped)
    else:
        raise AssertionError('spawn returned')
    assert 'DO-NOT-LOG-ARGV' not in text
    assert 'sk-' not in text
    assert 'browser closed before Chrome' in text
    assert 'exit 2' in text
