"""Owned, versioned voiceovers with durable jobs and immutable master snapshots."""
import json
import re
import shutil
import time
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import Field
from .auth import current_user
from .config import settings
from .db import connect, enqueue, reserve, event
from .schemas import Strict
from .studio import owned
from . import dubbing_audio as audio
from . import final_output

router = APIRouter(prefix='/api/studio')
ERRORS = {'dubbing_no_speech', 'dubbing_clipped_speech', 'dubbing_overlapping_speech',
          'dubbing_transcript_too_long', 'dubbing_translation_invalid', 'dubbing_audio_invalid',
          'dubbing_speech_too_long', 'dubbing_provider_failed', 'provider_not_configured',
          'provider_credits_required', 'budget_limit', 'output_duration_mismatch'}


def init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS dubbing_versions(
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        request_id TEXT NOT NULL, master_id TEXT NOT NULL, language TEXT NOT NULL, voice TEXT NOT NULL,
        kind TEXT NOT NULL, status TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
        snapshot TEXT NOT NULL, result TEXT, error TEXT, created REAL NOT NULL,
        UNIQUE(project_id,request_id))''')

    final_output.init(db)


class Create(Strict):
    request_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    master_id: str = Field(default='', pattern=r'^(?:[a-f0-9]{32})?$')
    language: Literal['ru', 'en', 'zh']
    voice: str = Field(max_length=40)
    kind: Literal['sample', 'video'] = 'video'
    replace_audio: Literal[True]


def public(row, current_master):
    return {k: row[k] for k in ('id', 'master_id', 'language', 'voice', 'kind', 'status', 'progress', 'error', 'created')} | {
        'result': json.loads(row['result']) if row['result'] else None,
        'stale': row['kind'] == 'video' and row['master_id'] != current_master,
    }


@router.get('/projects/{pid}/dubbing')
def listing(pid: str, user=Depends(current_user)):
    p = owned(pid, user)
    master = p['result'] or {}
    reason = None
    needs_transcription = False
    if not settings.openrouter_api_key:
        reason = 'provider_not_configured'
    elif not master.get('render_id'):
        reason = 'dubbing_render_first'
    else:
        try:
            audio.mapped_speech(master, p['analysis'] or {})
        except ValueError as exc:
            if str(exc) in {'dubbing_clipped_speech', 'dubbing_overlapping_speech'}:
                needs_transcription = True
            else:
                reason = str(exc)
    with connect() as db:
        versions = [public(r, master.get('render_id')) for r in db.execute(
            'SELECT * FROM dubbing_versions WHERE project_id=? ORDER BY created DESC LIMIT 30', (pid,))]
        busy = bool(db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')", (pid,)).fetchone())
        selected = final_output.current(db, pid, master.get('render_id', ''))
    return {'final_version_id': selected['id'] if selected else 'master',
            'final_version': public(selected, master.get('render_id')) if selected else None, 'versions': versions, 'voices': [{'id': k, 'language': v['language'], 'name': v['name']} for k, v in audio.VOICES.items()],
            'blocked_reason': reason, 'busy': busy, 'master_id': master.get('render_id', ''),
            'needs_transcription': needs_transcription,
            'max_cost': round((1.5 if needs_transcription else .50) + audio.speech_reservation(audio.MAX_CHARACTERS), 2),
            'sample_max_cost': max(audio.speech_reservation(len(t)) for t in audio.SAMPLES.values()),
            'remaining_budget': max(0, p['budget'] - p['cost'])}


class FinalSelection(Strict):
    master_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    version_id: str = Field(pattern=r'^(?:master|[a-f0-9]{32})$')


@router.put('/projects/{pid}/dubbing/final')
def choose_final(pid: str, body: FinalSelection, user=Depends(current_user)):
    with connect() as db:
        db.lock()
        p = owned(pid, user)
        if (p['result'] or {}).get('render_id') != body.master_id:
            raise HTTPException(409, 'master_changed')
        if body.version_id != 'master':
            row = db.execute('SELECT * FROM dubbing_versions WHERE id=? AND project_id=?',
                             (body.version_id, pid)).fetchone()
            if not row or row['kind'] != 'video' or row['status'] != 'ready':
                raise HTTPException(404, 'not_ready')
            if row['master_id'] != body.master_id:
                raise HTTPException(409, 'master_changed')
            if not (settings.data_dir / pid / 'dubbing' / row['id'] / 'video.mp4').is_file():
                raise HTTPException(404, 'not_ready')
        final_output.select(db, pid, body.master_id, body.version_id)
    event(pid, 'final_output_selected', body.version_id)
    return {'final_version_id': body.version_id}


@router.post('/projects/{pid}/dubbing', status_code=202)
def create(pid: str, body: Create, request: Request, user=Depends(current_user)):
    from .app import rate_limit
    p = owned(pid, user)
    rate_limit(request, 'dubbing', 20, 3600)
    if body.voice not in audio.VOICES or audio.VOICES[body.voice]['language'] != body.language:
        raise HTTPException(422, 'dubbing_voice_mismatch')
    if not settings.openrouter_api_key:
        raise HTTPException(503, 'provider_not_configured')
    if shutil.disk_usage(settings.data_dir).free < 1024 ** 3:
        raise HTTPException(507, 'storage_full')
    with connect() as db:
        db.lock()
        existing = db.execute('SELECT * FROM dubbing_versions WHERE project_id=? AND request_id=?', (pid, body.request_id)).fetchone()
        if existing:
            if any(existing[k] != getattr(body, k) for k in ('voice', 'language', 'kind', 'master_id')):
                raise HTTPException(409, 'dubbing_request_changed')
            return {'id': existing['id']}
        p = owned(pid, user)
        master_id = body.master_id if body.kind == 'video' else ''
        cached = db.execute("SELECT * FROM dubbing_versions WHERE project_id=? AND master_id=? AND language=? AND voice=? AND kind=? AND status='ready' ORDER BY created DESC LIMIT 1",
                            (pid, master_id, body.language, body.voice, body.kind)).fetchone()
        # Completed voice samples are reusable; videos must still target the current master.
        if body.kind == 'video' and (not p['result'] or p['result'].get('render_id') != master_id):
            raise HTTPException(409, 'master_changed')
        if cached and json.loads(cached['snapshot']).get('model') == settings.dubbing_model:
            if body.kind == 'video':
                final_output.select(db, pid, master_id, cached['id'])
            return {'id': cached['id']}
        if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')", (pid,)).fetchone():
            raise HTTPException(409, 'job_already_running')
        snapshot = {'model': settings.dubbing_model}
        if body.kind == 'video':
            try:
                snapshot['phrases'] = audio.mapped_speech(p['result'], p['analysis'] or {})
            except ValueError as exc:
                if str(exc) not in {'dubbing_clipped_speech', 'dubbing_overlapping_speech'}:
                    raise HTTPException(422, str(exc)) from None
                snapshot['phrases'] = None
            snapshot['master'] = p['result']
            maximum = (1.5 if snapshot['phrases'] is None else .50) + audio.speech_reservation(audio.MAX_CHARACTERS)
        else:
            maximum = audio.speech_reservation(len(audio.SAMPLES[body.language]))
        if p['cost'] + maximum > p['budget']:
            raise HTTPException(409, 'budget_limit')
        ident = uuid.uuid4().hex
        db.execute('INSERT INTO dubbing_versions(id,project_id,request_id,master_id,language,voice,kind,status,snapshot,created) VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (ident, pid, body.request_id, master_id, body.language, body.voice, body.kind, 'queued', json.dumps(snapshot), time.time()))
        enqueue(db, pid, 'dubbing', {'id': ident})
    return {'id': ident}


@router.get('/projects/{pid}/dubbing/{ident}/files/{filename}')
def file(pid: str, ident: str, filename: str, download: bool = False, user=Depends(current_user)):
    owned(pid, user)
    if not re.fullmatch(r'[a-f0-9]{32}', ident):
        raise HTTPException(404, 'not_ready')
    with connect() as db:
        row = db.execute('SELECT * FROM dubbing_versions WHERE id=? AND project_id=?', (ident, pid)).fetchone()
    if not row or row['status'] != 'ready':
        raise HTTPException(404, 'not_ready')
    allowed = {'sample.mp3': 'audio/mpeg'} if row['kind'] == 'sample' else {'video.mp4': 'video/mp4', 'subtitles.vtt': 'text/vtt'}
    path = settings.data_dir / pid / 'dubbing' / ident / filename
    if filename not in allowed or not path.is_file():
        raise HTTPException(404, 'not_ready')
    return FileResponse(path, media_type=allowed[filename], filename=f"lumen-{pid[:8]}-{row['language']}-{filename}",
                        content_disposition_type='attachment' if download else 'inline')


def advance(ident, status, progress):
    with connect() as db:
        db.execute('UPDATE dubbing_versions SET status=?,progress=? WHERE id=?', (status, progress, ident))


def run_job(p, payload):
    with connect() as db:
        row = db.execute('SELECT * FROM dubbing_versions WHERE id=? AND project_id=?', (payload['id'], p['id'])).fetchone()
    if not row:
        raise ValueError('dubbing_not_found')
    ident = row['id']
    folder = settings.data_dir / p['id'] / 'dubbing' / ident
    folder.mkdir(parents=True, exist_ok=True)
    snapshot = json.loads(row['snapshot'])
    try:
        if row['kind'] == 'sample':
            advance(ident, 'synthesizing', 20)
            text = audio.SAMPLES[row['language']]
            reserve(p['id'], audio.speech_reservation(len(text)), 'dubbing_voice_sample')
            audio.synthesize(text, row['voice'], folder / 'sample.mp3', snapshot['model'])
            result = {'duration': audio.probe_audio(folder / 'sample.mp3')['duration']}
        else:
            master = snapshot['master']
            master_path = settings.data_dir / p['id'] / 'renders' / row['master_id'] / 'result.mp4'
            if not master_path.is_file():
                raise ValueError('dubbing_master_missing')
            source_phrases = snapshot['phrases']
            if source_phrases is None:
                advance(ident, 'transcribing', 2)
                source_phrases = audio.transcribe_master(p['id'], master, master_path.parent)
            advance(ident, 'translating', 5)
            phrases = audio.translate(p['id'], source_phrases, row['language'])
            reserve(p['id'], audio.speech_reservation(sum(len(x['text']) for x in phrases)), 'dubbing_speech')
            for i, phrase in enumerate(phrases):
                advance(ident, 'synthesizing', 15 + int(i / len(phrases) * 65))
                mp3 = folder / f'{i}.mp3'
                audio.synthesize(phrase['text'], row['voice'], mp3, snapshot['model'])
                audio.fit_phrase(mp3, folder / f'{i}.wav', phrase['end'] - phrase['start'])
            advance(ident, 'muxing', 85)
            result = audio.assemble(master_path, folder, phrases, master['metadata']['duration'])
            audio.write_vtt(folder / 'subtitles.vtt', phrases)
            result['phrase_count'] = len(phrases)
        with connect() as db:
            db.lock()
            db.execute("UPDATE dubbing_versions SET status='ready',progress=100,result=? WHERE id=?", (json.dumps(result), ident))
            if row['kind'] == 'video':
                latest = db.execute('SELECT result FROM projects WHERE id=?', (p['id'],)).fetchone()
                if latest and json.loads(latest['result'] or '{}').get('render_id') == row['master_id']:
                    final_output.select(db, p['id'], row['master_id'], ident)
        event(p['id'], 'dubbing_ready', json.dumps({'id': ident, 'language': row['language'], 'kind': row['kind']}))
    except Exception as exc:
        code = str(exc) if str(exc) in ERRORS else 'dubbing_failed'
        with connect() as db:
            db.execute("UPDATE dubbing_versions SET status='failed',error=? WHERE id=?", (code, ident))
        raise
    finally:
        # Intermediate speech is not exposed; keep only completed delivery files.
        for path in folder.iterdir():
            if path.suffix == '.wav' or (path.suffix == '.mp3' and path.name != 'sample.mp3'):
                path.unlink(missing_ok=True)
