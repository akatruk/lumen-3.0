import json, time
import pytest
from fastapi.testclient import TestClient
from backend.app import app, limits
from backend.auth import current_user
from backend.config import settings
from backend.db import connect, project
from backend import studio
from backend.style_match import build
from backend.tests.test_studio import create, plan

T = {'en': 'A measured change', 'zh': '调整'}

def shot(**overrides):
    row = dict(start=0, end=2, observation={'en': 'SECRET REFERENCE LINE', 'zh': '参考原文'}, visual_type={'en': 'presenter', 'zh': '主讲'}, narrative_role={'en': 'hook', 'zh': '开场'}, motion={'en': 'punch in with motion tracking and a color grade', 'zh': '推近'}, transition={'en': 'fade', 'zh': '淡入'}, subtitle_emphasis={'en': 'Highlight the price', 'zh': '强调价格'}, music={'en': 'trending audio', 'zh': '热门音乐'}, emotion={'en': 'calm', 'zh': '平静'}, information_density={'en': 'chart of the price', 'zh': '价格图表'}, reusable_method={'en': 'zoom on the speaker', 'zh': '推近说话人'})
    row.update(overrides)
    return row

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    limits.clear()
    app.dependency_overrides[current_user] = lambda: {'id': 'u', 'email': 'test@example.com'}
    with TestClient(app) as c:
        with connect() as db:
            db.execute('INSERT INTO users VALUES(?,?,?,?)', ('u', 'test@example.com', 'disabled', time.time()))
            db.execute('INSERT INTO users VALUES(?,?,?,?)', ('v', 'other@example.com', 'disabled', time.time()))
            ref = dict(aweme_id='1234567890123456789', title='Reference', author='Author', share_url='https://www.douyin.com/video/1234567890123456789', duration=20)
            db.execute('INSERT INTO douyin_results VALUES(?,?,?,?)', ('a' * 32, 'u', json.dumps(ref), time.time()))
        monkeypatch.setattr(studio.media, 'probe', lambda _: dict(duration=40, width=320, height=568, has_audio=False, size=16))
        yield c
    app.dependency_overrides.clear()

def dna():
    second = shot(start=2, end=4, motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, subtitle_emphasis={'en': 'none', 'zh': '无'}, music={'en': '', 'zh': ''}, information_density={'en': 'low', 'zh': '低'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'})
    return [dict(reference_id='1234567890123456789', duration=20, analysis={'summary': T, 'shots': [shot(), second]})]

def analyze(pid, monkeypatch):
    with connect() as db:
        db.execute('UPDATE studio_projects SET dna=? WHERE project_id=?', (json.dumps(dna()), pid))
    monkeypatch.setattr(studio.media, 'prepare', lambda *args: None)
    monkeypatch.setattr(studio.ai, 'json_call', lambda *args, **kwargs: plan())
    studio.analyze(project(pid))

def test_build_uses_supported_effects_and_skips_the_rest():
    edit, report = build(dna()[0]['analysis']['shots'], 40, [], False)
    blob = json.dumps(edit)
    assert 'SECRET REFERENCE LINE' not in blob
    assert 'Highlight the price' not in blob
    assert 'trending audio' not in blob
    assert edit['clips'][0]['zoom'] == 1.2 and edit['clips'][0]['transition'] == 'fade'
    assert edit['clips'][1]['zoom'] == 1 and edit['clips'][1]['transition'] == 'cut'
    assert abs(sum(c['end'] - c['start'] for c in edit['clips']) - 40) < 0.05
    gaps = {g['id']: g['essential'] for g in report['gaps']}
    assert gaps['motion_tracking'] is False
    assert gaps['color_grade'] is False
    assert gaps['number_card'] is True
    assert gaps['reference_music'] is False
    assert gaps['captions_need_speech'] is True
    assert report['scores']['color_treatment'] == 35
    assert report['scores']['effect_similarity'] == 100
    assert edit['clips'][0]['enhance'] is True and edit['clips'][0]['y'] == 0.4
    assert report['note'] == 'owned_only'

def test_owned_facts_become_cards_and_reference_words_stay_out():
    shots = dna()[0]['analysis']['shots']
    edit, report = build(shots, 40, [{'start': 0, 'end': 4, 'original': 'The visa takes 120 days', 'en': 'The visa takes 120 days', 'zh': '签证需要120天'}], False, script='Price 120000 and deposit 30000')
    blob = json.dumps(edit)
    assert 'SECRET REFERENCE LINE' not in blob
    assert 'Highlight the price' not in blob
    card = edit['clips'][0]['card']
    assert card['kind'] == 'bar_chart'
    assert card['title']['en'] == 'Price' and card['primary']['en'] == '120000'
    assert {item['value'] for item in card['items']} == {120000, 30000, 120}
    assert all(gap['id'] != 'number_card' for gap in report['gaps'])
    assert '120' in edit['captions'][0]['emphasis_en']
    assert edit['captions'][0]['emphasis_zh'] == ['120']
    assert edit['color'] == 'yellow' and edit['font_size'] == 'large'
    assert 'cards' in report['applied'] and 'emphasis' in report['applied'] and 'enhance' in report['applied']

def test_safe_removes_shorten_the_cut_without_slicing_speech():
    shots = [shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})]
    edit, report = build(shots, 40, [], False, recommendations=[{'action': 'remove', 'start': 5, 'end': 30}])
    assert sum(c['end'] - c['start'] for c in edit['clips']) < 20
    assert 'trimmed' in report['applied']
    spoken = [{'start': 0, 'end': 40, 'original': 'Keep every word', 'en': 'Keep every word', 'zh': '保留'}]
    full, _report = build(shots, 40, spoken, False, recommendations=[{'action': 'remove', 'start': 5, 'end': 30}])
    assert abs(sum(c['end'] - c['start'] for c in full['clips']) - 40) < 0.05

