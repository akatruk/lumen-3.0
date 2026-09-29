import os
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError
from backend.manual import Edit
from backend.media import ffmpeg, probe, render
from backend.presentation_graphics import plan, shown_language, write_presentation
from backend.schemas import Analysis
from backend.tests.test_render import T
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
    assert 'end="2.000s"' in low.presentation_prompt
    assert 'contrast: 1.040' in low.presentation_prompt
    assert 'film.vignette' not in low.presentation_prompt
    assert 'end="8.000s"' in mid.presentation_prompt
    assert 'style={title-style} during="program"' not in mid.presentation_prompt
    assert 'style={title-style} during="program"' in full.presentation_prompt
    assert 'contrast: 1.220' in full.presentation_prompt and 'film.vignette { amount: 0.550; }' in full.presentation_prompt
    assert 'size: 72' in full.presentation_prompt
    assert '<text:Track' not in bare.presentation_prompt and 'film.grade' not in bare.presentation_prompt
    assert '<performance:Track' in bare.presentation_prompt
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
    assert 'text.kinetic' in scaled.presentation_prompt and 'style={title-style} during="program"' in scaled.presentation_prompt
    colored = plan(edit(card_motion=100), {**quiet, 'effects': {**quiet['effects'], 'color': True, 'kinetic': False}})
    assert 'contrast: 1.352' in colored.presentation_prompt and 'text.kinetic' not in colored.presentation_prompt

def test_hypit_page_uses_that_prompt_percentage():
    from backend.hypit_picture import _presentation_page, presentation_layers
    planned = plan(edit(presentation_share=10))
    beats = [beat.model_dump() for beat in planned.presentation]
    layers = presentation_layers(beats, 'en', 20 * 30)
    page = _presentation_page(320, 240, '20.000', 600, layers, planned.presentation_prompt)
    assert 'data-hypit-prompt="' in page
    assert 'render:Video' not in page and '<?svml' not in page and 'Many business' not in page
    assert 'data-hypit-source-fps="30/1"' in page and 'data-hypit-source-rate="1/1"' in page
    assert 'rotateY' not in page and 'hf-window' in page
    boxes = [tuple(map(float, item)) for item in __import__('re').findall(r'left:([\d.]+)%;top:([\d.]+)%;right:auto;bottom:auto;width:([\d.]+)%', ''.join(layers))]
    assert boxes and all(left >= 4 and top >= 6 and left + width <= 96 for left, top, width in boxes)
    spans = [(int(a), int(b)) for a, b in __import__('re').findall(r'<aside[^>]*data-hypit-start-frame="(\d+)" data-hypit-end-frame="(\d+)"', page)]
    assert sum(b - a for a, b in spans) / 30 == pytest.approx(2, abs=0.05)

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

def test_scan_endpoint_places_graphics_without_saving(client):
    pid = create(client).json()['id']
    seed_plan(pid)
    url = f'/api/studio/projects/{pid}/manual'
    body = {'revision': 1, 'edit': edit(presentation_share=20, clips=[{'start': 0, 'end': 10}], captions=[
        {'start': 1, 'end': 3, 'original': 'Привет', 'en': 'Hello', 'zh': '你好'},
    ]).model_dump()}
    scanned = client.post(url + '/presentation', json=body)
    assert scanned.status_code == 200
    beats = scanned.json()['edit']['presentation']
    assert sum(beat['end'] - beat['start'] for beat in beats) == pytest.approx(2, abs=0.02)
    assert client.get(url).json()['saved'] is False
    missing = edit(presentation_share=20, clips=[{'start': 0, 'end': 10, 'text': ''}], captions=[]).model_dump()
    assert client.post(url + '/presentation', json={'revision': 1, 'edit': missing}).status_code == 422
    saved = client.put(url, json={'revision': 1, 'edit': body['edit']})
    assert saved.status_code == 200
    assert saved.json()['edit']['presentation'][0]['title']['ru'] == 'Привет'

def test_languages_follow_voiceover_then_project(tmp_path):
    assert shown_language('zh', 'ru') == 'ru'
    assert shown_language('zh', None) == 'zh'
    assert shown_language('en') == 'en'
    planned = plan(edit(presentation_share=50, clips=[{'start': 0, 'end': 4}], captions=[
        {'start': 0.4, 'end': 1.6, 'original': 'Окно', 'en': 'Window', 'zh': '窗口'},
        {'start': 2.0, 'end': 3.2, 'original': 'Карточка', 'en': 'Card', 'zh': '卡片'},
    ]))
    script = tmp_path / 'presentation.ass'
    write_presentation(script, [beat.model_dump() for beat in planned.presentation], 'zh', 320, 240)
    text = script.read_text()
    assert '卡片' in text and '\\fry' in text and '\\frx' in text and '\\t(' in text
    assert 'Card' not in text
    ru = tmp_path / 'ru.ass'
    write_presentation(ru, [beat.model_dump() for beat in planned.presentation], 'ru', 320, 240)
    russian = ru.read_text()
    assert 'Карточка' in russian and 'Style: Ru,Noto Sans' in russian

