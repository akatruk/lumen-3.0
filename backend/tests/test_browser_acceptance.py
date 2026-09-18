"""Opt-in real HTTP/browser/worker/FFmpeg acceptance bridge.

Run only in an isolated checkout without .env. The browser driver is
frontend/tests/real-render.browser.cjs. External AI responses are deterministic;
HTTP, authentication, persistence, queueing, rendering and downloads are real.
"""
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

import pytest
import uvicorn

from backend.tests.test_render_audio import client, source_fixture, energy
from backend.config import settings
from backend.db import connect, project
from backend.app import app
from backend.auth import current_user
from backend.worker import run_once
from backend import creative_plans, media
from backend.manual import Edit, Clip
from backend.final_output import current, path

if os.getenv('LUMEN_BROWSER_ACCEPTANCE') and settings.database_url:
    raise RuntimeError('Browser acceptance requires isolated SQLite, never a configured database')


@pytest.mark.skipif(not os.getenv('LUMEN_BROWSER_ACCEPTANCE'), reason='Opt-in isolated browser acceptance')
def test_real_browser_render_lifecycle(client, monkeypatch, tmp_path):
    assert not settings.database_url, 'Never run against production PostgreSQL'
    bridge = Path(os.environ['LUMEN_BROWSER_ACCEPTANCE'])
    bridge.mkdir(parents=True, exist_ok=True)
    pid, voice, revision = source_fixture(client, monkeypatch)
    root = settings.data_dir / pid
    # A spatial pattern makes zoom/reframing visibly measurable, unlike a flat color.
    media.ffmpeg('-f', 'lavfi', '-i', 'testsrc2=s=160x240:d=8:r=30',
                 '-f', 'lavfi', '-i', 'sine=frequency=110:duration=8',
                 '-c:v', 'libx264', '-c:a', 'aac', '-f', 'mp4', root / 'source')
    media.prepare(root / 'source', root)
    from backend.tests.test_studio import plan
    initial = media.render(root / 'source', root / 'renders' / ('b' * 32), media.probe(root / 'source'),
                           plan(), [], 'en', 'original', manual=Edit(clips=[Clip(start=0, end=8)]).model_dump())
    initial.update(render_id='b' * 32, qa=None, qa_status='manual_review_required', plan_revision=revision)
    with connect() as db:
        db.execute('UPDATE projects SET title=?,language=?,result=? WHERE id=?', ('Isolated release acceptance', 'en', json.dumps(initial), pid))
        db.execute('UPDATE projects SET metadata=? WHERE id=?', (json.dumps(media.probe(root / 'source') | {'preview_ready': True}), pid))
        db.execute('UPDATE dubbing_versions SET snapshot=? WHERE id=?', (json.dumps({'master': initial}), voice))
        config = json.loads(db.execute('SELECT config FROM studio_manual WHERE project_id=?', (pid,)).fetchone()[0])
        config['clips'] = [Clip(start=0, end=8).model_dump()]
        config['captions'] = [{'start': 0, 'end': 1.5, 'original': 'QA caption', 'en': 'QA caption', 'zh': '测试'}]
        config['subtitles'] = False
        config['music'].update(gain_db=-12, fade_in=0, fade_out=0, duck=False)
        db.execute('UPDATE studio_manual SET config=? WHERE project_id=?', (json.dumps(config), pid))
    # Seed only external AI/TTS output; all downstream user actions use real HTTP.
    text = {'en': 'Acceptance fixture: trim and zoom', 'zh': '测试剪辑'}
    proposal = creative_plans.Proposal(
        recommendation_reviews=[creative_plans.RecommendationReview(recommendation_id='cut', outcome='not_applied', reason=text)],
        decisions=[creative_plans.CreativeDecision(clip_index=i, title=text, observation=text, change=text, reason=text) for i in range(2)],
        reason=text, notes=[], edit=Edit(clips=[Clip(start=4, end=8, zoom_end=1.3, motion_seconds=2), Clip(start=0, end=2)]))
    def fixture_ai(*args, **kwargs):
        if len(args) > 4 and args[4] == 'creative_plan':
            return proposal.model_copy(deep=True)
        raise ValueError('Unexpected external AI request in isolated acceptance')
    monkeypatch.setattr(creative_plans.ai, 'json_call', fixture_ai)
    monkeypatch.setattr(settings, 'google_sso_only', False)
    monkeypatch.setattr(settings, 'public_origin', os.getenv('LUMEN_ACCEPTANCE_ORIGIN', 'http://127.0.0.1:5193'))
    app.dependency_overrides.pop(current_user, None)
    token = uuid.uuid4().hex
    with connect() as db:
        db.execute('INSERT INTO sessions(token,user_id,expires) VALUES(?,?,?)',
                   (hashlib.sha256(token.encode()).hexdigest(), 'u', time.time() + 1200))
    port = int(os.getenv('LUMEN_ACCEPTANCE_PORT', '8021'))
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, log_level='warning'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 20
    while not server.started and time.monotonic() < deadline:
        time.sleep(.05)
    assert server.started
    ready = bridge / 'ready.json'
    ready.write_text(json.dumps({'pid': pid, 'token': token}))
    ready.chmod(0o600)
    try:
        deadline = time.monotonic() + 900
        while not (bridge / 'done.json').exists() and time.monotonic() < deadline:
            if not run_once():
                time.sleep(.2)
        assert (bridge / 'done.json').exists(), 'Browser did not finish'
        report = json.loads((bridge / 'done.json').read_text())
        assert report.get('passed'), report
        p = project(pid)
        assert p['result']['timeline'] == [[4, 8], [0, 2]]
        with connect() as db:
            selected = current(db, pid, p['result']['render_id'])
        assert selected['delivery'] == 'mix' and selected['language'] == 'ru'
        video = path(pid, selected)
        assert abs(media.probe(video)['duration'] - 6) < .15
        assert energy(video, .7, 880) > energy(video, .7, 110) * 50
        assert energy(video, 4.7, 440) > energy(video, 4.7, 880) * 50
        assert energy(video, .7, 220) > energy(video, .7, 110) * 10
        def frame(file, at):
            return subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', str(at), '-i', str(file),
                                            '-vf', 'scale=32:48', '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
        output_frame = frame(video, 2.7)
        source_frame = frame(root / 'source', 6.7)
        assert len(output_frame) == len(source_frame) == 32 * 48 * 3
        assert len(set(zip(output_frame[::3], output_frame[1::3], output_frame[2::3]))) > 100, 'Must use the new patterned picture, not the old flat blue dub'
        picture_difference = sum(abs(a - b) for a, b in zip(output_frame, source_frame)) / len(output_frame)
        assert picture_difference > 8, 'The rendered zoom must visibly change the corresponding source frame'
        shutil.copyfile(video, bridge / 'verified-final.mp4')
        report['media_verified'] = {'duration': 6, 'timeline': p['result']['timeline'],
                                    'voice_before_cut_hz': 880, 'voice_after_cut_hz': 440,
                                    'music_hz': 220, 'picture_difference': round(picture_difference, 2),
                                    'render_id': p['result']['render_id']}
        (bridge / 'verified.json').write_text(json.dumps(report, indent=2))
    finally:
        ready.unlink(missing_ok=True)
        server.should_exit = True
        thread.join(timeout=10)
