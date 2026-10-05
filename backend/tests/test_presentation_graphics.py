"""The hand prompt is what create-video stores. Retired studio surfaces stay closed."""
import json

from backend.hypit_prompt import illustration_request, plan
from backend.manual import Edit
from backend.tests.test_studio import client, create, seed_plan


def edit(**extra):
    captions = extra.pop('captions', [
        {'start': 1, 'end': 2.2, 'original': 'Открытие сцены', 'en': 'Opening scene', 'zh': '开场画面'},
    ])
    body = {'clips': [{'start': 0, 'end': 20}], 'captions': captions, 'presentation_share': 40}
    body.update(extra)
    return Edit.model_validate(body)


def test_plan_stores_the_hand_prompt():
    stored = plan(edit(card_motion=10, presentation_prompt='make ilustration', animation_prompt='Будет добавлена анимация'))
    assert stored.presentation_prompt == illustration_request()
    assert stored.animation_prompt == ''
    assert stored.presentation == []
    assert 'make ilustration' not in stored.presentation_prompt
    assert '<?svml' not in stored.presentation_prompt


def test_retired_studio_surfaces_do_not_change_the_picture(client):
    pid = create(client).json()['id']
    seed_plan(pid)
    url = f'/api/studio/projects/{pid}/manual'
    body = {'revision': 1, 'edit': edit(presentation_share=20, clips=[{'start': 0, 'end': 10}], captions=[
        {'start': 1, 'end': 3, 'original': 'Привет', 'en': 'Hello', 'zh': '你好'},
    ]).model_dump()}
    scanned = client.post(url + '/presentation', json=body)
    assert scanned.status_code == 409 and scanned.json()['detail'] == 'studio_surface_disabled'
    assert client.get(url).json()['saved'] is False
    saved = client.put(url, json={'revision': 1, 'edit': body['edit']})
    assert saved.status_code == 409 and saved.json()['detail'] == 'studio_surface_disabled'


def test_create_video_enqueues_the_short_prompt(client):
    from backend.db import connect
    pid = create(client).json()['id']
    seed_plan(pid)
    refused = client.post(f'/api/studio/projects/{pid}/render', json={'revision': 1})
    assert refused.status_code == 409 and refused.json()['detail'] == 'studio_surface_disabled'
    started = client.post(f'/api/studio/projects/{pid}/create-video', json={'illustration_percent': 50})
    assert started.status_code == 200
    with connect() as db:
        row = db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='studio_render' AND status='queued'", (pid,)).fetchone()
    payload = json.loads(row[0])
    assert payload['illustration'] is True and payload['manual']['card_motion'] == 40
    assert payload['manual']['animation_intensity'] == 60
    assert payload['manual']['animation_motion'] == 80
    assert payload['manual']['animation_density'] == 70
    assert payload['manual']['voice_cleanup'] is True and payload['manual']['normalize'] is True
    assert payload['manual']['subtitles'] is bool(payload['manual']['captions'])
    assert payload['manual']['font_size'] == 'medium' and payload['manual']['position'] == 'bottom'
    assert payload['manual']['color'] == 'white'
    assert payload['manual']['music'] is None and payload['decisions'] == []
    text = illustration_request()
    assert payload['manual']['presentation_prompt'] == text
    assert 'Анимация 40%  ведущий' in text
    assert 'Звуковые акценты: щелчок, свист, колокольчик.' in text
    assert client.post(f'/api/studio/projects/{pid}/create-video', json={'illustration_percent': 80}).status_code == 409
    other = create(client).json()['id']
    seed_plan(other)
    changed = client.post(f'/api/studio/projects/{other}/create-video', json={'illustration_percent': 80})
    assert changed.status_code == 200
    with connect() as db:
        second = json.loads(db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='studio_render' AND status='queued'", (other,)).fetchone()[0])
    assert second['manual']['card_motion'] == 40
    assert second['manual']['presentation_prompt'] == illustration_request()


def test_effect_board_cannot_change_the_picture(client):
    pid = create(client).json()['id']
    seed_plan(pid)
    effects = {key: False for key in ('blur', 'glow', 'shadow', 'color', 'speed', 'stabilize', 'kinetic', 'progress', 'split', 'screen')}
    effects['color'] = True
    board = client.put(f'/api/studio/projects/{pid}/effect-board', json={'name': 'punch', 'amount': 1.6, 'effects': effects})
    assert board.status_code == 409 and board.json()['detail'] == 'studio_surface_disabled'
    assert client.get(f'/api/studio/projects/{pid}').json()['revision'] == 1