def test_pan_and_owned_cutaway_follow_the_reference_instruction():
    moving = shot(motion={'en': 'pan left', 'zh': '左移'}, transition={'en': 'cut', 'zh': '切'}, visual_type={'en': 'b-roll cutaway', 'zh': '空镜'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    edit, report = build([moving], 40, [], False)
    assert edit['clips'][0]['x'] == 0.62 and edit['clips'][0]['x_end'] == 0.38
    assert edit['clips'][0]['cutaway']['source_start'] >= edit['clips'][0]['end'] - 0.01 or edit['clips'][0]['cutaway']['source_start'] == 0
    assert 'cutaway' in report['applied'] and 'framing' in report['applied']
    from backend.timeline import motion_filter
    assert 'eq=' in motion_filter(edit['clips'][0], 1080, 1920, 3)
    assert 'eq=' not in motion_filter({'zoom': 1, 'x': 0.5, 'y': 0.5}, 1080, 1920, 3)

def test_default_analysis_does_not_auto_render(client, monkeypatch):
    pid = create(client).json()['id']
    analyze(pid, monkeypatch)
    assert project(pid)['status'] == 'ready'
    assert studio.state(pid)['context']['style_match'] is False
    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND kind='studio_render'", (pid,)).fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND kind='creative_plan'", (pid,)).fetchone()[0] == 1

def test_style_match_renders_the_owned_timeline_and_keeps_the_plan(client, monkeypatch):
    pid = create(client, style_match=True).json()['id']
    analyze(pid, monkeypatch)
    state = studio.state(pid)
    assert state['plan']['recommendations']
    assert state['context']['style_report']['note'] == 'owned_only'
    with connect() as db:
        payload = json.loads(db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='studio_render'", (pid,)).fetchone()[0])
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND kind='creative_plan'", (pid,)).fetchone()[0] == 1
    assert payload['decisions'] == [] and payload['quality_review'] is False
    assert payload['manual']['clips'][0]['zoom'] == 1.2
    assert 'SECRET REFERENCE LINE' not in json.dumps(payload['manual'])
    assert project(pid)['status'] == 'queued'

def test_section_regenerate_changes_one_clip(client, monkeypatch):
    pid = create(client, style_match=True).json()['id']
    analyze(pid, monkeypatch)
    with connect() as db:
        config = json.loads(db.execute('SELECT config FROM studio_manual WHERE project_id=?', (pid,)).fetchone()[0])
        before = [(c['start'], c['end']) for c in config['clips']]
        config['clips'][0]['zoom'] = 1
        config['clips'][0]['zoom_end'] = None
        config['clips'][0]['motion_seconds'] = None
        db.execute('UPDATE studio_manual SET config=? WHERE project_id=?', (json.dumps(config), pid))
        db.execute("UPDATE jobs SET status='complete' WHERE project_id=?", (pid,))
    response = client.post(f'/api/studio/projects/{pid}/style-match/sections/0/regenerate')
    assert response.status_code == 200
    with connect() as db:
        config = json.loads(db.execute('SELECT config FROM studio_manual WHERE project_id=?', (pid,)).fetchone()[0])
    assert config['clips'][0]['zoom'] == 1.2
    assert [(c['start'], c['end']) for c in config['clips']] == before

def test_approve_records_the_cut_without_another_render(client, monkeypatch):
    pid = create(client, style_match=True).json()['id']
    analyze(pid, monkeypatch)
    with connect() as db:
        db.execute("UPDATE jobs SET status='complete' WHERE project_id=?", (pid,))
        before = db.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND kind='studio_render'", (pid,)).fetchone()[0]
    assert client.post(f'/api/studio/projects/{pid}/style-match/approve').status_code == 200
    assert studio.state(pid)['context']['style_match_status'] == 'approved'
    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND kind='studio_render'", (pid,)).fetchone()[0] == before
    app.dependency_overrides[current_user] = lambda: {'id': 'v', 'email': 'other@example.com'}
    assert client.post(f'/api/studio/projects/{pid}/style-match/approve').status_code == 404

def test_measured_shots_keep_short_beats_fast_and_match_color():
    grade = {'brightness': 0.02, 'contrast': 1.05, 'saturation': 1.08, 'gamma': 1, 'rs': 0.01, 'gs': 0, 'bs': -0.01}
    measured = {'shots': [{'start': 0, 'end': 0.4, 'motion': {'en': 'fast punch in', 'zh': '快推'}, 'transition': {'en': 'cut', 'zh': '切'}}, {'start': 0.4, 'end': 2.4, 'motion': {'en': 'blur and glow with shadows', 'zh': '模糊'}, 'transition': {'en': 'fade', 'zh': '淡入'}}], 'flat': True, 'grade': grade, 'silences': [{'start': 30, 'end': 36}]}
    edit, report = build([shot()], 40, [], False, measured=measured)
    assert edit['clips'][0]['speed'] == 1.35
    assert edit['clips'][1]['blur'] == 2 and edit['clips'][1]['glow'] and edit['clips'][1]['shadow']
    assert edit['clips'][0]['grade']['brightness'] == 0.02
    assert edit['clips'][0]['enhance'] is False
    assert 'speed' in report['applied'] and 'grade' in report['applied'] and 'blur' in report['applied']
    assert abs(sum(c['end'] - c['start'] for c in edit['clips']) - 40) < 1

def test_detail_track_mask_and_unusable_spans_change_the_cut():
    row = shot(motion={'en': 'follow the subject with a mask and slow motion', 'zh': '跟踪'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    edit, report = build([row], 40, [], False, measured={'track': {'x0': 0.22, 'x1': 0.78}, 'unusable': [{'start': 8, 'end': 14}], 'chroma': 'green'})
    assert edit['clips'][0]['track'] is True and edit['clips'][0]['x'] == 0.22 and edit['clips'][0]['x_end'] == 0.78
    assert edit['clips'][0]['mask'] is False and edit['clips'][0]['speed'] == 0.75
    gaps = {gap['id'] for gap in report['gaps']}
    assert 'motion_tracking' not in gaps and 'mask' in gaps
    window = shot(motion={'en': 'follow the subject with a mask and slow motion', 'zh': '跟踪'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'zoom': 1, 'x': 0.5, 'y': 0.5, 'split': False, 'graphic': False, 'mask': True, 'lower': False})
    masked, masked_report = build([window], 40, [], False)
    assert masked['clips'][0]['mask'] is True and masked['clips'][0]['split'] is False
    assert 'mask' not in {gap['id'] for gap in masked_report['gaps']}
    assert sum(c['end'] - c['start'] for c in edit['clips']) < 39
    keyed, keyed_report = build([shot(motion={'en': 'replace the background', 'zh': '换背景'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'})], 40, [], False, measured={'chroma': 'green'})
    assert keyed['clips'][0]['cutout'] is True and keyed['clips'][0]['plate'] == '1A1F1C'
    assert 'background_replacement' not in {gap['id'] for gap in keyed_report['gaps']}

def test_named_wipe_uses_the_existing_wipe_filter():
    row = shot(transition={'en': 'wipe', 'zh': '划'})
    edit, _report = build([row], 40, [], False)
    assert edit['clips'][0]['transition'] == 'wipe'

def test_measured_vertical_composition_frames_the_subject():
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'zoom': 1.35, 'x': 0.5, 'y': 0.78, 'y_end': 0.22, 'split': False, 'graphic': False})
    edit, report = build([row], 40, [], False)
    assert edit['clips'][0]['y'] == 0.78 and edit['clips'][0]['y_end'] == 0.22 and edit['clips'][0]['zoom'] == 1.35
    assert report['scores']['effect_similarity'] == 100

def test_picture_measurement_sets_zoom_framing_and_a_graphic():
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'zoom': 1.15, 'zoom_end': 1.35, 'x': 0.22, 'x_end': 0.78, 'split': False, 'graphic': True})
    edit, report = build([row], 40, [], False, script='Price 120000 and deposit 30000')
    clip = edit['clips'][0]
    assert clip['zoom'] == 1.15 and clip['zoom_end'] == 1.35
    assert clip['x'] == 0.22 and clip['x_end'] == 0.78
    assert clip['transition'] == 'fade' and clip['card']['kind'] == 'bar_chart'
    assert clip['graphic'] is True and clip['bars'][0] == 1
    assert 'framing' in report['applied'] and 'cards' in report['applied'] and 'illustration' in report['applied']

def test_measured_vignette_adds_a_shadow_without_the_word():
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'zoom': 1, 'zoom_end': None, 'x': 0.5, 'x_end': None, 'split': False, 'graphic': False, 'fade': False, 'vignette': True})
    edit, report = build([row], 40, [], False)
    assert edit['clips'][0]['shadow'] is True
    assert 'shadow' in report['applied']

def test_screenshot_and_illustration_use_owned_material():
    screen = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'zoom': 1, 'screen': True, 'graphic': False, 'split': False})
    shown, shown_report = build([screen], 40, [], False)
    assert shown['clips'][0]['screen'] is not None and shown['clips'][0]['still'] is None
    assert 'screen' in shown_report['applied']
    drawn = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'illustration', 'zh': '插画'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    edit, report = build([drawn], 40, [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False)
    assert edit['clips'][0]['diagram'] >= 1 and edit['clips'][0]['text'] == 'Visa'
    assert 'diagram' in report['applied'] and 'SECRET' not in edit['clips'][0]['text']

def test_graphic_without_figures_holds_another_owned_frame():
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'zoom': 1, 'zoom_end': None, 'x': 0.5, 'x_end': None, 'split': False, 'graphic': True, 'fade': False})
    edit, report = build([row], 40, [], False)
    assert edit['clips'][0]['graphic'] is False and edit['clips'][0]['card'] is None
    assert edit['clips'][0]['still'] is not None
    assert 'still' in report['applied'] and 'illustration' not in report['applied']

