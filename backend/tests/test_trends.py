import json
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app import app, limits
from backend.auth import current_user
from backend.config import settings
from backend.db import connect
from backend import media, trends
from backend.tests.test_studio import create


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    limits.clear()
    app.dependency_overrides[current_user] = lambda: {'id': 'u', 'email': 'test@example.com'}
    with TestClient(app) as api:
        with connect() as db:
            db.execute('INSERT INTO users VALUES(?,?,?,?)', ('u', 'test@example.com', 'disabled', time.time()))
            db.execute('INSERT INTO users VALUES(?,?,?,?)', ('v', 'other@example.com', 'disabled', time.time()))
            ref = dict(aweme_id='1234567890123456789', title='Reference', author='Author', share_url='https://www.douyin.com/video/1234567890123456789', duration=20)
            db.execute('INSERT INTO douyin_results VALUES(?,?,?,?)', ('a' * 32, 'u', json.dumps(ref), time.time()))
            db.execute('INSERT INTO douyin_results VALUES(?,?,?,?)', ('b' * 32, 'v', json.dumps(ref), time.time()))
        monkeypatch.setattr('backend.studio.media.probe', lambda _: dict(duration=40, width=320, height=568, has_audio=False, size=16))
        yield api
    app.dependency_overrides.clear()


def manual(api, **extra):
    body = dict(url='https://example.com/video/1', creator='Ada', published_at=time.time() - 3600, duration=20,
                caption='A quiet tour turns at the door.', hashtags='travel', audio='Original voice', category='travel',
                views=1000, likes=80, comments=10, shares=40)
    body.update(extra)
    return api.post('/api/trends/manual', json=body)


def test_score_prefers_a_fresh_fast_video_over_a_large_old_one():
    now = 1_800_000_000
    old = trends.trend_score(now - 30 * 86400, [{'observed_at': now, 'views': 10_000_000, 'likes': 100_000, 'comments': 1000, 'shares': 1000}], now)
    fresh = trends.trend_score(now - 2 * 3600, [{'observed_at': now, 'views': 50_000, 'likes': 4000, 'comments': 800, 'shares': 2500}], now)
    assert fresh > old
    assert 0 <= old <= 100 and 0 <= fresh <= 100


def test_missing_ass_filter_is_named(monkeypatch):
    monkeypatch.setattr(media, 'ass_available', lambda: False)
    with pytest.raises(RuntimeError, match='ffmpeg_ass_unavailable'):
        media.ffmpeg('-vf', "scale=16:16,ass='caption.ass'", 'out.mp4')


def test_manual_trend_stores_metadata_without_a_download(client, tmp_path):
    response = manual(client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body['source'] == 'manual'
    assert body['sample'] is False
    assert body['score'] > 0
    assert [path.name for path in tmp_path.iterdir()] == ['lumen.db']
    app.dependency_overrides[current_user] = lambda: {'id': 'v', 'email': 'other@example.com'}
    assert client.get('/api/trends/' + body['id']).status_code == 404


def test_samples_are_labeled_and_not_fetched(client):
    listing = client.get('/api/trends').json()
    assert {row['source'] for row in listing['samples']} == {'instagram', 'tiktok', 'youtube'}
    assert all(row['sample'] and row['url'].startswith('https://example.invalid/') for row in listing['samples'])
    saved = client.post('/api/trends/samples/tiktok')
    assert saved.status_code == 201
    assert saved.json()['sample'] is True
    assert client.post('/api/trends/samples/missing').status_code == 404


def test_concept_links_into_an_ordinary_studio_project(client):
    ident = manual(client).json()['id']
    assert client.post(f'/api/trends/{ident}/concepts').status_code == 409
    detail = client.post(f'/api/trends/{ident}/analyze').json()
    assert detail['dna']['slots'] == list(trends.SLOTS)
    assert 'not downloaded' in detail['dna']['why']
    made = client.post(f'/api/trends/{ident}/concepts').json()
    concept = next(row for row in made['concepts'] if row['kind'] == 'safe')
    assert 'Do not reuse the reference caption.' in concept['dialogue']
    created = create(client, concept_id=concept['id'])
    assert created.status_code == 422
    chosen = client.post(f'/api/trends/{ident}/concepts/{concept["id"]}/choose').json()
    assert next(row for row in chosen['concepts'] if row['id'] == concept['id'])['chosen'] is True
    created = create(client, concept_id=concept['id'])
    assert created.status_code == 201, created.text
    with connect() as db:
        link = db.execute('SELECT concept_id FROM project_trend_links WHERE project_id=?', (created.json()['id'],)).fetchone()
    assert link['concept_id'] == concept['id']
    plain = create(client)
    assert plain.status_code == 201
    with connect() as db:
        assert db.execute('SELECT 1 FROM project_trend_links WHERE project_id=?', (plain.json()['id'],)).fetchone() is None
    assert client.post(f'/api/trends/{ident}/concepts').status_code == 409


def test_other_user_concept_is_not_attached(client):
    ident = manual(client).json()['id']
    client.post(f'/api/trends/{ident}/analyze')
    concept = client.post(f'/api/trends/{ident}/concepts').json()['concepts'][0]['id']
    client.post(f'/api/trends/{ident}/concepts/{concept}/choose')
    app.dependency_overrides[current_user] = lambda: {'id': 'v', 'email': 'other@example.com'}
    denied = create(client, concept_id=concept, references=['b' * 32], request_id=uuid.uuid4().hex)
    assert denied.status_code == 404
