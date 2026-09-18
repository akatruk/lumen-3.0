import json
import uuid
from pathlib import Path

import pytest
from backend.tests.test_studio import client, create, seed_plan
from backend.auth import current_user
from backend.app import app
from backend.config import settings
from backend.db import connect, project
from backend.worker import run_once
from backend import dubbing, dubbing_audio as audio

MASTER = 'b' * 32


def setup(client, monkeypatch):
    monkeypatch.setattr(settings, 'openrouter_api_key', 'test-not-a-key')
    pid = create(client).json()['id']
    seed_plan(pid)
    transcript = [{'start': 0, 'end': 2, 'original': 'Hello there.', 'en': 'Hello there.', 'zh': '你好。'}]
    p = project(pid)
    analysis = p['analysis'] | {'transcript': transcript}
    master = {'render_id': MASTER, 'timeline': [[0, 40]], 'metadata': {'duration': 40, 'has_audio': True}}
    with connect() as db:
        db.execute('UPDATE projects SET analysis=?,result=? WHERE id=?', (json.dumps(analysis), json.dumps(master), pid))
    folder = settings.data_dir / pid / 'renders' / MASTER
    folder.mkdir(parents=True)
    (folder / 'result.mp4').write_bytes(b'original master')
    return pid


def body(**changes):
    return dict(request_id=uuid.uuid4().hex, master_id=MASTER, language='ru', voice='ru-male', kind='video', replace_audio=True) | changes


def test_owned_validation_and_stale_master(client, monkeypatch):
    pid = setup(client, monkeypatch)
    url = f'/api/studio/projects/{pid}/dubbing'
    assert client.get(url).status_code == 200
    assert client.post(url, json=body(voice='en-male')).status_code == 422
    assert client.post(url, json=body(master_id='c' * 32)).status_code == 409
    assert client.post(url, json=body(replace_audio=False)).status_code == 422
    app.dependency_overrides[current_user] = lambda: {'id': 'v'}
    assert client.get(url).status_code == 404
    assert client.post(url, json=body()).status_code == 404
    assert client.get(url + '/' + 'a' * 32 + '/files/video.mp4').status_code == 404


def test_idempotent_queue_and_snapshot(client, monkeypatch):
    pid = setup(client, monkeypatch)
    url = f'/api/studio/projects/{pid}/dubbing'
    request = body()
    first = client.post(url, json=request)
    assert first.status_code == 202
    assert client.post(url, json=request).json() == first.json()
    assert client.post(url, json=request | {'voice': 'ru-female'}).status_code == 409
    assert client.post(url, json=body()).status_code == 409
    with connect() as db:
        rows = list(db.execute("SELECT * FROM jobs WHERE project_id=? AND kind='dubbing'", (pid,)))
        row = db.execute('SELECT * FROM dubbing_versions WHERE id=?', (first.json()['id'],)).fetchone()
    assert len(rows) == 1
    assert json.loads(row['snapshot'])['master']['render_id'] == MASTER
    assert client.get(url + '/' + first.json()['id'] + '/files/video.mp4').status_code == 404