def test_words_alone_do_not_split_mask_or_overlay():
    named = shot(motion={'en': 'split screen with an icon and a mask', 'zh': '分屏'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    spoken = [{'start': 0, 'end': 4, 'original': 'Visa days', 'en': 'Visa days', 'zh': '签证天数'}]
    edit, report = build([named], 40, spoken, False)
    assert edit['clips'][0]['split'] is False and edit['clips'][0]['mask'] is False and edit['clips'][0]['lower'] is False
    assert {'split_screen', 'mask'} <= {gap['id'] for gap in report['gaps']}
    measured = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'zoom': 1, 'x': 0.5, 'y': 0.5, 'split': True, 'graphic': False, 'mask': False, 'lower': False})
    split_edit, split_report = build([measured], 40, spoken, False)
    assert split_edit['clips'][0]['split'] is True and split_edit['clips'][0]['panel'] is not None and split_edit['clips'][0]['lower'] is False
    assert 'split' in split_report['applied']
    band = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'zoom': 1, 'x': 0.5, 'y': 0.5, 'split': False, 'graphic': False, 'mask': False, 'lower': True})
    lower_edit, lower_report = build([band], 40, spoken, False)
    assert lower_edit['clips'][0]['lower'] is True and lower_edit['clips'][0]['icon'] is True and lower_edit['clips'][0]['text'].startswith('Visa')
    assert 'lower' in lower_report['applied']

