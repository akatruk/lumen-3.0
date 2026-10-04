import pytest
from pydantic import ValidationError
from backend.manual import Edit
from backend.presentation_graphics import plan, shown_language
from backend.tests.test_studio import client, create, seed_plan

def edit(**extra):
    captions = extra.pop('captions', [
        {'start': 1, 'end': 2.2, 'original': 'Открытие сцены', 'en': 'Opening scene', 'zh': '开场画面'},
        {'start': 4, 'end': 5.4, 'original': 'Вторая мысль', 'en': 'Second point', 'zh': '第二点'},
        {'start': 8, 'end': 9.2, 'original': 'Третья мысль', 'en': 'Third point', 'zh': '第三点'},
        {'start': 12, 'end': 13.2, 'original': 'Четвёртая мысль', 'en': 'Fourth point', 'zh': '第四点'},
    ])
    body = {'clips': [{'start': 0, 'end': 20}], 'captions': captions, 'presentation_share': 40}
    body.update(extra)
    return Edit.model_validate(body)

def test_slider_percentage_is_the_hypit_prompt():
    low = plan(edit(card_motion=10))
    mid = plan(edit(card_motion=40))
    full = plan(edit(card_motion=100))
    bare = plan(edit(card_motion=0))
    assert low.presentation_prompt.startswith('<?svml using="@hypit/svs@1"?>')
    assert '<render:Video id="final" composition={main.composition}' in low.presentation_prompt
    assert 'make ilustration 10% from all time video' in low.presentation_prompt
    assert 'Будет добавлена анимация' not in low.presentation_prompt
    assert 'end="' not in low.presentation_prompt and 'film.grade' not in low.presentation_prompt
    assert 'film.vignette' not in low.presentation_prompt
    assert 'make ilustration 40% from all time video' in mid.presentation_prompt and 'end="' not in mid.presentation_prompt
    assert 'make ilustration 100% from all time video' in full.presentation_prompt
    assert 'film.grade' not in full.presentation_prompt and 'film.vignette' not in full.presentation_prompt
    assert 'make ilustration 0% from all time video' in bare.presentation_prompt and 'film.grade' not in bare.presentation_prompt
    assert '<performance:Track' in bare.presentation_prompt and 'src="./source.mp4"' in bare.presentation_prompt
    assert low.presentation_prompt != mid.presentation_prompt != full.presentation_prompt != bare.presentation_prompt
    assert len(full.presentation_prompt) < 12000
    covered = sum(beat.end - beat.start for beat in plan(edit(presentation_share=10)).presentation)
    assert covered == pytest.approx(2, abs=0.05)
    quiet = {'name': 'clean', 'amount': 1.6, 'effects': {
        'blur': False, 'glow': False, 'shadow': False, 'color': False, 'speed': False,
        'stabilize': False, 'kinetic': True, 'progress': False, 'split': False, 'screen': False,
    }}
    scaled = plan(edit(card_motion=100), quiet)
    assert 'film.grade' not in scaled.presentation_prompt and 'film.vignette' not in scaled.presentation_prompt
    assert 'Эффекты' not in scaled.presentation_prompt
    colored = plan(edit(card_motion=100), {**quiet, 'effects': {**quiet['effects'], 'color': True, 'kinetic': False}})
    assert colored.presentation_prompt == scaled.presentation_prompt
    assert 'contrast:' not in colored.presentation_prompt

def test_reference_analysis_changes_the_assembled_prompt():
    from backend.hypit_prompt import host_diameter, picture_prompt
    talking = [{
        'visual_type': {'en': 'Talking head with lower photo overlay', 'zh': '口播'},
        'motion': {'en': 'Static medium shot with natural hand gestures', 'zh': '静态'},
    }]
    screen = [{
        'visual_type': {'en': 'Talking head intercut with UI screen overlays', 'zh': '口播'},
        'motion': {'en': 'Document scan overlay with animated avatar cutout', 'zh': '扫描'},
    }]
    bare = picture_prompt(edit())
    photo = picture_prompt(edit(), reference=talking)
    ui = picture_prompt(edit(), reference=screen)
    assert bare == photo == ui
    assert 'make ilustration 100% from all time video' in bare
    assert '50% ширины кадра' not in photo and 'врезка предмета речи' not in photo
    assert 'Talking head with lower photo overlay' not in photo and 'UI screen overlays' not in ui
    assert host_diameter(talking) == 0.5
    assert host_diameter() == 0.5


