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
    saved = edit(card_motion=10, presentation_prompt='make ilustration', animation_prompt='Будет добавлена анимация')
    stored = plan(saved)
    assert stored.presentation_prompt == illustration_request(saved)
    assert 'Доля анимации — 10%' in stored.presentation_prompt
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
    started = client.post(f'/api/studio/projects/{pid}/create-video', json={
        'animation_percent': 50, 'intensity_percent': 40, 'motion_percent': 80, 'density_percent': 70,
    })
    assert started.status_code == 200
    with connect() as db:
        row = db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='studio_render' AND status='queued'", (pid,)).fetchone()
    payload = json.loads(row[0])
    assert payload['illustration'] is True and payload['manual']['card_motion'] == 50
    assert payload['manual']['animation_intensity'] == 40
    assert payload['manual']['animation_motion'] == 80
    assert payload['manual']['animation_density'] == 70
    assert payload['manual']['voice_cleanup'] is True and payload['manual']['normalize'] is True
    assert payload['manual']['subtitles'] is bool(payload['manual']['captions'])
    assert payload['manual']['font_size'] == 'medium' and payload['manual']['position'] == 'bottom'
    assert payload['manual']['color'] == 'white'
    assert payload['manual']['music'] is None and payload['decisions'] == []
    text = illustration_request(payload['manual'])
    assert payload['manual']['presentation_prompt'] == text
    preview = client.get('/api/studio/picture-prompt?animation_percent=50&intensity_percent=40&motion_percent=80&density_percent=70')
    assert preview.status_code == 200 and preview.json()['prompt'] == text
    assert 'Доля анимации — 50%' in text
    assert 'Интенсивность — 40' in text
    assert 'SPEAKER MUST REMAIN THE PROTAGONIST' in text
    assert "THE USER'S ORIGINAL VIDEO IS THE VIDEO." in text
    assert 'CURATED MEDIA LIBRARY' in text
    assert '1.5–4 seconds' in text
    assert client.post(f'/api/studio/projects/{pid}/create-video', json={'animation_percent': 80}).status_code == 409
    other = create(client).json()['id']
    seed_plan(other)
    changed = client.post(f'/api/studio/projects/{other}/create-video', json={'animation_percent': 80})
    assert changed.status_code == 200
    with connect() as db:
        second = json.loads(db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='studio_render' AND status='queued'", (other,)).fetchone()[0])
    assert second['manual']['card_motion'] == 80
    assert second['manual']['animation_intensity'] == 60
    assert second['manual']['presentation_prompt'] == illustration_request(second['manual'])
    odd = client.post(f'/api/studio/projects/{other}/create-video', json={'animation_percent': 7})
    assert odd.status_code == 422


def test_one_language_switch_sets_card_labels_and_drops_the_three_language_dump(client):
    """One language changes the cards and the request. Three languages are not dumped."""
    from backend.db import connect
    from backend.hypit_prompt import author_source, illustration_request

    sentence = "THE USER'S ORIGINAL VIDEO IS THE VIDEO."
    line = {
        'start': 1.0, 'end': 8.0,
        'original': 'Планируете переезд, второй вид на жительство',
        'ru': 'Планируете переезд, второй вид на жительство',
        'en': 'Are you planning a move, a second residency',
        'zh': '您是否正在计划移居，获取第二居留权',
    }
    late = {
        'start': 30.0, 'end': 36.0,
        'original': 'Поздняя фраза',
        'ru': 'Поздняя фраза',
        'en': 'A later phrase',
        'zh': '较晚的一句',
    }
    bare = {
        'clips': [{'start': 0, 'end': 40}],
        'captions': [line, late],
        'card_motion': 60,
    }
    dumped = illustration_request({**bare, 'translate_all': True})
    assert 'русский:' not in dumped and 'English:' not in dumped and '中文:' not in dumped
    assert 'Планируете переезд' not in dumped and 'Are you planning a move' not in dumped
    assert '您是否正在计划移居' not in dumped
    assert sentence in dumped
    russian = illustration_request({**bare, 'language': 'ru'})
    chinese = illustration_request({**bare, 'language': 'zh'})
    assert sentence in russian and '--- PROJECT LANGUAGE ---' in russian and '"locale": "ru-RU"' in russian
    assert 'Планируете переезд' not in russian and '您是否正在计划移居' not in russian
    assert sentence in chinese and '"locale": "zh-CN"' in chinese and '简体中文' in chinese
    assert '原始视频和脸部保持清晰' not in chinese
    filmed = author_source({**bare, 'language': 'ru'}, 464, 848, duration=40)
    value = filmed.split('id="request">', 1)[1].split('</text:Value>', 1)[0]
    assert sentence in value and 'ru-RU' in value
    assert 'Планируете переезд' not in value and '您是否正在计划移居' not in value
    assert 'русский:' not in filmed and 'English:' not in filmed and '中文:' not in filmed
    picture = filmed.split('<picture>', 1)[1].split('</picture>', 1)[0]
    assert picture.startswith('<Планируете переезд, второй вид на жительство|您是否正在计划移居，获取第二居留权>')
    assert '&lt;' not in picture
    assert 'Планируете переезд' in filmed and '您是否正在计划移居' not in filmed.split('id="motion-1">', 1)[1].split('</text:Value>', 1)[0]
    kept = author_source({**bare, 'language': 'zh'}, 464, 848, duration=40)
    assert '您是否正在计划移居' in kept and 'Планируете переезд' not in kept
    assert 'src="./motion/1.mp4"' in filmed and 'PATTERN INTERRUPTS' in value

    pid = create(client).json()['id']
    seed_plan(pid)
    with connect() as db:
        stored = json.loads(db.execute('SELECT plan FROM studio_projects WHERE project_id=?', (pid,)).fetchone()[0])
        stored['transcript'] = [line]
        db.execute('UPDATE studio_projects SET plan=? WHERE project_id=?', (json.dumps(stored, ensure_ascii=False), pid))
    started = client.post(f'/api/studio/projects/{pid}/create-video', json={
        'animation_percent': 60, 'language': 'ru',
    })
    assert started.status_code == 200
    with connect() as db:
        payload = json.loads(db.execute(
            "SELECT payload FROM jobs WHERE project_id=? AND kind='studio_render' AND status='queued'",
            (pid,),
        ).fetchone()[0])
    assert payload.get('translate_all') is None and payload['manual'].get('translate_all') is not True
    assert payload['language'] == 'ru' and payload['manual']['language'] == 'ru'
    assert payload['manual']['host_language'] == 'ru'
    assert payload['manual']['subtitle_language'] == 'ru'
    assert payload['manual']['effects_language'] == 'ru'
    assert payload['manual']['presentation_prompt'] == illustration_request(payload['manual'])
    assert sentence in payload['manual']['presentation_prompt']
    assert 'Планируете переезд' not in payload['manual']['presentation_prompt']
    markup = author_source(payload['manual'], 464, 848, duration=40)
    assert 'Планируете переезд' in markup
    assert '您是否正在计划移居' not in markup.split('id="motion-1">', 1)[1].split('</text:Value>', 1)[0]
    assert '<Планируете переезд, второй вид на жительство|您是否正在计划移居' in markup
    refused = client.post(f'/api/studio/projects/{pid}/create-video', json={
        'animation_percent': 60, 'translate_all': True,
    })
    assert refused.status_code == 422
    other_language = create(client).json()['id']
    seed_plan(other_language)
    with connect() as db:
        stored = json.loads(db.execute('SELECT plan FROM studio_projects WHERE project_id=?', (other_language,)).fetchone()[0])
        stored['transcript'] = [line]
        db.execute('UPDATE studio_projects SET plan=? WHERE project_id=?', (json.dumps(stored, ensure_ascii=False), other_language))
    pending = client.post(f'/api/studio/projects/{other_language}/create-video', json={
        'animation_percent': 60, 'language': 'en-US',
    })
    assert pending.status_code == 200 and pending.json()['ok'] is True
    with connect() as db:
        queued = db.execute(
            "SELECT payload FROM jobs WHERE project_id=? AND kind='studio_render'",
            (other_language,),
        ).fetchone()
    assert queued is not None
    body = json.loads(queued[0])
    assert body['dubbed'] is True
    assert body['voice'] == 'en-male'
    assert body['voice_resolution']['mode'] == 'dubbed'
    assert body['voice_resolution']['path'] == 'project_default'
    assert 'Выберите язык исходника' not in json.dumps(body, ensure_ascii=False)


def test_effect_board_cannot_change_the_picture(client):
    pid = create(client).json()['id']
    seed_plan(pid)
    effects = {key: False for key in ('blur', 'glow', 'shadow', 'color', 'speed', 'stabilize', 'kinetic', 'progress', 'split', 'screen')}
    effects['color'] = True
    board = client.put(f'/api/studio/projects/{pid}/effect-board', json={'name': 'punch', 'amount': 1.6, 'effects': effects})
    assert board.status_code == 409 and board.json()['detail'] == 'studio_surface_disabled'
    assert client.get(f'/api/studio/projects/{pid}').json()['revision'] == 1


def test_higher_density_films_more_spoken_parts_on_the_figure():
    from backend.tests.test_hypit_picture import _density_markup, _motion_parts

    line = '再看出资节奏，中国认缴时间弹性很大，泰国则要求实缴部分资本，银行开户、工作证、签证申请都会盯着资金到位情况'
    low = _motion_parts(_density_markup(20, line))
    high = _motion_parts(_density_markup(70, line))
    assert len(high) > len(low)
    assert len(high) > 3
    assert 'Визуальная плотность — 70%' in _density_markup(70, line)
    assert 'src="./motion/1.mp4"' in _density_markup(70, line)