def test_kinetic_caption_adds_a_second_owned_word():
    row = shot(motion={'en': 'kinetic title', 'zh': '动效标题'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': 'SECRET REFERENCE LINE', 'zh': '参考'})
    spoken = [{'start': 0, 'end': 4, 'original': 'Visa paperwork', 'en': 'Visa paperwork', 'zh': '签证材料'}]
    edit, _report = build([row], 40, spoken, False)
    assert edit['clips'][0]['kinetic'] is True
    assert edit['clips'][0]['text'].split() == ['paperwork', 'Visa']
    assert 'SECRET' not in edit['clips'][0]['text']
    one = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False)[0]
    assert one['clips'][0]['text'] == 'Visa'

def test_measured_strength_replaces_the_fixed_blur_glow_and_shadow():
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'zoom': 1, 'x': 0.5, 'y': 0.5, 'split': False, 'graphic': False, 'blur': 4.5, 'glow': 1.1, 'shade': 1.2})
    edit, report = build([row], 40, [], False)
    clip = edit['clips'][0]
    assert clip['blur'] == 4.5 and clip['glow_amount'] == 1.1 and clip['shade'] == 1.2
    assert clip['glow'] is True and clip['shadow'] is True
    assert {'blur', 'glow', 'shadow'} <= set(report['applied'])