@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg required')
@pytest.mark.skipif(
    not (Path(os.environ.get('HYPIT_ROOT') or '/opt/hypit') / 'node_modules' / 'tsx' / 'dist' / 'cli.mjs').is_file(),
    reason='Hypit capture required',
)
def test_windows_are_burned_in_the_requested_language(tmp_path):
    src = tmp_path / 'source.mp4'
    ffmpeg('-f', 'lavfi', '-i', 'color=red:s=320x240:d=4:r=30', '-c:v', 'libx264', src)
    analysis = Analysis(summary=T, strongest_moment=T, audience=T, scores=[{'category': 'clarity', 'value': 50, 'reason': T}],
                        scenes=[{'start': 0, 'end': 4, 'title': T, 'observation': T, 'role': 'context'}], transcript=[], recommendations=[], uncertainties=[])
    planned = plan(edit(presentation_share=50, clips=[{'start': 0, 'end': 4}], captions=[
        {'start': 0.4, 'end': 1.6, 'original': 'Окно', 'en': 'Window', 'zh': '窗口'},
        {'start': 2.0, 'end': 3.2, 'original': 'Карточка', 'en': 'Card', 'zh': '卡片'},
    ]))
    result = render(src, tmp_path, probe(src), analysis, [], 'en', 'original', manual=planned.model_dump(), presentation_language='zh')
    page = (tmp_path / 'hypit-presentation' / 'index.html').read_text()
    assert '卡片' in page and 'data-hypit-source-fps="30/1"' in page
    assert 'Card' not in page
    assert abs(result['metadata']['duration'] - 4) < 0.2
    import subprocess
    beat = planned.presentation[0]
    mid = (beat.start + beat.end) / 2
    # Sample the middle of the fitted window, not the old anchor that sat outside the frame.
    box = __import__('re').search(r'left:([\d.]+)%;top:([\d.]+)%;right:auto;bottom:auto;width:([\d.]+)%', page)
    left, top, width = (float(item) for item in box.groups())
    x, y = int(320 * (left + width / 2) / 100), min(232, int(240 * top / 100) + 20)
    def pixel(t):
        frame = int(round(t * 30))
        return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(tmp_path / 'result.mp4'),
                                         '-vf', f'select=eq(n\\,{frame}),crop=8:8:{x}:{y},scale=1:1',
                                         '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
    covered = pixel(mid)
    assert covered[0] < 180
    quiet = tmp_path / 'quiet.ass'
    write_presentation(quiet, [], 'ru', 320, 240)
    assert 'Dialogue' not in quiet.read_text()

def _speech():
    return [{'start': 1, 'end': 3, 'original': 'Привет', 'en': 'Hello', 'zh': '你好'}]

def test_saved_percent_queues_a_render_only_when_every_scene_is_approved(client):
    from backend.db import connect
    pid = create(client).json()['id']
    seed_plan(pid)
    url = f'/api/studio/projects/{pid}/manual'
    approved = edit(card_motion=40, presentation_share=0, clips=[{'start': 0, 'end': 10, 'approved': True}], captions=_speech()).model_dump()
    saved = client.put(url, json={'revision': 1, 'edit': approved})
    assert saved.status_code == 200
    assert 'end="4.000s"' in saved.json()['edit']['presentation_prompt']
    revision = saved.json()['revision']
    assert client.post(url + '/render', json={'revision': revision}).status_code == 200
    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND kind='studio_render'", (pid,)).fetchone()[0] == 1
    other = create(client).json()['id']
    seed_plan(other)
    held = edit(card_motion=80, presentation_share=0, clips=[
        {'start': 0, 'end': 5, 'approved': True},
        {'start': 5, 'end': 10, 'approved': False},
    ], captions=_speech()).model_dump()
    stored = client.put(f'/api/studio/projects/{other}/manual', json={'revision': 1, 'edit': held})
    assert stored.status_code == 200
    assert 'during="program"' in stored.json()['edit']['presentation_prompt']
    refused = client.post(f'/api/studio/projects/{other}/manual/render', json={'revision': stored.json()['revision']})
    assert refused.status_code == 422 and refused.json()['detail'] == 'approve_shots_first'
    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND kind='studio_render'", (other,)).fetchone()[0] == 0

def test_effect_board_scales_the_stored_prompt_without_a_new_revision(client):
    import json
    from backend.db import connect
    pid = create(client).json()['id']
    seed_plan(pid)
    saved = client.put(f'/api/studio/projects/{pid}/manual', json={'revision': 1, 'edit': edit(card_motion=100, presentation_share=0).model_dump()})
    assert saved.status_code == 200
    revision = saved.json()['revision']
    effects = {key: False for key in ('blur', 'glow', 'shadow', 'color', 'speed', 'stabilize', 'kinetic', 'progress', 'split', 'screen')}
    effects['color'] = True
    board = client.put(f'/api/studio/projects/{pid}/effect-board', json={'name': 'punch', 'amount': 1.6, 'effects': effects})
    assert board.status_code == 200
    assert client.get(f'/api/studio/projects/{pid}').json()['revision'] == revision
    with connect() as db:
        stored = json.loads(db.execute('SELECT config FROM studio_manual WHERE project_id=?', (pid,)).fetchone()[0])
    assert 'contrast: 1.352' in stored['presentation_prompt']
    assert 'film.vignette' not in stored['presentation_prompt']