def test_job_preserves_master_and_serves_owned_output(client, monkeypatch):
    pid = setup(client, monkeypatch)
    before = project(pid)['result']
    url = f'/api/studio/projects/{pid}/dubbing'
    monkeypatch.setattr(audio, 'translate', lambda pid, phrases, language: [dict(p, text='Привет!') for p in phrases])
    monkeypatch.setattr(audio, 'synthesize', lambda text, voice, path, model: path.write_bytes(b'mp3'))
    monkeypatch.setattr(audio, 'fit_phrase', lambda source, output, seconds: output.write_bytes(b'wav'))
    def assemble(master, folder, phrases, duration):
        assert master.read_bytes() == b'original master'
        (folder / 'video.mp4').write_bytes(b'dubbed video')
        return {'duration': duration, 'has_audio': True}
    monkeypatch.setattr(audio, 'assemble', assemble)
    ident = client.post(url, json=body()).json()['id']
    assert run_once()
    assert project(pid)['result'] == before
    assert client.get(f'/api/projects/{pid}/media/result').content == b'dubbed video'
    assert client.get(f'/api/projects/{pid}/media/master').content == b'original master'
    assert client.get(url).json()['final_version_id'] == ident
    assert client.get(url).json()['versions'][0]['status'] == 'ready'
    assert client.get(url + f'/{ident}/files/video.mp4').content == b'dubbed video'
    assert 'attachment' in client.get(url + f'/{ident}/files/video.mp4?download=true').headers['content-disposition']
    assert 'Привет!' in client.get(url + f'/{ident}/files/subtitles.vtt').text
    assert client.get(url + f'/{ident}/files/sample.mp3').status_code == 404
    assert client.post(url, json=body()).json()['id'] == ident
    with connect() as db:
        db.execute('UPDATE projects SET result=? WHERE id=?', (json.dumps(before | {'render_id': 'c' * 32}), pid))
    assert client.get(url).json()['versions'][0]['stale']
    assert client.get(url + f'/{ident}/files/video.mp4').status_code == 200
    app.dependency_overrides[current_user] = lambda: {'id': 'v'}
    assert client.get(url + f'/{ident}/files/video.mp4').status_code == 404


def test_failure_preserves_project_and_exposes_retry_reason(client, monkeypatch):
    pid = setup(client, monkeypatch)
    before = project(pid)
    url = f'/api/studio/projects/{pid}/dubbing'
    def fail(*args):
        raise ValueError('dubbing_speech_too_long')
    monkeypatch.setattr(audio, 'translate', fail)
    client.post(url, json=body())
    run_once()
    version = client.get(url).json()['versions'][0]
    assert version['status'] == 'failed' and version['error'] == 'dubbing_speech_too_long'
    after = project(pid)
    assert after['result'] == before['result'] and after['status'] == before['status']
    assert client.get(url).json()['final_version_id']=='master'
    assert client.get(f'/api/projects/{pid}/media/result').content==b'original master'
    assert client.post(url, json=body()).status_code == 202


def test_empty_speech_and_budget_rejected_before_queue(client, monkeypatch):
    pid = setup(client, monkeypatch)
    url = f'/api/studio/projects/{pid}/dubbing'
    with connect() as db:
        db.execute('UPDATE projects SET budget=0.001 WHERE id=?', (pid,))
    assert client.post(url, json=body()).json()['detail'] == 'budget_limit'
    assert client.post(url, json=body(kind='sample', master_id='')).json()['detail'] == 'budget_limit'
    with connect() as db:
        db.execute('UPDATE projects SET budget=5,analysis=? WHERE id=?', (json.dumps({'transcript': []}), pid))
    assert client.post(url, json=body()).json()['detail'] == 'dubbing_no_speech'
    assert client.get(url).json()['blocked_reason'] == 'dubbing_no_speech'


def test_sample_reuse_and_voices(client, monkeypatch):
    pid = setup(client, monkeypatch)
    url = f'/api/studio/projects/{pid}/dubbing'
    calls = []
    def synth(text, voice, path, model):
        calls.append((text, voice)); path.write_bytes(b'audio sample')
    monkeypatch.setattr(audio, 'synthesize', synth)
    monkeypatch.setattr(audio, 'probe_audio', lambda _: {'duration': 5})
    ident = client.post(url, json=body(kind='sample', master_id='')).json()['id']
    run_once()
    assert client.post(url, json=body(kind='sample', master_id='')).json()['id'] == ident
    assert len(calls) == 1 and calls[0][0] == audio.SAMPLES['ru']
    assert client.get(url).json()['final_version_id']=='master'
    assert client.get(f'/api/projects/{pid}/media/result').content==b'original master'
    assert client.get(url + f'/{ident}/files/sample.mp3').content == b'audio sample'
    assert client.get(url + f'/{ident}/files/video.mp4').status_code == 404


