"""Private immutable project footage, uploaded with the resumable transport."""
import json,time,uuid,os
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import FileResponse
from pydantic import Field
from .schemas import Strict
from .config import settings
from .db import connect
from .auth import current_user
router=APIRouter(prefix='/api/studio')
class AssetCreate(Strict):
    kind:Literal['video','music']='video'
    asset_project_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    request_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    title:str=Field(min_length=1,max_length=120)
    attribution:str=Field(min_length=1,max_length=1000)
    owned_rights_confirmed:Literal[True]

def init(db):
    from .stock import init as init_stock
    init_stock(db)
    db.execute('CREATE TABLE IF NOT EXISTS studio_assets(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,request_id TEXT NOT NULL,title TEXT NOT NULL,attribution TEXT NOT NULL,metadata TEXT NOT NULL,created REAL NOT NULL,UNIQUE(project_id,request_id))')

def path(pid,ident):return settings.data_dir/pid/'assets'/ident

@router.post('/projects/{pid}/assets/{ident}/rhythm')
def rhythm(pid:str,ident:str,request:Request,user=Depends(current_user)):
    from .studio import owned
    from .app import rate_limit
    from .rhythm import analyze
    owned(pid,user)
    with connect() as db:
        row=db.execute('SELECT metadata FROM studio_assets WHERE id=? AND project_id=?',(ident,pid)).fetchone()
    if not row:raise HTTPException(404,'asset_not_found')
    metadata=json.loads(row['metadata'])
    if metadata.get('kind')!='music':raise HTTPException(422,'not_audio')
    if metadata.get('rhythm',{}).get('version')==1:return metadata['rhythm']
    rate_limit(request,'music_rhythm',20,3600)
    result=analyze(path(pid,ident));metadata['rhythm']=result
    with connect() as db:db.execute('UPDATE studio_assets SET metadata=? WHERE id=? AND project_id=?',(json.dumps(metadata),ident,pid))
    return result

def completed(token,user):
    with connect() as db:
        r=db.execute('SELECT a.id FROM studio_assets a JOIN projects p ON p.id=a.project_id WHERE a.request_id=? AND p.user_id=?',(token,user['id'])).fetchone()
    return {'id':r['id']} if r else {}

@router.get('/projects/{pid}/assets')
def listing(pid:str,user=Depends(current_user)):
    from .studio import owned
    owned(pid,user)
    with connect() as db:
        return [dict(r)|{'metadata':json.loads(r['metadata'])} for r in db.execute('SELECT id,title,attribution,metadata FROM studio_assets WHERE project_id=? ORDER BY created DESC',(pid,)).fetchall()]

@router.get('/projects/{pid}/assets/{ident}/media')
def media(pid:str,ident:str,user=Depends(current_user)):
    from .studio import owned
    owned(pid,user)
    with connect() as db:
        row=db.execute('SELECT metadata FROM studio_assets WHERE id=? AND project_id=?',(ident,pid)).fetchone()
        if not row:raise HTTPException(404,'asset_not_found')
    return FileResponse(path(pid,ident),media_type=json.loads(row['metadata']).get('mime','video/mp4'))

def validate(edit,pid,db):
    paths={}
    if edit.music:
        m=edit.music
        r=db.execute('SELECT metadata FROM studio_assets WHERE id=? AND project_id=?',(m.asset_id,pid)).fetchone()
        if not r:raise HTTPException(422,'asset_not_found')
        meta=json.loads(r['metadata'])
        if meta.get('kind')!='music' or m.source_start>=meta['duration']-.1:raise HTTPException(422,'invalid_music_range')
        paths[m.asset_id]=path(pid,m.asset_id)
    for clip in edit.clips:
        c=clip.external_broll
        if c:
            r=db.execute('SELECT metadata FROM studio_assets WHERE id=? AND project_id=?',(c.asset_id,pid)).fetchone()
            if not r:raise HTTPException(422,'asset_not_found')
            if json.loads(r['metadata']).get('kind')=='music':raise HTTPException(422,'not_a_video')
            if c.source_start+c.end-c.start>json.loads(r['metadata'])['duration']:raise HTTPException(422,'invalid_cutaway_range')
            paths[c.asset_id]=path(pid,c.asset_id)
        still=clip.stock_still
        if not still:continue
        row=db.execute('SELECT metadata FROM studio_assets WHERE id=? AND project_id=?',(still,pid)).fetchone()
        if not row:raise HTTPException(422,'asset_not_found')
        if json.loads(row['metadata']).get('kind')=='music':raise HTTPException(422,'not_a_video')
        paths[still]=path(pid,still)
    return paths

async def ingest(ident,body,user):
    from .studio import owned
    from .uploads import owned as owned_upload,path as upload_path
    from . import media as processing
    from starlette.concurrency import run_in_threadpool
    pid=body.asset_project_id;owned(pid,user)
    with connect() as db:
        old=db.execute('SELECT id FROM studio_assets WHERE project_id=? AND request_id=?',(pid,body.request_id)).fetchone()
        if old:return {'id':old['id']}
        r=owned_upload(db,ident,user)
        if r['received']!=r['size']:raise HTTPException(409,'upload_incomplete')
    from .music import probe_audio
    try:meta=await run_in_threadpool(probe_audio if body.kind=='music' else processing.probe,upload_path(ident))
    except Exception:raise HTTPException(422,'not_a_video') from None
    with upload_path(ident).open('rb') as f:header=f.read(1024)
    if header.startswith(bytes.fromhex('1a45dfa3')) and b'webm' not in header:raise HTTPException(422,'not_a_video')
    if body.kind=='video':meta['mime']='video/webm' if header.startswith(bytes.fromhex('1a45dfa3')) else 'video/mp4'
    used=await run_in_threadpool(lambda:sum(p.stat().st_size for p in settings.data_dir.rglob('*') if p.is_file()))
    if used>settings.max_storage_gb*1024**3:raise HTTPException(507,'storage_full')
    if not .1<=meta['duration']<=settings.max_duration_seconds:raise HTTPException(422,'asset_duration')
    # Store an immutable hard link; never move the upload while another finalizer can read it.
    with connect() as db:
        db.lock()
        old=db.execute('SELECT id FROM studio_assets WHERE project_id=? AND request_id=?',(pid,body.request_id)).fetchone()
        if old:return {'id':old['id']}
        if db.execute('SELECT count(*) FROM studio_assets WHERE project_id=?',(pid,)).fetchone()[0]>=20:raise HTTPException(422,'asset_limit')
        asset=uuid.uuid4().hex;target=path(pid,asset);target.parent.mkdir(exist_ok=True)
        os.link(upload_path(ident),target)
        db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)',(asset,pid,body.request_id,body.title,body.attribution,json.dumps(meta),time.time()))
        db.execute('DELETE FROM studio_uploads WHERE id=?',(ident,))
    upload_path(ident).unlink(missing_ok=True)
    return {'id':asset}