def test_other_controls_do_not_change_the_hypit_request():
    bare = plan(edit())
    assert 'make ilustration 100% from all time video' in bare.presentation_prompt
    assert 'Будет добавлена анимация' not in bare.presentation_prompt
    assert 'без склейки из кусков' not in bare.presentation_prompt
    assert 'посторонних шумов' not in bare.presentation_prompt
    cleaned = plan(edit(voice_cleanup=True, normalize=True, picture_quality=True, subtitles=True, font_size='large', position='top', color='yellow'))
    assert 'посторонних шумов' not in cleaned.presentation_prompt
    assert 'субтитры по речи' not in cleaned.presentation_prompt
    assert 'make ilustration 100% from all time video' in cleaned.presentation_prompt
    music = plan(edit(music={'asset_id': 'a' * 32, 'gain_db': -18, 'fade_in': 1, 'fade_out': 2, 'duck': True}))
    assert 'фоновую музыку' not in music.presentation_prompt
    accents = plan(edit(clips=[{'start': 0, 'end': 20, 'sound_effects': [{'kind': 'whoosh', 'at': 1}]}]))
    assert 'Звуковые акценты' not in accents.presentation_prompt
    from backend.hypit_prompt import author_source, picture_prompt
    voiced = author_source(edit(voice_cleanup=True), 720, 1280, voiceover=True)
    assert 'make ilustration 100% from all time video' in voiced and 'закадровый голос' not in voiced and 'Будет добавлена анимация' not in voiced
    chinese = author_source(edit(captions=[{'start': 0, 'end': 2, 'original': '很多老板', 'zh': '很多老板', 'en': 'bosses'}]), 720, 1280, language='en')
    assert 'language="zh"' in chinese
    russian = plan(edit(host_language='ru', subtitle_language='ru', subtitles=True))
    assert 'Речь ведущего' not in russian.presentation_prompt
    assert 'make ilustration 100% from all time video' in russian.presentation_prompt
    mixed = plan(edit(host_language='en', subtitle_language='zh', subtitles=True))
    assert 'Субтитры на китайском' not in mixed.presentation_prompt
    same = plan(edit(host_language='ru', effects_language='ru'))
    assert 'Графика и вставки' not in same.presentation_prompt
    plain = picture_prompt({'clips': [{'start': 0, 'end': 4, 'text': '', 'transition': 'cut', 'zoom': 1}], 'captions': []})
    noted = picture_prompt({
        'clips': [
            {'start': 0, 'end': 4, 'text': 'Элитная виза', 'transition': 'crossfade', 'zoom': 1.25, 'approved': True},
            {'start': 4, 'end': 6, 'approved': False},
        ],
        'captions': [{'start': 0, 'end': 2, 'original': 'пауза', 'zh': '精英签', 'en': 'elite visa'}],
        'card_motion': 40,
    })
    moved = picture_prompt({
        'clips': [{'start': 0, 'end': 4, 'text': 'Элитная виза', 'transition': 'crossfade', 'zoom': 1.25, 'approved': True}],
        'captions': [{'start': 0, 'end': 2, 'original': 'пауза', 'zh': '精英签', 'en': 'elite visa'}],
        'card_motion': 80,
    })
    assert 'Элитная виза' not in plain and 'растворение' not in plain and '1.25' not in plain
    assert 'Текст на сцене' not in noted and 'Переходы между фразами' not in noted
    assert 'make ilustration 50% from all time video' in plain
    assert 'make ilustration 40% from all time video' in noted and 'make ilustration 80% from all time video' not in noted
    assert 'make ilustration 80% from all time video' in moved and 'make ilustration 40% from all time video' not in moved
    assert 'Будет добавлена анимация' not in noted
    other = plan(edit(host_language='ru', effects_language='en'))
    assert 'Графика и вставки' not in other.presentation_prompt
    assert 'make ilustration 100% from all time video' in other.presentation_prompt