def test_mapping_uses_output_order_and_preserves_silence():
    transcript = [{'start': 1, 'end': 3, 'original': 'First.'}, {'start': 8, 'end': 10, 'original': 'Second.'}]
    master = {'timeline': [[8, 12], [0, 8]], 'metadata': {'duration': 12}}
    result = audio.mapped_speech(master, {'transcript': transcript})
    assert [(p['text'], p['start'], p['end']) for p in result] == [('Second.', 0, 2), ('First.', 5, 7)]
    with pytest.raises(ValueError, match='dubbing_clipped_speech'):
        audio.mapped_speech(master | {'timeline': [[2, 12]]}, {'transcript': transcript})
    with pytest.raises(ValueError, match='dubbing_no_speech'):
        audio.mapped_speech(master, {'transcript': []})


def test_invalid_translation_ids_are_rejected(monkeypatch):
    class Response:
        status_code = 200
        def json(self):
            return {'choices': [{'message': {'content': '{"phrases":[{"id":99,"text":"Привет"}]}'}}], 'usage': {'cost': .01}}
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return Response()
    monkeypatch.setattr(audio.httpx, 'Client', Client)
    monkeypatch.setattr(audio.ai, 'headers', lambda: {})
    monkeypatch.setattr(audio, 'reserve', lambda *args: 'reservation')
    monkeypatch.setattr(audio, 'settle', lambda *args: None)
    with pytest.raises(ValueError, match='dubbing_translation_invalid'):
        audio.translate('pid', [{'id': 0, 'start': 0, 'end': 2, 'text': 'Hello'}], 'ru')


def test_worker_restart_fails_interrupted_dub_without_replaying(client, monkeypatch):
    from backend import worker
    pid = setup(client, monkeypatch)
    before = project(pid)['result']
    ident = client.post(f'/api/studio/projects/{pid}/dubbing', json=body()).json()['id']
    with connect() as db:
        db.execute("UPDATE jobs SET status='running' WHERE project_id=? AND kind='dubbing'", (pid,))
        db.execute("UPDATE dubbing_versions SET status='synthesizing' WHERE id=?", (ident,))
    class StopWorker(Exception): pass
    def stop(): raise StopWorker()
    monkeypatch.setattr(worker, 'run_once', stop)
    with pytest.raises(StopWorker):
        worker.serve(None)
    with connect() as db:
        row = db.execute('SELECT status,error FROM dubbing_versions WHERE id=?', (ident,)).fetchone()
    assert row['status'] == 'failed' and row['error'] == 'worker_interrupted'
    assert project(pid)['result'] == before


def test_clipped_source_transcript_uses_final_master_recognition(client, monkeypatch):
    pid = setup(client, monkeypatch)
    p = project(pid)
    with connect() as db:
        db.execute('UPDATE projects SET result=? WHERE id=?', (json.dumps(p['result'] | {'timeline': [[1, 40]]}), pid))
    url = f'/api/studio/projects/{pid}/dubbing'
    catalog = client.get(url).json()
    assert catalog['blocked_reason'] is None and catalog['needs_transcription']
    assert catalog['max_cost'] == 2.94
    ident = client.post(url, json=body()).json()['id']
    calls = []
    def transcribe(pid, master, folder):
        calls.append(master['render_id'])
        return [{'id': 0, 'start': 0, 'end': 1, 'text': 'Actual cut speech'}]
    def translate(pid, spans, language):
        assert spans[0]['text'] == 'Actual cut speech'
        raise ValueError('dubbing_translation_invalid')
    monkeypatch.setattr(audio, 'transcribe_master', transcribe)
    monkeypatch.setattr(audio, 'translate', translate)
    run_once()
    assert calls == [MASTER]
    assert client.get(url).json()['versions'][0]['id'] == ident


def test_transcription_repairs_invalid_completed_reply_and_caches(tmp_path, monkeypatch):
    (tmp_path / 'qa.mp4').write_bytes(b'proxy')
    calls = []
    def generate(*args, **kwargs):
        calls.append(args)
        return audio.HeardSpeech(speech_detected=True, phrases=[audio.HeardPhrase(start=0, end=50 if len(calls)==1 else 2, text='Hello')])
    monkeypatch.setattr(audio.ai, 'json_call', generate)
    result = audio.transcribe_master('pid', {'metadata': {'duration': 4}}, tmp_path)
    assert result[0]['end'] == 2 and len(calls) == 2
    assert audio.transcribe_master('pid', {'metadata': {'duration': 4}}, tmp_path) == result
    assert len(calls) == 2


