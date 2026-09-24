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
    assert report['scores']['color_treatment'] == 0
    assert report['scores']['effect_similarity'] == 100
    assert edit['clips'][0]['enhance'] is False and edit['clips'][0]['grade'] is None and edit['clips'][0]['y'] == 0.4
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
    assert 'cards' in report['applied'] and 'emphasis' in report['applied']
    assert 'enhance' not in report['applied']

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
    bare = motion_filter(edit['clips'][0], 1080, 1920, 3)
    assert 'eq=' not in bare and 'exposure=' not in bare
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

def test_approve_renders_the_saved_edit_and_keeps_the_selected_delivery(client, monkeypatch):
    import uuid
    from backend.final_output import current, path as delivery_path
    from backend.music import Music
    from backend.worker import run_once
    bare = create(client, style_match=True).json()['id']
    analyze(bare, monkeypatch)
    with connect() as db:
        db.execute("UPDATE jobs SET status='complete' WHERE project_id=?", (bare,))
        db.execute('DELETE FROM studio_manual WHERE project_id=?', (bare,))
    missing = client.post(f'/api/studio/projects/{bare}/style-match/approve')
    assert missing.status_code == 422 and missing.json()['detail'] == 'save_manual_first'
    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND kind='studio_render' AND status='queued'", (bare,)).fetchone()[0] == 0
    assert (settings.data_dir / bare / 'source').read_bytes() == b'owned-source-only'
    pid = create(client, style_match=True).json()['id']
    analyze(pid, monkeypatch)
    aid, voice, render_id = 'e' * 32, 'd' * 32, 'c' * 32
    with connect() as db:
        db.execute("UPDATE jobs SET status='complete' WHERE project_id=?", (pid,))
        config = json.loads(db.execute('SELECT config FROM studio_manual WHERE project_id=?', (pid,)).fetchone()[0])
        config['clips'][0]['zoom'] = 1.05
        config['clips'][0]['zoom_end'] = None
        config['music'] = Music(asset_id=aid).model_dump()
        db.execute('UPDATE studio_manual SET config=? WHERE project_id=?', (json.dumps(config), pid))
        db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)', (aid, pid, uuid.uuid4().hex, 'Test track', 'Synthetic', json.dumps({'kind': 'music', 'duration': 60}), 0))
        master = {'render_id': render_id, 'timeline': [[0, 40]], 'metadata': {'duration': 40, 'width': 320, 'height': 568, 'has_audio': False}}
        db.execute('UPDATE projects SET result=? WHERE id=?', (json.dumps(master), pid))
        db.execute('INSERT INTO dubbing_versions(id,project_id,request_id,master_id,language,voice,kind,status,snapshot,created) VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (voice, pid, uuid.uuid4().hex, render_id, 'ru', 'ru-male', 'video', 'ready', json.dumps({'master': master}), time.time()))
        db.execute('INSERT INTO project_final_outputs(project_id,master_id,version_id,updated) VALUES(?,?,?,?)', (pid, render_id, voice, time.time()))
    folder = settings.data_dir / pid
    (folder / 'renders' / render_id).mkdir(parents=True)
    (folder / 'renders' / render_id / 'result.mp4').write_bytes(b'finished-cut')
    (folder / 'dubbing' / voice).mkdir(parents=True)
    (folder / 'dubbing' / voice / 'video.mp4').write_bytes(b'chosen-voice')
    (folder / 'reference_source').write_bytes(b'REFERENCE-PIXELS-NOT-A-SOURCE')
    assert client.post(f'/api/studio/projects/{pid}/style-match/approve').status_code == 200
    assert studio.state(pid)['context']['style_match_status'] == 'approved'
    with connect() as db:
        payload = json.loads(db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='studio_render' AND status='queued'", (pid,)).fetchone()[0])
    assert payload['quality_review'] is False and payload['decisions'] == []
    assert payload['manual']['music']['asset_id'] == aid and payload['manual']['clips'][0]['zoom'] == 1.05
    assert payload['voice_id'] == voice
    assert 'reference_source' not in json.dumps(payload) and 'REFERENCE-PIXELS' not in json.dumps(payload)
    assert client.post(f'/api/studio/projects/{pid}/style-match/regenerate').status_code == 409
    assert client.post(f'/api/studio/projects/{pid}/style-match/sections/0/regenerate').status_code == 409
    assert client.post(f'/api/studio/projects/{pid}/style-match/approve').status_code == 409
    with connect() as db:
        db.execute("UPDATE jobs SET status='complete' WHERE project_id=? AND status='queued'", (pid,))
        assert db.execute('SELECT version_id FROM project_final_outputs WHERE project_id=?', (pid,)).fetchone()['version_id'] == voice
    assert client.post(f'/api/studio/projects/{pid}/style-match/approve').status_code == 200
    with connect() as db:
        second = json.loads(db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='studio_render' AND status='queued'", (pid,)).fetchone()[0])
        assert db.execute('SELECT version_id FROM project_final_outputs WHERE project_id=?', (pid,)).fetchone()['version_id'] == voice
    assert second['quality_review'] is False and second['manual']['music']['asset_id'] == aid and second['voice_id'] == voice
    assert second['manual']['clips'][0]['zoom'] == 1.05 and 'reference_source' not in json.dumps(second)
    from backend import media, render_audio
    monkeypatch.setattr('backend.style_match.score_output', lambda *_a, **_k: None)
    def prepare(_pid, _voice, render_folder, _timeline):
        (render_folder / 'voice-clean.wav').write_bytes(b'voice')
        (render_folder / 'voice-subtitles.vtt').write_text('WEBVTT\n')
        return render_folder / 'voice-clean.wav'
    def render_picture(source, render_folder, *_args, **kwargs):
        assert source.read_bytes() == b'owned-source-only'
        assert kwargs['manual']['clips'][0]['zoom'] == 1.05
        assert kwargs['manual']['music']['asset_id'] == aid
        assert kwargs.get('voice_audio')
        (render_folder / 'result.mp4').write_bytes(b'new-picture-with-voice-and-music')
        (render_folder / 'music-free.mp4').write_bytes(b'music-free-picture')
        clips = [c for c in kwargs['manual']['clips'] if c.get('approved', True)]
        return {'music': kwargs['manual']['music'], 'metadata': {'duration': 40, 'has_audio': True, 'width': 320, 'height': 568}, 'timeline': [(c['start'], c['end']) for c in clips], 'applied': [], 'generated_clips': 0}
    monkeypatch.setattr(render_audio, 'prepare', prepare)
    monkeypatch.setattr(media, 'render', render_picture)
    assert run_once()
    rendered = project(pid)
    assert rendered['result']['render_id'] != render_id
    assert (folder / 'renders' / render_id / 'result.mp4').read_bytes() == b'finished-cut'
    with connect() as db:
        selected = current(db, pid, rendered['result']['render_id'])
    assert selected['delivery'] == 'mix' and selected['voice'] == 'ru-male'
    assert json.loads(selected['music'])['asset_id'] == aid
    played = delivery_path(pid, selected).read_bytes()
    downloaded = client.get(f'/api/projects/{pid}/media/result').content
    assert played == downloaded == b'new-picture-with-voice-and-music'
    assert downloaded != (folder / 'source').read_bytes()
    assert downloaded != (folder / 'reference_source').read_bytes()
    with connect() as db:
        db.execute("UPDATE jobs SET status='complete' WHERE project_id=? AND status='queued'", (pid,))
    assert client.post(f'/api/studio/projects/{pid}/style-match/approve').status_code == 200
    def fail_render(source, render_folder, *_args, **_kwargs):
        (render_folder / 'result.mp4').write_bytes(source.read_bytes())
        raise ValueError('media_processing_failed')
    monkeypatch.setattr(media, 'render', fail_render)
    assert run_once()
    failed = project(pid)
    assert failed['result']['render_id'] == rendered['result']['render_id']
    assert failed['status'] == 'failed'
    with connect() as db:
        kept = current(db, pid, failed['result']['render_id'])
    played = delivery_path(pid, kept).read_bytes()
    downloaded = client.get(f'/api/projects/{pid}/media/result').content
    assert played == downloaded == b'new-picture-with-voice-and-music'
    assert downloaded != (folder / 'source').read_bytes()
    assert (folder / 'renders' / render_id / 'result.mp4').read_bytes() == b'finished-cut'
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

def test_color_moves_only_when_the_reference_was_measured():
    from backend.timeline import motion_filter
    plain, report = build(dna()[0]['analysis']['shots'], 40, [], False)
    clip = plain['clips'][0]
    assert clip['enhance'] is False and clip['grade'] is None and clip['exposure'] == 0
    bare = motion_filter(clip, 1080, 1920, 3)
    assert 'eq=' not in bare and 'exposure=' not in bare
    assert 'enhance' not in report['applied']
    grade = {'brightness': 0.02, 'contrast': 1.05, 'saturation': 1.08, 'gamma': 1, 'rs': 0.01, 'gs': 0, 'bs': -0.01}
    graded, graded_report = build([shot()], 40, [], False, measured={'grade': grade, 'exposure': 0.08})
    moved = graded['clips'][0]
    assert moved['enhance'] is False and moved['exposure'] == 0.08
    assert moved['grade']['brightness'] == 0.02 and moved['grade']['contrast'] == 1.05 and moved['grade']['rs'] == 0.01
    chain = motion_filter(moved, 1080, 1920, 3)
    assert 'contrast=1.0500' in chain and 'colorbalance=rs=0.0100' in chain and 'exposure=0.080' in chain
    assert 'eq=contrast=1.04:brightness=0.02:saturation=1.06:gamma=1.02' not in chain
    assert 'grade' in graded_report['applied'] and 'exposure' in graded_report['applied'] and 'enhance' not in graded_report['applied']
    small = motion_filter(moved, 480, 848, 3)
    assert 'colorbalance=rs=0.0100' in small and 'brightness=0.0200' in small
    assert 'contrast=1.0125' in small and 'saturation=1.0200' in small
    assert 'contrast=1.0500' not in small and 'saturation=1.0800' not in small
    assert 'eq=contrast=1.04' not in small
    held, _report = build([shot()], 40, [], False, measured={'grade': grade, 'exposure': 0})
    assert held['clips'][0]['enhance'] is False and held['clips'][0]['exposure'] == 0
    held_chain = motion_filter(held['clips'][0], 1080, 1920, 3)
    assert 'exposure=' not in held_chain and 'contrast=1.0500' in held_chain
    quiet = motion_filter({'zoom': 1, 'x': 0.5, 'y': 0.5, 'enhance': True}, 480, 640, 2)
    assert 'eq=' not in quiet and 'exposure=' not in quiet

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
    spoken = [{'start': 0, 'end': 4, 'original': 'Visa days stay', 'en': 'Visa days stay', 'zh': '签证'}]
    kept, _report = build([row], 40, spoken, False, measured={'unusable': [{'start': 1, 'end': 3}]})
    assert abs(sum(c['end'] - c['start'] for c in kept['clips']) - 40) < 1
    opened, _report = build([row], 40, [], False, measured={'highlight': {'start': 30, 'end': 34}})
    assert opened['clips'][0]['start'] >= 28
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

def test_measured_bezel_is_kept_and_a_named_screen_stays_a_tenth():
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': 'SECRET REFERENCE LINE', 'zh': '参考'}, picture={'zoom': 1, 'screen': True, 'bezel': 0.18, 'graphic': False, 'split': False})
    edit, _report = build([row], 40, [], False)
    assert edit['clips'][0]['screen'] is not None and edit['clips'][0]['bezel'] == 0.18
    assert 'SECRET' not in json.dumps(edit['clips'][0])
    named = shot(motion={'en': 'screenshot', 'zh': '截图'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    words, _report = build([named], 40, [], False)
    assert words['clips'][0]['screen'] is not None and words['clips'][0]['bezel'] == 0.1

def test_measured_tiles_replace_the_word_count():
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'illustration', 'zh': '插画'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': 'SECRET REFERENCE LINE', 'zh': '参考'}, picture={'zoom': 1, 'graphic': False, 'split': False, 'screen': False, 'tiles': 4})
    edit, _report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False)
    assert edit['clips'][0]['diagram'] == 4 and edit['clips'][0]['text'] == 'Visa'
    assert 'SECRET' not in edit['clips'][0]['text']
    words = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'illustration', 'zh': '插画'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    spoken, _report = build([words], 40, [{'start': 0, 'end': 4, 'original': 'Visa days', 'en': 'Visa days', 'zh': '签证'}], False)
    assert spoken['clips'][0]['diagram'] == 2

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

def test_kinetic_words_follow_the_reference_rhythm(tmp_path):
    from backend import media
    from backend.media import ass_time, write_kinetic
    from backend.style_vision import kinetic_appearances
    span = 4
    reference = tmp_path / 'flashes.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', f'color=0x101010:s=180x240:r=30:d={span}', '-f', 'lavfi', '-i', f'color=white:s=180x48:r=30:d={span}', '-filter_complex', "[0:v][1:v]overlay=0:16:enable='between(t,1.0,1.35)+between(t,3.0,3.35)'", '-c:v', 'libx264', '-pix_fmt', 'yuv420p', reference)
    hits = kinetic_appearances(reference, 0, span)
    assert len(hits) == 2
    assert abs(hits[0] - 0.25) < 0.1 and abs(hits[1] - 0.75) < 0.1
    triple = tmp_path / 'three.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', f'color=0x101010:s=180x240:r=30:d={span}', '-f', 'lavfi', '-i', f'color=white:s=180x48:r=30:d={span}', '-filter_complex', "[0:v][1:v]overlay=0:16:enable='between(t,0.8,1.15)+between(t,2.0,2.35)+between(t,3.2,3.55)'", '-c:v', 'libx264', '-pix_fmt', 'yuv420p', triple)
    assert len(kinetic_appearances(triple, 0, span)) == 3
    held = tmp_path / 'hold.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=0x101010:s=180x240:r=30:d=2', '-f', 'lavfi', '-i', 'color=white:s=180x48:r=30:d=2', '-filter_complex', '[0:v][1:v]overlay=0:16', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', held)
    assert len(kinetic_appearances(held, 0, 2)) <= 1
    picture = {'zoom': 1, 'x': 0.5, 'y': 0.5, 'split': False, 'graphic': False, 'kinetic_at': hits}
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': 'SECRET REFERENCE LINE', 'zh': '参考原文'}, picture=picture)
    owned = 16
    spoken = [{'start': 0, 'end': owned, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}]
    edit, _report = build([row], owned, spoken, False, measured={'shots': [{'start': 0, 'end': span, 'picture': picture}]})
    clip = edit['clips'][0]
    length = clip['end'] - clip['start']
    assert length > span + 1
    assert clip['kinetic'] is True and clip['text'] == 'Visa'
    assert len(clip['kinetic_at']) == 2
    assert abs(clip['kinetic_at'][0] - hits[0]) < 0.02 and abs(clip['kinetic_at'][1] - hits[1]) < 0.02
    assert abs(clip['kinetic_at'][0] * length - hits[0] * span) > 1
    blob = json.dumps(edit)
    assert 'SECRET REFERENCE LINE' not in blob and '参考原文' not in blob
    quiet, _report = build([row], owned, [], False, measured={'shots': [{'start': 0, 'end': span, 'picture': picture}]})
    assert quiet['clips'][0]['text'] == '' and quiet['clips'][0]['kinetic'] is False and quiet['clips'][0]['kinetic_at'] == []
    ass = tmp_path / 'words.ass'
    write_kinetic(ass, clip['text'], length, 180, 240, at=clip['kinetic_at'])
    lines = [line for line in ass.read_text().splitlines() if line.startswith('Dialogue:')]
    assert len(lines) == 2 and all(line.endswith('Visa') for line in lines)
    assert 'SECRET' not in ass.read_text()
    assert lines[0].split(',')[1] == ass_time(clip['kinetic_at'][0] * length)
    assert lines[1].split(',')[1] == ass_time(clip['kinetic_at'][1] * length)
    if media.ass_available():
        source = tmp_path / 'owned.mp4'
        media.ffmpeg('-f', 'lavfi', '-i', f'color=0x224466:s=180x240:r=30:d={owned}', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', source)
        folder = tmp_path / 'render'
        folder.mkdir()
        from types import SimpleNamespace
        rendered = media.render(source, folder, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=edit)
        assert abs(rendered['metadata']['duration'] - owned) < 0.6
        burned = (folder / 'title-0.ass').read_text()
        assert burned.count('Visa') >= 2 and 'SECRET' not in burned

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

def test_a_measured_entrance_times_the_effect_and_words_do_not():
    late = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'zoom': 1, 'x': 0.5, 'y': 0.5, 'split': False, 'graphic': False, 'mask': False, 'lower': True, 'hold': 0.5, 'blur': 0})
    edit, _report = build([late], 40, [{'start': 0, 'end': 4, 'original': 'Visa days', 'en': 'Visa days', 'zh': '签证'}], False)
    assert edit['clips'][0]['lower'] is True and edit['clips'][0]['effect_at'] == 0.5
    words = shot(motion={'en': 'soft blur', 'zh': '虚化'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    blurred, _report = build([words], 40, [], False)
    assert blurred['clips'][0]['blur'] == 2 and blurred['clips'][0]['effect_at'] == 0

def test_owned_percent_sets_the_progress_and_the_icon_plate():
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': '', 'zh': ''})
    band, _report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Saved 40 percent', 'en': 'Saved 40 percent', 'zh': '节省'}], False, measured={'layout': {'split': False, 'bar': False, 'lower': True, 'shake': False}})
    assert band['clips'][0]['icon'] is True and band['clips'][0]['mark'] == 0.4 and band['clips'][0]['progress'] == 0
    bar, _report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Complete 80%', 'en': 'Complete 80%', 'zh': '完成'}], False, measured={'layout': {'split': False, 'bar': True, 'lower': False, 'shake': False}})
    assert {clip['progress'] for clip in bar['clips']} == {0.8}
    days, _report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Visa takes 120 days', 'en': 'Visa takes 120 days', 'zh': '签证'}], False, measured={'layout': {'split': False, 'bar': True, 'lower': False, 'shake': False}})
    assert days['clips'][-1]['progress'] == 1

def test_measured_shake_sets_the_deshake_window_and_words_use_the_default():
    words = shot(motion={'en': 'shaky camera', 'zh': '晃动'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    spoken, _report = build([words], 40, [], False)
    assert spoken['clips'][0]['stabilize'] is True and spoken['clips'][0]['shake_rx'] == 16
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    strong, _report = build([row], 40, [], False, measured={'layout': {'split': False, 'bar': False, 'lower': False, 'shake': True, 'shake_rx': 32}})
    assert strong['clips'][0]['stabilize'] is True and strong['clips'][0]['shake_rx'] == 32
    calm, _report = build([row], 40, [], False, measured={'layout': {'split': False, 'bar': False, 'lower': False, 'shake': False, 'shake_rx': 0}})
    assert calm['clips'][0]['stabilize'] is False and calm['clips'][0]['shake_rx'] == 0

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

def test_effect_board_changes_the_look_and_leaves_an_empty_board_alone():
    from backend.style_match import apply_effect_board
    clip = {'start': 1.2, 'blur': 4, 'glow': False, 'glow_amount': 0, 'shadow': True, 'shade': 0.8, 'speed': 1, 'speed_end': None, 'exposure': 0, 'enhance': False, 'grade': None, 'stabilize': False, 'kinetic': False, 'text': 'Visa', 'progress': 0, 'split': True, 'panel': 3, 'screen': 2}
    board = {'name': 'punch', 'amount': 1, 'effects': {'blur': False, 'glow': True, 'shadow': False, 'color': True, 'speed': True, 'stabilize': True, 'kinetic': True, 'progress': True, 'split': False, 'screen': False}}
    changed = apply_effect_board({'clips': [dict(clip)]}, board)['clips'][0]
    assert changed['blur'] == 0 and changed['shadow'] is False and changed['shade'] == 0
    assert changed['glow'] is True and changed['glow_amount'] == 0.55
    assert changed['exposure'] == 0.18 and changed['enhance'] is True
    assert changed['speed'] == 1.15 and changed['stabilize'] is True and changed['kinetic'] is True
    assert changed['progress'] == 0.7 and changed['split'] is False and changed['panel'] is None and changed['screen'] is None
    assert apply_effect_board({'clips': [dict(clip)]}, None)['clips'][0]['blur'] == 4

def test_downloaded_reference_is_measured_when_no_file_was_uploaded(tmp_path):
    from backend.style_match import reference_video
    from backend.timeline import motion_filter
    folder = tmp_path / 'project'
    nested = folder / 'references' / '7640040044933238056'
    nested.mkdir(parents=True)
    (nested / 'source').write_bytes(b'reference-download')
    found = reference_video(folder, {'references': [{'aweme_id': '7640040044933238056'}]})
    assert found == nested / 'source'
    uploaded = folder / 'reference_source'
    uploaded.write_bytes(b'uploaded')
    assert reference_video(folder, {'references': [{'aweme_id': '7640040044933238056'}]}) == uploaded
    assert reference_video(tmp_path / 'empty', None) is None
    moving = motion_filter({'zoom': 1, 'zoom_end': 1.2, 'x': 0.5, 'y': 0.5}, 480, 848, 3)
    assert 'scale=iw*2:ih*2:flags=lanczos' in moving
    still = motion_filter({'zoom': 1.2, 'x': 0.5, 'y': 0.5}, 480, 848, 3)
    assert 'scale=iw*2' not in still

def test_style_match_stays_off_until_requested(client):
    pid = create(client).json()['id']
    with connect() as db:
        db.execute("UPDATE jobs SET status='complete' WHERE project_id=?", (pid,))
    assert client.post(f'/api/studio/projects/{pid}/style-match/regenerate').status_code == 422
    refused = client.post(f'/api/studio/projects/{pid}/style-match/approve')
    assert refused.status_code == 422 and refused.json()['detail'] == 'style_match_off'

def test_owned_keyword_is_emphasized_at_the_reference_flash(tmp_path):
    from backend import media
    from backend.media import ass_available, emphasize_caption, write_subtitles
    from backend.schemas import Caption
    from backend.style_vision import highlight_moments
    flash = tmp_path / 'flash.mp4'
    media.ffmpeg(
        '-f', 'lavfi', '-i', 'color=0x303030:s=180x240:r=30:d=0.9',
        '-f', 'lavfi', '-i', 'color=0x303030:s=180x240:r=30:d=0.2',
        '-f', 'lavfi', '-i', 'color=white:s=48x48:r=30:d=0.2',
        '-f', 'lavfi', '-i', 'color=0x303030:s=180x240:r=30:d=0.9',
        '-filter_complex', '[1:v][2:v]overlay=66:96[flash];[0:v][flash][3:v]concat=n=3:v=1:a=0',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', flash,
    )
    fractions = highlight_moments(flash, 0, 2)
    assert fractions == [0.5]
    flat = tmp_path / 'flat.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=0x303030:s=180x240:r=30:d=2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', flat)
    assert highlight_moments(flat, 0, 2) == []
    row = shot(
        start=0, end=2,
        motion={'en': 'static hold', 'zh': '固定'},
        transition={'en': 'cut', 'zh': '切'},
        reusable_method={'en': 'hold the frame', 'zh': '固定机位'},
        information_density={'en': 'low', 'zh': '低'},
        subtitle_emphasis={'en': '', 'zh': ''},
        music={'en': '', 'zh': ''},
        observation={'en': 'SECRET REFERENCE LINE Highlight the price', 'zh': '参考原文'},
        picture={'zoom': 1, 'x': 0.5, 'y': 0.5, 'split': False, 'graphic': False, 'highlights': fractions},
    )
    spoken = [
        {'start': 0, 'end': 0.7, 'original': 'Deposit forms', 'en': 'Deposit forms', 'zh': '材料'},
        {'start': 0.7, 'end': 1.4, 'original': 'Pay with Visa', 'en': 'Pay with Visa', 'zh': '签证'},
        {'start': 1.4, 'end': 2, 'original': 'Final papers', 'en': 'Final papers', 'zh': '文件'},
    ]
    edit, report = build([row], 2, spoken, False)
    assert report['note'] == 'owned_only'
    assert edit['captions'][1]['emphasis_en'] == ['Visa']
    assert edit['captions'][0]['emphasis_en'] == [] and edit['captions'][2]['emphasis_en'] == []
    blob = json.dumps(edit)
    assert 'SECRET REFERENCE LINE' not in blob and 'Highlight the price' not in blob
    assert all('SECRET' not in term and 'Highlight' not in term and 'price' not in term.lower() for cap in edit['captions'] for term in cap['emphasis_en'] + cap['emphasis_zh'])
    tagged = emphasize_caption('Pay with Visa', edit['captions'][1]['emphasis_en'], 'en', '&H00FFFFFF')
    assert '{\\c&H0000FFFF}Visa' in tagged and 'Highlight the price' not in tagged
    ass = tmp_path / 'captions.ass'
    write_subtitles(ass, [Caption.model_validate(edit['captions'][1])], [(0, 2)], 'en', 180, 240, {'color': 'white'})
    caption_file = ass.read_text()
    assert 'Visa' in caption_file and '{\\c' in caption_file
    assert 'Highlight the price' not in caption_file and 'SECRET REFERENCE LINE' not in caption_file
    quiet = [{'start': 0, 'end': 2, 'original': 'to be', 'en': 'to be', 'zh': '好'}]
    empty, empty_report = build([row], 2, quiet, False)
    assert empty['captions'][0]['emphasis_en'] == [] and empty['captions'][0]['emphasis_zh'] == []
    dumped = json.dumps(empty)
    assert 'Visa' not in dumped and 'Highlight the price' not in dumped and 'SECRET REFERENCE LINE' not in dumped
    assert empty_report['note'] == 'owned_only' and 'emphasis' not in empty_report['applied']
    if ass_available():
        source = tmp_path / 'owned.mp4'
        media.ffmpeg('-f', 'lavfi', '-i', 'color=0x203028:s=180x240:r=30:d=2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', source)
        folder = tmp_path / 'render'
        folder.mkdir()
        media.render(source, folder, media.probe(source), type('A', (), {'transcript': []})(), [], 'en', 'original', manual=edit)
        burned = (folder / 'captions.ass').read_text()
        assert 'Visa' in burned and 'Highlight the price' not in burned and 'SECRET REFERENCE LINE' not in burned

def test_effect_similarity_waits_until_frames_are_compared():
    edit, report = build(dna()[0]['analysis']['shots'], 40, [], False)
    assert edit['clips']
    assert report['compared'] is False
    assert report['comparison_note'] == 'Frames have not been compared yet.'
    assert report.get('measured_effect_similarity') is None
    assert report['scores']['effect_similarity'] == report['effect_similarity_rule']
    if report['scores']['effect_similarity'] == 100:
        assert report['compared'] is False
    from backend.style_match import blend_effect_similarity
    stored = blend_effect_similarity({
        'scores': {'shot_structure': 100, 'visual_pacing': 100, 'effect_similarity': 100, 'motion_graphic_style': 100, 'color_treatment': 100, 'production_quality': 100, 'overall': 100},
        'effect_similarity_rule': 100,
        'compared': False,
        'comparison_note': 'Frames have not been compared yet.',
    }, 40)
    assert stored['scores']['effect_similarity'] == 70
    assert stored['scores']['overall'] == 95.0
    assert stored['compared'] is True
    assert stored['measured_effect_similarity'] == 40
    assert stored['comparison_note'] == ''
    missed = blend_effect_similarity({'scores': {'effect_similarity': 40}, 'effect_similarity_rule': 40, 'compared': False}, None)
    assert missed['compared'] is False and missed['scores']['effect_similarity'] == 40
    assert missed['comparison_note'] == 'Frames have not been compared yet.'
    assert 'measured_effect_similarity' not in missed
    row = shot(motion={'en': 'follow the subject and replace the background', 'zh': '跟踪换背景'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    tracked, tracked_report = build([row], 40, [], False)
    assert tracked['clips']
    gaps = {gap['id']: gap['essential'] for gap in tracked_report['gaps']}
    assert gaps['motion_tracking'] is False
    assert gaps['background_replacement'] is False

def test_owned_number_lands_on_the_reference_card_moment(tmp_path):
    from types import SimpleNamespace
    from backend import media
    from backend.media import ass_available
    from backend.style_vision import annotate_pictures, card_moment
    reference = tmp_path / 'reference.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=5', '-f', 'lavfi', '-i', 'color=white:s=60x200:r=30:d=5', '-filter_complex', "[0:v][1:v]overlay=60:20:enable='between(t,1.5,3.5)'", '-c:v', 'libx264', '-pix_fmt', 'yuv420p', reference)
    plain = tmp_path / 'plain.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=0x446688:s=180x240:r=30:d=2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', plain)
    assert card_moment(plain, 0, 2) is None
    marked = [{'start': 0, 'end': 5}]
    annotate_pictures(reference, marked)
    moment = marked[0]['picture']['card']
    assert marked[0]['picture']['graphic'] is False
    assert 0.30 <= moment['in'] <= moment['out'] <= 0.70
    row = shot(start=0, end=10, observation={'en': 'SECRET REFERENCE LINE 999', 'zh': '参考'}, motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'zoom': 1, 'x': 0.5, 'y': 0.5, 'split': False, 'graphic': False, 'card': {'in': moment['in'], 'out': moment['out']}})
    edit, report = build([row], 10, [], False, script='Price 120000')
    clip = edit['clips'][0]
    length = clip['end'] - clip['start']
    card = clip['card']
    blob = json.dumps(edit)
    assert card['kind'] == 'number' and card['primary']['en'] == '120000' and card['title']['en'] == 'Price'
    assert 0.30 <= card['start'] / length <= 0.70
    assert card['end'] < length - 0.4 and card['end'] - card['start'] >= 0.5
    assert abs(card['start'] - moment['in'] * 5) > 0.5
    assert 'SECRET REFERENCE LINE' not in blob and '999' not in blob
    assert all(gap['id'] != 'number_card' for gap in report['gaps'])
    empty, missing = build([row], 10, [], False, script='')
    assert empty['clips'][0]['card'] is None
    assert any(gap['id'] == 'number_card' and gap['essential'] is True for gap in missing['gaps'])
    assert '999' not in json.dumps(empty) and 'SECRET REFERENCE LINE' not in json.dumps(empty)
    if ass_available():
        source = tmp_path / 'owned.mp4'
        media.ffmpeg('-f', 'lavfi', '-i', 'color=0x224466:s=180x240:r=30:d=10', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', source)
        assert source.resolve() != reference.resolve()
        folder = tmp_path / 'render'
        folder.mkdir()
        media.render(source, folder, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=edit)
        burned = (folder / 'card-0.ass').read_text()
        assert '120000' in burned and '999' not in burned and 'SECRET' not in burned

def test_timed_owned_progress_bar(tmp_path, monkeypatch):
    import subprocess
    from types import SimpleNamespace
    from backend import media
    from backend.manual import Edit
    from backend.style_vision import reference_layout
    reference = tmp_path / 'reference.mp4'
    media.ffmpeg(
        '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=2',
        '-vf', "drawbox=x=0:y=ih-8:w=iw:h=8:color=white:t=fill:enable='between(t\\,0.5\\,1.5)'",
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', reference,
    )
    layout = reference_layout(reference)
    assert layout['bar'] is True and layout['split'] is False and layout['lower'] is False
    assert abs(layout['bar_in'] - 0.25) < 0.12 and abs(layout['bar_out'] - 0.75) < 0.12
    flat = tmp_path / 'flat.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=0x222222:s=180x240:r=30:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', flat)
    assert reference_layout(flat)['bar'] is False
    callout = tmp_path / 'callout.mp4'
    media.ffmpeg(
        '-f', 'lavfi', '-i', 'color=0x222222:s=180x240:r=30:d=1',
        '-vf', 'drawbox=x=0:y=192:w=180:h=48:color=0xF4F1EA:t=fill',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', callout,
    )
    assert reference_layout(callout)['bar'] is False
    row = shot(start=0, end=2, observation={'en': '', 'zh': ''}, motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    percent, _report = build([row], 2, [], False, script='Visa 40%', measured={'layout': layout})
    clip = percent['clips'][0]
    assert abs(clip['progress'] - 0.4) < 0.05
    assert abs(clip['progress_at'] - 0.25) < 0.12 and abs(clip['progress_end'] - 0.75) < 0.12
    assert clip['progress_play'] is False and clip['effect_at'] == 0
    plain, _plain_report = build([row], 2, [], False, script='Visa opens', measured={'layout': layout})
    bare = plain['clips'][0]
    assert bare['progress'] > 0.02 and bare['progress_play'] is True
    assert abs(bare['progress_at'] - layout['bar_in']) < 0.02 and abs(bare['progress_end'] - layout['bar_out']) < 0.02
    dumped = json.dumps(plain)
    assert '99' not in dumped
    assert all(item['progress'] != 0.99 for item in plain['clips'])
    assert bare['progress'] == 1
    owned = tmp_path / 'owned.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=0x224466:s=180x240:r=30:d=2.4', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', owned)
    seen = []
    original = media.ffmpeg
    def spy(*args, **kwargs):
        seen.append([str(arg) for arg in args])
        return original(*args, **kwargs)
    monkeypatch.setattr(media, 'ffmpeg', spy)
    folder = tmp_path / 'bar-render'
    folder.mkdir()
    drawn = dict(clip)
    drawn.update(text='', kinetic=False, kinetic_at=[], card=None, graphic=False, lower=False, icon=False, split=False, mask=False, cutout=False, screen=None, still=None, diagram=0)
    media.render(owned, folder, media.probe(owned), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[drawn]).model_dump())
    joined = '\n'.join(' '.join(call) for call in seen)
    assert str(reference) not in joined and str(owned) in joined and 'drawbox' in joined and 'between' in joined
    assert not list(folder.glob('*.ass'))
    result = folder / 'result.mp4'
    height = media.probe(result)['height']
    span = drawn['end'] - drawn['start']
    start_t = drawn['progress_at'] * span
    end_t = drawn['progress_end'] * span
    before = max(0.04, start_t - 0.18)
    inside = (start_t + end_t) / 2
    after = min(span - 0.06, end_t + 0.18)

    def luma(t, y):
        proc = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(result), '-ss', f'{t:.3f}', '-vf', f'crop=12:6:8:{y},signalstats,metadata=print', '-frames:v', '1', '-f', 'null', '-'], capture_output=True, text=True)
        values = [float(line.rsplit('YAVG=', 1)[-1]) for line in proc.stderr.splitlines() if 'signalstats.YAVG=' in line]
        return values[-1]

    bar_y = max(0, height - 10)
    picture_y = max(0, height // 2)
    before_bar, before_picture = luma(before, bar_y), luma(before, picture_y)
    inside_bar, inside_picture = luma(inside, bar_y), luma(inside, picture_y)
    after_bar, after_picture = luma(after, bar_y), luma(after, picture_y)
    assert inside_bar > inside_picture + 40
    assert before_bar < before_picture + 20 and after_bar < after_picture + 20
    assert inside_picture < 160

def test_owned_screen_uses_the_reference_fraction(tmp_path, monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace
    from backend import media
    from backend.style_vision import picture_of
    reference = tmp_path / 'reference-screen.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=0x446688:s=180x240:r=30:d=1.4', '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=1.2', '-f', 'lavfi', '-i', 'color=0x446688:s=180x240:r=30:d=1.4', '-filter_complex', "[1:v]drawbox=x=16:y=16:w=148:h=208:color=0xD8D2C4:t=fill[mid];[0:v][mid][2:v]concat=n=3:v=1:a=0", '-c:v', 'libx264', '-pix_fmt', 'yuv420p', reference)
    owned = tmp_path / 'owned.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=0x224466:s=180x240:r=30:d=10', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', owned)
    owned_meta = media.probe(owned)
    reference_meta = media.probe(reference)
    assert abs(owned_meta['duration'] - 10) < 0.25
    measured = picture_of(reference, 0, reference_meta['duration'])
    assert measured['screen'] is True
    assert abs(measured['fraction'] - 0.5) < 0.08
    quiet = dict(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': 'SECRET REFERENCE LINE', 'zh': '参考'})
    row = shot(start=0, end=owned_meta['duration'], picture=measured, **quiet)
    edit, report = build([row], owned_meta['duration'], [], False, source=owned)
    stamp = edit['clips'][0]['screen']
    assert isinstance(stamp, float) and not isinstance(stamp, bool)
    assert abs(stamp - owned_meta['duration'] * measured['fraction']) < 0.05
    assert abs(stamp - 5) < 0.5
    assert edit['clips'][0]['still'] is None
    blob = json.dumps(edit)
    assert 'SECRET REFERENCE LINE' not in blob
    assert str(reference) not in blob and reference.name not in blob
    gap = next(item for item in report['gaps'] if item['id'] == 'owned_screen_frame')
    assert gap['essential'] is False and 'owned frame' in gap['note']
    named = shot(start=0, end=owned_meta['duration'], picture={'zoom': 1, 'screen': True, 'fraction': 0.5, 'graphic': False, 'split': False}, **quiet)
    exact, exact_report = build([named], owned_meta['duration'], [], False, source=owned)
    owned_stamp = exact['clips'][0]['screen']
    assert isinstance(owned_stamp, float)
    assert abs(owned_stamp - 0.5 * owned_meta['duration']) < 0.05
    assert abs(owned_stamp - 5) < 0.3
    assert any(item['id'] == 'owned_screen_frame' and item['essential'] is False for item in exact_report['gaps'])
    assert 'SECRET REFERENCE LINE' not in json.dumps(exact)
    framed = tmp_path / 'owned-bezel.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=10', '-vf', 'drawbox=x=16:y=16:w=148:h=208:color=0xD8D2C4:t=fill', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', framed)
    framed_meta = media.probe(framed)
    seen, seen_report = build([shot(start=0, end=framed_meta['duration'], picture={'zoom': 1, 'screen': True, 'fraction': 0.5, 'graphic': False, 'split': False}, **quiet)], framed_meta['duration'], [], False, source=framed)
    assert abs(seen['clips'][0]['screen'] - 0.5 * framed_meta['duration']) < 0.05
    assert all(item['id'] != 'owned_screen_frame' for item in seen_report['gaps'])
    calls = []
    real = media.ffmpeg
    def spy(*args, **kwargs):
        calls.append(tuple(args))
        return real(*args, **kwargs)
    monkeypatch.setattr(media, 'ffmpeg', spy)
    folder = tmp_path / 'out'
    folder.mkdir()
    media.render(owned, folder, owned_meta, SimpleNamespace(transcript=[]), [], 'en', 'original', manual=exact)
    inputs = [part for args in calls for index, part in enumerate(args) if index and args[index - 1] == '-i']
    assert inputs and Path(inputs[0]).resolve() == owned.resolve()
    assert all(Path(str(part)).resolve() != reference.resolve() for part in inputs)
    assert str(reference) not in ' '.join(str(part) for args in calls for part in args)
    assert owned_stamp in [part for args in calls for part in args]
    assert reference.name not in {path.name for path in folder.rglob('*')}

def test_timed_owned_callout_uses_the_reference_fraction(tmp_path, monkeypatch):
    import subprocess
    from types import SimpleNamespace
    from backend import media
    from backend.manual import Edit
    from backend.style_vision import annotate_pictures, callout_at
    reference = tmp_path / 'reference-callout.mp4'
    media.ffmpeg('-y', '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=2', '-f', 'lavfi', '-i', 'color=0xFFE14A:s=30x40:r=30:d=2', '-filter_complex', "[0:v][1:v]overlay=7:92:enable='gte(t\\,1.2)'", '-c:v', 'libx264', '-pix_fmt', 'yuv420p', reference)
    flat = tmp_path / 'flat-callout.mp4'
    media.ffmpeg('-y', '-f', 'lavfi', '-i', 'color=0x446688:s=180x240:r=30:d=2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', flat)
    card = tmp_path / 'full-card.mp4'
    media.ffmpeg('-y', '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=2', '-f', 'lavfi', '-i', 'color=white:s=180x240:r=30:d=2', '-filter_complex', "[0:v][1:v]overlay=enable='gte(t\\,1.2)'", '-c:v', 'libx264', '-pix_fmt', 'yuv420p', card)
    assert callout_at(flat, 0, 2) == 0
    assert callout_at(card, 0, 2) == 0
    quiet = dict(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': 'SECRET REFERENCE LINE', 'zh': '参考'})
    row = shot(start=0, end=2, **quiet)
    annotate_pictures(reference, [row])
    fraction = row['picture']['callout']
    assert 0.45 <= fraction <= 0.8
    spoken = [{'start': 0, 'end': 2, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}]
    edit, _report = build([row], 2, spoken, False, script='')
    clip = edit['clips'][0]
    assert clip['text'] == 'Visa' or clip['text'].startswith('● Visa') or clip['text'].startswith('▮ Visa')
    assert clip['icon'] is True and clip['lower'] is True
    assert clip['effect_at'] == fraction
    assert clip['effect_at'] < 1
    blob = json.dumps(edit)
    assert 'SECRET REFERENCE LINE' not in blob and str(reference) not in blob
    empty, _empty_report = build([row], 2, [], False, script='')
    assert empty['clips'][0]['text'] == '' and empty['clips'][0]['icon'] is False
    assert 'SECRET REFERENCE LINE' not in json.dumps(empty)
    owned = tmp_path / 'owned-source.mp4'
    media.ffmpeg('-y', '-f', 'lavfi', '-i', 'color=0x203028:s=180x240:r=30:d=2.2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', owned)
    calls = []
    real = media.ffmpeg
    def spy(*args, **kwargs):
        calls.append(tuple(str(part) for part in args))
        return real(*args, **kwargs)
    monkeypatch.setattr(media, 'ffmpeg', spy)
    folder = tmp_path / 'edit-render'
    folder.mkdir()
    try:
        media.render(owned, folder, media.probe(owned), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=edit)
    except RuntimeError as exc:
        if media.ass_available() or 'ass' not in str(exc):
            raise
    span = clip['end'] - clip['start']
    opened = clip['effect_at'] * span
    joined = '\n'.join(' '.join(call) for call in calls)
    assert str(reference) not in joined and reference.name not in joined
    assert str(owned) in joined and 'drawbox' in joined and '0xF4F1EA' in joined and f'{opened:.3f}' in joined
    bare = dict(clip)
    bare.update(text='', kinetic=False, kinetic_at=[], card=None, graphic=False, bars=[], lower=True, icon=True, split=False, mask=False, cutout=False, screen=None, still=None, diagram=0, art='')
    pixels = tmp_path / 'chip-render'
    pixels.mkdir()
    media.render(owned, pixels, media.probe(owned), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[bare], subtitles=False, captions=[]).model_dump())
    pixel_calls = '\n'.join(' '.join(call) for call in calls)
    assert str(reference) not in pixel_calls
    result = pixels / 'result.mp4'
    meta = media.probe(result)
    width, height = int(meta['width']), int(meta['height'])

    def colors(at):
        proc = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{at:.3f}', '-i', str(result), '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True)
        data = proc.stdout
        yellow = cream = 0
        for index in range(0, len(data) - 2, 3):
            red, green, blue = data[index], data[index + 1], data[index + 2]
            if red > 200 and green > 160 and blue < 120:
                yellow += 1
            if red > 200 and green > 190 and blue > 180:
                cream += 1
        return yellow, cream

    early_yellow, early_cream = colors(0.12)
    late_yellow, late_cream = colors(min(span - 0.08, opened + 0.4))
    assert early_yellow == 0 and late_yellow == 0
    assert late_cream > early_cream + 40
    assert width >= 16 and height >= 16

def test_reference_fraction_lands_on_the_owned_timeline():
    quiet = dict(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': 'SECRET REFERENCE LINE', 'zh': '参考'})
    picture = {'zoom': 1, 'x': 0.5, 'y': 0.5, 'split': False, 'graphic': False, 'blur': 4, 'glow': 0.8, 'hold': 0, 'event': 0.70}
    measured = {'duration': 10, 'shots': [{**quiet, 'start': 0, 'end': 4, 'picture': picture}]}
    edit, _report = build([shot(**quiet)], 10, [], False, measured=measured)
    clip = edit['clips'][0]
    span = clip['end'] - clip['start']
    landed = clip['start'] + clip['effect_at'] * span
    assert abs(landed - 7.0) < 0.05
    assert clip['blur'] == 4 and clip['glow'] is True
    assert 'SECRET REFERENCE LINE' not in json.dumps(edit)
    rows = [{**quiet, 'start': index * 0.4, 'end': (index + 1) * 0.4} for index in range(30)]
    many, _report = build([shot(**quiet)], 40, [], False, measured={'duration': 12, 'shots': rows})
    assert len(many['clips']) <= 24
    assert 'SECRET REFERENCE LINE' not in json.dumps(many)

def test_overlay_window_is_absent_outside_the_measured_span(tmp_path, monkeypatch):
    import subprocess
    from types import SimpleNamespace
    from backend import media
    from backend.manual import Clip, Edit
    from backend.style_vision import reference_layout
    from backend.visuals import CardText, VisualCard, write_card
    reference = tmp_path / 'reference-window.mp4'
    media.ffmpeg(
        '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=2',
        '-vf', "drawbox=x=0:y=ih-8:w=iw:h=8:color=white:t=fill:enable='between(t\\,0.5\\,1.5)'",
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', reference,
    )
    layout = reference_layout(reference)
    assert layout['bar'] is True
    assert layout['bar_in'] * 2 > 0.1 and layout['bar_out'] * 2 < 1.8
    assert layout['bar_in'] * 2 < 1.0 < layout['bar_out'] * 2
    quiet = dict(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': '', 'zh': ''})
    plate = shot(start=0, end=2, picture={'zoom': 1, 'x': 0.5, 'y': 0.5, 'split': False, 'graphic': False, 'mask': False, 'lower': True, 'hold': 0.25, 'release': 0.75, 'blur': 0}, **quiet)
    timed, _report = build([plate], 2, [{'start': 0, 'end': 2, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False)
    assert timed['clips'][0]['effect_at'] == 0.25 and timed['clips'][0]['effect_end'] == 0.75
    stays = shot(start=0, end=2, picture={'zoom': 1, 'x': 0.5, 'y': 0.5, 'split': False, 'graphic': False, 'mask': False, 'lower': True, 'hold': 0.5, 'blur': 0}, **quiet)
    whole, _report = build([stays], 2, [{'start': 0, 'end': 2, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False)
    assert whole['clips'][0]['effect_at'] == 0.5 and whole['clips'][0]['effect_end'] == 1
    spoken = [{'start': 0.0, 'end': 0.7, 'original': 'Hello', 'en': 'Hello', 'zh': '你好'}, {'start': 0.7, 'end': 1.4, 'original': 'Pay with Visa', 'en': 'Pay with Visa', 'zh': '签证'}, {'start': 1.4, 'end': 2.0, 'original': 'Thanks', 'en': 'Thanks', 'zh': '谢谢'}]
    flash = shot(start=0, end=2, picture={'zoom': 1, 'highlights': [0.5], 'emphasis': {'in': 0.5, 'out': 0.65}}, **quiet)
    emphasized, _report = build([flash], 2, spoken, True)
    middle = next(row for row in emphasized['captions'] if 'Visa' in row['en'])
    assert middle['start'] == 0.7 and middle['end'] == 1.4 and middle['emphasis_en']
    assert all(not row['emphasis_en'] for row in emphasized['captions'] if 'Visa' not in row['en'])
    card_row = shot(start=0, end=2, picture={'zoom': 1, 'card': {'in': 0.25, 'out': 0.75}, 'graphic': False, 'split': False}, **quiet)
    carded, _report = build([card_row], 2, [], False, script='Price 40')
    card = carded['clips'][0]['card']
    assert abs(card['start'] - 0.5) < 0.08 and abs(card['end'] - 1.5) < 0.08
    card_file = tmp_path / 'card.ass'
    write_card(card_file, card, 'en', 180, 240)
    burned = card_file.read_text()
    assert '0:00:00.50' in burned and '0:00:01.50' in burned
    owned = tmp_path / 'owned-window.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=0x203028:s=180x240:r=30:d=2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', owned)
    seen = []
    original = media.ffmpeg
    def spy(*args, **kwargs):
        seen.append([str(arg) for arg in args])
        return original(*args, **kwargs)
    monkeypatch.setattr(media, 'ffmpeg', spy)
    folder = tmp_path / 'window-render'
    folder.mkdir()
    drawn = Clip(start=0, end=2, progress=0.8, progress_at=0.25, progress_end=0.75, progress_play=False, text='').model_dump()
    media.render(owned, folder, media.probe(owned), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[drawn], subtitles=False, captions=[]).model_dump())
    joined = '\n'.join(' '.join(call) for call in seen)
    assert str(reference) not in joined and reference.name not in joined
    assert str(owned) in joined and 'drawbox' in joined and 'between' in joined
    assert not list(folder.glob('*.ass'))
    result = folder / 'result.mp4'
    meta = media.probe(result)
    assert abs(meta['duration'] - 2) <= 0.08
    height = int(meta['height'])

    def luma(t, y):
        proc = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(result), '-ss', f'{t:.3f}', '-vf', f'crop=12:6:8:{y},signalstats,metadata=print', '-frames:v', '1', '-f', 'null', '-'], capture_output=True, text=True)
        values = [float(line.rsplit('YAVG=', 1)[-1]) for line in proc.stderr.splitlines() if 'signalstats.YAVG=' in line]
        return values[-1]

    bar_y = max(0, height - 10)
    picture_y = max(0, height // 2)
    samples = {0.1: luma(0.1, bar_y), 1.0: luma(1.0, bar_y), 1.8: luma(1.8, bar_y)}
    picture = luma(1.0, picture_y)
    present = {stamp: value > picture + 40 for stamp, value in samples.items()}
    assert present == {0.1: False, 1.0: True, 1.8: False}
    words = tmp_path / 'callout-render'
    words.mkdir()
    callout = Clip(start=0, end=2, text='Visa', effect_at=0.25, effect_end=0.75, progress=0).model_dump()
    try:
        media.render(owned, words, media.probe(owned), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[callout], subtitles=False, captions=[]).model_dump())
    except RuntimeError as exc:
        if media.ass_available() or 'ass' not in str(exc):
            raise
    dialogue = (words / 'title-0.ass').read_text()
    assert '0:00:00.50' in dialogue and '0:00:01.50' in dialogue
    assert '0:00:02.00' not in dialogue
    spare = VisualCard(start=0.5, end=1.5, title=CardText(en='Note', zh='注'), primary=CardText(en='1', zh='1'), source=CardText(en='Owned', zh='自有'))
    spare_file = tmp_path / 'spare-card.ass'
    write_card(spare_file, spare.model_dump(), 'en', 180, 240)
    spare_text = spare_file.read_text()
    assert spare_text.count('0:00:00.50') >= 1 and spare_text.count('0:00:01.50') >= 1