def test_share_moves_in_steps_of_five_and_covers_that_fraction():
    with pytest.raises(ValidationError):
        Edit.model_validate({'clips': [{'start': 0, 'end': 20}], 'presentation_share': 7})
    planned = plan(edit())
    covered = sum(beat.end - beat.start for beat in planned.presentation)
    assert planned.presentation_share == 40
    assert covered == pytest.approx(8, abs=0.02)
    assert [beat.kind for beat in planned.presentation] == ['window', 'mini', 'window']
    assert planned.presentation[0].title.ru == 'Открытие сцены'
    assert planned.presentation[0].title.zh == '开场画面'
    assert planned.presentation[1].body is not None
    assert { (round(beat.x, 2), round(beat.y, 2)) for beat in planned.presentation } != {(0.5, 0.5)}

def test_zero_share_clears_graphics_and_empty_speech_is_refused():
    assert plan(edit(presentation_share=0)).presentation == []
    with pytest.raises(ValueError, match='presentation_needs_context'):
        plan(edit(presentation_share=20, captions=[], clips=[{'start': 0, 'end': 10, 'text': ''}]))

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

def test_languages_follow_voiceover_then_project():
    assert shown_language('zh', 'ru') == 'ru'
    assert shown_language('zh', None) == 'zh'
    assert shown_language('en') == 'en'
    planned = plan(edit(presentation_share=50, clips=[{'start': 0, 'end': 4}], captions=[
        {'start': 0.4, 'end': 1.6, 'original': 'Окно', 'en': 'Window', 'zh': '窗口'},
        {'start': 2.0, 'end': 3.2, 'original': 'Карточка', 'en': 'Card', 'zh': '卡片'},
    ]))
    assert any(beat.title.zh == '卡片' for beat in planned.presentation)
    assert any(beat.title.ru == 'Карточка' for beat in planned.presentation)
    assert all(beat.title.en != beat.title.zh for beat in planned.presentation)

def test_create_video_enqueues_the_short_prompt(client):
    import json
    from backend.db import connect
    from backend.hypit_prompt import illustration_request
    pid = create(client).json()['id']
    seed_plan(pid)
    refused = client.post(f'/api/studio/projects/{pid}/render', json={'revision': 1})
    assert refused.status_code == 409 and refused.json()['detail'] == 'studio_surface_disabled'
    started = client.post(f'/api/studio/projects/{pid}/create-video', json={'illustration_percent': 50})
    assert started.status_code == 200
    with connect() as db:
        row = db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='studio_render' AND status='queued'", (pid,)).fetchone()
    payload = json.loads(row[0])
    assert payload['illustration'] is True and payload['manual']['card_motion'] == 50
    assert payload['manual']['music'] is None and payload['decisions'] == []
    text = illustration_request(payload['manual']['card_motion'])
    assert payload['manual']['presentation_prompt'] == text
    assert text == (
        'analyze the style of both reference video and reference video 2, make edit to\n'
        'src video 2. focus on adding the appropriate visuals to make it more\n'
        'illustrative. make ilustration 50% from all time video'
    )
    assert client.post(f'/api/studio/projects/{pid}/create-video', json={'illustration_percent': 80}).status_code == 409
    other = create(client).json()['id']
    seed_plan(other)
    changed = client.post(f'/api/studio/projects/{other}/create-video', json={'illustration_percent': 80})
    assert changed.status_code == 200
    with connect() as db:
        second = json.loads(db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='studio_render' AND status='queued'", (other,)).fetchone()[0])
    assert second['manual']['card_motion'] == 80
    assert 'make ilustration 80% from all time video' in illustration_request(80)

def test_effect_board_cannot_change_the_picture(client):
    pid = create(client).json()['id']
    seed_plan(pid)
    effects = {key: False for key in ('blur', 'glow', 'shadow', 'color', 'speed', 'stabilize', 'kinetic', 'progress', 'split', 'screen')}
    effects['color'] = True
    board = client.put(f'/api/studio/projects/{pid}/effect-board', json={'name': 'punch', 'amount': 1.6, 'effects': effects})
    assert board.status_code == 409 and board.json()['detail'] == 'studio_surface_disabled'
    assert client.get(f'/api/studio/projects/{pid}').json()['revision'] == 1
