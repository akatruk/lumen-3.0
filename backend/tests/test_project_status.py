"""Project GET exposes live job status for Studio UI."""
from backend.project_status import attach_job_status
from backend.tests.test_studio import client, create, seed_plan  # noqa: F401


def test_attach_job_status_includes_latest_job(client):
    from backend.db import connect, enqueue

    pid = create(client).json()['id']
    seed_plan(pid)
    with connect() as db:
        enqueue(db, pid, 'director_v3', {
            'composition': 'DirectorV3Preview',
            'language': 'en-US',
            'target_language': 'en-US',
            'duration_seconds': 20,
        })
    body = client.get(f'/api/projects/{pid}').json()
    assert body['latest_job']['kind'] == 'director_v3'
    assert body['latest_job']['status'] == 'queued'
    assert body['latest_job']['language'] == 'en-US'
    assert body['active_job']['id'] == body['latest_job']['id']


def test_attach_job_status_maps_short_language_code():
    out = attach_job_status({'id': None, 'language': 'ru'})
    assert out['latest_job'] is None
    assert out['video_language'] == 'ru-RU'