def test_transcription_never_retries_uncertain_network_failure(tmp_path, monkeypatch):
    (tmp_path / 'qa.mp4').write_bytes(b'proxy')
    calls = []
    def generate(*args, **kwargs):
        calls.append(1)
        raise TimeoutError('uncertain paid request')
    monkeypatch.setattr(audio.ai, 'json_call', generate)
    with pytest.raises(TimeoutError):
        audio.transcribe_master('pid', {'metadata': {'duration': 4}}, tmp_path)
    assert len(calls) == 1


def ready_delivery(pid, *, master=MASTER, kind='video', status='ready'):
    ident = uuid.uuid4().hex
    with connect() as db:
        db.execute('INSERT INTO dubbing_versions(id,project_id,request_id,master_id,language,voice,kind,status,snapshot,created) VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (ident,pid,uuid.uuid4().hex,master,'ru','ru-male',kind,status,json.dumps({'model':settings.dubbing_model}),1))
    folder=settings.data_dir/pid/'dubbing'/ident
    folder.mkdir(parents=True)
    (folder/'video.mp4').write_bytes(b'chosen voiceover')
    return ident


def test_final_selection_persists_restores_master_and_rejects_stale(client, monkeypatch):
    pid=setup(client,monkeypatch)
    url=f'/api/studio/projects/{pid}/dubbing'
    ident=ready_delivery(pid)
    selection={'master_id':MASTER,'version_id':ident}
    assert client.get(url).json()['final_version_id']=='master'
    assert client.put(url+'/final',json=selection).status_code==200
    assert client.get(url).json()['final_version_id']==ident
    assert client.get(f'/api/projects/{pid}/media/result').content==b'chosen voiceover'
    assert client.get(f'/api/projects/{pid}/media/master').content==b'original master'
    assert client.put(url+'/final',json=selection|{'version_id':'master'}).status_code==200
    assert client.get(f'/api/projects/{pid}/media/result').content==b'original master'
    # Reusing an already generated video still applies the requested voice, without another paid job.
    assert client.post(url,json=body()).json()['id']==ident
    assert client.get(url).json()['final_version_id']==ident
    new_master='c'*32
    before=project(pid)['result']
    with connect() as db:
        db.execute('UPDATE projects SET result=? WHERE id=?',(json.dumps(before|{'render_id':new_master}),pid))
    folder=settings.data_dir/pid/'renders'/new_master
    folder.mkdir(parents=True)
    (folder/'result.mp4').write_bytes(b'new edit')
    assert client.get(url).json()['final_version_id']=='master'
    assert client.get(f'/api/projects/{pid}/media/result').content==b'new edit'
    assert client.put(url+'/final',json=selection).status_code==409
    assert client.put(url+'/final',json=selection|{'master_id':new_master}).status_code==409
    # Historical voiceovers remain accessible, but cannot replace the new edit.
    assert client.get(url+f'/{ident}/files/video.mp4').content==b'chosen voiceover'


def test_final_selection_ownership_readiness_and_missing_files(client, monkeypatch):
    pid=setup(client,monkeypatch)
    url=f'/api/studio/projects/{pid}/dubbing'
    for kind,status in [('sample','ready'),('video','queued'),('video','failed')]:
        ident=ready_delivery(pid,kind=kind,status=status)
        assert client.put(url+'/final',json={'master_id':MASTER,'version_id':ident}).status_code==404
    ident=ready_delivery(pid)
    (settings.data_dir/pid/'dubbing'/ident/'video.mp4').unlink()
    assert client.put(url+'/final',json={'master_id':MASTER,'version_id':ident}).status_code==404
    other=setup(client,monkeypatch)
    ident=ready_delivery(other)
    assert client.put(url+'/final',json={'master_id':MASTER,'version_id':ident}).status_code==404
    app.dependency_overrides[current_user]=lambda:{'id':'v'}
    assert client.put(url+'/final',json={'master_id':MASTER,'version_id':'master'}).status_code==404
    assert client.get(f'/api/projects/{pid}/media/result').status_code==404
    assert client.get(f'/api/projects/{pid}/media/master').status_code==404
