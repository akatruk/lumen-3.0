"""Curated music and private cross-project reuse, through normal project assets."""
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from .auth import current_user
from .config import settings
from .db import connect
from .schemas import Strict
from .studio import owned
from .assets import path as asset_path

router = APIRouter(prefix='/api/studio')
MANIFEST = Path(__file__).parent / 'data' / 'soundtracks.json'


def init(db):
    db.execute('CREATE TABLE IF NOT EXISTS soundtrack_favorites(user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, track_key TEXT NOT NULL, PRIMARY KEY(user_id,track_key))')


def curated():
    return json.loads(MANIFEST.read_text())


def resolve(key, user, db):
    if key.startswith('curated:'):
        row = next((r for r in curated() if key == 'curated:' + r['id']), None)
        if row:
            return {'key': key, 'title': row['title'], 'attribution': row['attribution'],
                    'metadata': {'duration': row['duration'], 'kind': 'music', 'mime': 'audio/mpeg', 'catalogue_id': row['id']},
                    'path': settings.data_dir / 'soundtracks' / (row['id'] + '.mp3')}
    elif re.fullmatch(r'asset:[a-f0-9]{32}', key):
        row = db.execute('SELECT a.* FROM studio_assets a JOIN projects p ON p.id=a.project_id WHERE a.id=? AND p.user_id=?', (key[6:], user['id'])).fetchone()
        if row:
            meta = json.loads(row['metadata'])
            if meta.get('kind') == 'music':
                return {'key': key, 'title': row['title'], 'attribution': row['attribution'], 'metadata': meta, 'path': asset_path(row['project_id'], row['id'])}
    raise HTTPException(404, 'soundtrack_not_found')


@router.get('/soundtracks')
def listing(user=Depends(current_user)):
    with connect() as db:
        favorites = {r['track_key'] for r in db.execute('SELECT track_key FROM soundtrack_favorites WHERE user_id=?', (user['id'],))}
        rows = [{k: v for k, v in r.items() if k not in ('download_url', 'sha256')} | {
            'key': 'curated:' + r['id'], 'origin': 'curated',
            'available': (settings.data_dir / 'soundtracks' / (r['id'] + '.mp3')).is_file(),
        } for r in curated()]
        for row in db.execute('SELECT a.*,p.title AS project_title FROM studio_assets a JOIN projects p ON p.id=a.project_id WHERE p.user_id=? ORDER BY a.created DESC', (user['id'],)):
            meta = json.loads(row['metadata'])
            if meta.get('kind') != 'music' or meta.get('catalogue_id') or meta.get('reused_from'):
                continue
            rows.append({'key': 'asset:' + row['id'], 'title': row['title'], 'artist': row['project_title'],
                         'origin': 'uploaded', 'mood': 'other', 'duration': meta['duration'], 'bpm': None,
                         'attribution': row['attribution'], 'available': asset_path(row['project_id'], row['id']).is_file()})
    return [r | {'favorite': r['key'] in favorites} for r in rows]


@router.get('/soundtracks/{key}/media')
def preview(key: str, user=Depends(current_user)):
    with connect() as db:
        row = resolve(key, user, db)
    if not row['path'].is_file():
        raise HTTPException(404, 'soundtrack_unavailable')
    return FileResponse(row['path'], media_type=row['metadata'].get('mime', 'audio/mpeg'))


class Favorite(Strict):
    favorite: bool


@router.put('/soundtracks/{key}/favorite')
def favorite(key: str, body: Favorite, user=Depends(current_user)):
    with connect() as db:
        resolve(key, user, db)
        if body.favorite:
            db.execute('INSERT INTO soundtrack_favorites(user_id,track_key) VALUES(?,?) ON CONFLICT(user_id,track_key) DO NOTHING', (user['id'], key))
        else:
            db.execute('DELETE FROM soundtrack_favorites WHERE user_id=? AND track_key=?', (user['id'], key))
    return {'favorite': body.favorite}


@router.post('/projects/{pid}/soundtracks/{key}', status_code=201)
def add(pid: str, key: str, user=Depends(current_user)):
    owned(pid, user)
    with connect() as db:
        db.lock()
        row = resolve(key, user, db)
        if not row['path'].is_file():
            raise HTTPException(409, 'soundtrack_unavailable')
        # Re-adding the same source never consumes another project asset slot.
        request_id = uuid.uuid5(uuid.NAMESPACE_URL, 'lumen:soundtrack:' + pid + ':' + key).hex
        old = db.execute('SELECT id FROM studio_assets WHERE project_id=? AND request_id=?', (pid, request_id)).fetchone()
        if old:
            return {'id': old['id'], 'existing': True}
        if key.startswith('asset:') and db.execute('SELECT id FROM studio_assets WHERE project_id=? AND id=?', (pid, key[6:])).fetchone():
            return {'id': key[6:], 'existing': True}
        if db.execute('SELECT count(*) FROM studio_assets WHERE project_id=?', (pid,)).fetchone()[0] >= 20:
            raise HTTPException(422, 'asset_limit')
        if shutil.disk_usage(settings.data_dir).free < row['path'].stat().st_size + 1024 ** 3:
            raise HTTPException(507, 'storage_full')
        ident = uuid.uuid4().hex
        target = asset_path(pid, ident)
        target.parent.mkdir(exist_ok=True)
        try:
            try:
                os.link(row['path'], target)
            except OSError:
                shutil.copyfile(row['path'], target)
            meta = row['metadata'] | {'reused_from': key, 'size': target.stat().st_size}
            db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)', (ident, pid, request_id, row['title'], row['attribution'], json.dumps(meta), time.time()))
        except Exception:
            target.unlink(missing_ok=True)
            raise
    return {'id': ident, 'existing': False}