def test_a_measured_pace_changes_speed_inside_the_shot():
    words = shot(motion={'en': 'speed ramp', 'zh': '变速'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    named, named_report = build([words], 40, [], False)
    assert named['clips'][0]['speed'] == 1 and named['clips'][0]['speed_end'] is None
    assert 'speed_ramp' in {gap['id'] for gap in named_report['gaps']}
    measured = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'zoom': 1, 'x': 0.5, 'y': 0.5, 'split': False, 'graphic': False, 'speed': 1, 'speed_end': 1.45})
    edit, report = build([measured], 40, [], False)
    assert edit['clips'][0]['speed'] == 1 and edit['clips'][0]['speed_end'] == 1.45
    assert 'speed' in report['applied']

def test_icon_plate_follows_the_owned_percent(tmp_path):
    import subprocess
    from types import SimpleNamespace
    from backend import media
    from backend.manual import Edit
    source = tmp_path / 'src.mp4'
    folder = tmp_path / 'plate'
    folder.mkdir()
    subprocess.check_call(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=0x203028:s=180x240:r=30:d=1.2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rendered = media.render(source, folder, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.2, 'lower': True, 'icon': True, 'mark': 0.8, 'text': ''}]).model_dump())
    assert abs(rendered['metadata']['duration'] - 1.2) < 0.2

    def luma(x):
        proc = subprocess.run(['ffmpeg', '-v', 'info', '-ss', '0.4', '-i', str(folder / 'result.mp4'), '-vf', f'crop=8:8:{x}:210,signalstats,metadata=print', '-frames:v', '1', '-f', 'null', '-'], capture_output=True, text=True)
        return float(next(line for line in proc.stderr.splitlines() if 'YAVG=' in line).rsplit('YAVG=', 1)[-1])

    assert luma(100) > luma(168) + 40

def test_owned_percent_sets_the_progress_and_the_icon_plate():
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': '', 'zh': ''})
    band, _report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Saved 40 percent', 'en': 'Saved 40 percent', 'zh': '节省'}], False, measured={'layout': {'split': False, 'bar': False, 'lower': True, 'shake': False}})
    assert band['clips'][0]['icon'] is True and band['clips'][0]['mark'] == 0.4 and band['clips'][0]['progress'] == 0
    bar, _report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Complete 80%', 'en': 'Complete 80%', 'zh': '完成'}], False, measured={'layout': {'split': False, 'bar': True, 'lower': False, 'shake': False}})
    assert {clip['progress'] for clip in bar['clips']} == {0.8}
    days, _report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Visa takes 120 days', 'en': 'Visa takes 120 days', 'zh': '签证'}], False, measured={'layout': {'split': False, 'bar': True, 'lower': False, 'shake': False}})
    assert days['clips'][-1]['progress'] == 1

def test_measured_layout_adds_split_progress_and_stabilization():
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    edit, report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Visa days', 'en': 'Visa days', 'zh': '签证天数'}], False, measured={'layout': {'split': True, 'bar': True, 'lower': True, 'shake': True}})
    assert all(c['split'] and c['stabilize'] for c in edit['clips'])
    assert edit['clips'][-1]['progress'] == 1
    assert edit['clips'][0]['text'].startswith('Visa')
    assert 'progress' in report['applied'] and 'split' in report['applied'] and 'stabilize' in report['applied'] and 'panel' in report['applied']
    assert edit['clips'][0]['panel'] is not None and edit['clips'][0]['lower'] is False
    band, band_report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Visa days', 'en': 'Visa days', 'zh': '签证天数'}], False, measured={'layout': {'split': False, 'bar': False, 'lower': True, 'shake': False}})
    assert band['clips'][0]['lower'] is True and band['clips'][0]['icon'] is True and band['clips'][0]['text'].startswith('Visa')
    assert 'lower' in band_report['applied'] and 'icon' in band_report['applied']

def test_reference_file_replaces_douyin_results(client):
    response = client.post('/api/studio/projects', data={'config': json.dumps(dict(request_id='c' * 32, references=[], title='Owned project', script='My original script', creator=dict(topic='travel', audience='Families', tone='Calm', rules='No invented claims'), owned_rights_confirmed=True, language='zh', budget=5, style_match=True))}, files={'file': ('owned.mp4', b'owned-source-only', 'video/mp4'), 'reference': ('ref.mp4', b'reference-pixels', 'video/mp4')})
    assert response.status_code == 201
    pid = response.json()['id']
    state = studio.state(pid)
    assert state['context']['references'] == []
    assert state['context']['style_match'] is True and state['context']['reference_file'] is True
    assert (settings.data_dir / pid / 'reference_source').read_bytes() == b'reference-pixels'
    assert (settings.data_dir / pid / 'source').read_bytes() == b'owned-source-only'

def test_held_reference_upload_is_copied_into_the_project(client):
    payload = b'reference-held'
    begin = client.post('/api/studio/uploads', json={'size': len(payload), 'token': 'd' * 32})
    assert begin.status_code == 201
    ident = begin.json()['id']
    assert client.put(f'/api/studio/uploads/{ident}?offset=0', content=payload).status_code == 200
    response = client.post('/api/studio/projects', data={'config': json.dumps(dict(request_id='e' * 32, references=[], reference_upload_id=ident, title='Owned project', script='My original script', creator=dict(topic='travel', audience='Families', tone='Calm', rules='No invented claims'), owned_rights_confirmed=True, language='zh', budget=5))}, files={'file': ('owned.mp4', b'owned-source-only', 'video/mp4')})
    assert response.status_code == 201
    pid = response.json()['id']
    assert (settings.data_dir / pid / 'reference_source').read_bytes() == payload
    assert studio.state(pid)['context']['style_match'] is True
    with connect() as db:
        assert db.execute('SELECT 1 FROM studio_uploads WHERE id=?', (ident,)).fetchone() is None

def test_style_match_stays_off_until_requested(client):
    pid = create(client).json()['id']
    with connect() as db:
        db.execute("UPDATE jobs SET status='complete' WHERE project_id=?", (pid,))
    assert client.post(f'/api/studio/projects/{pid}/style-match/regenerate').status_code == 422
