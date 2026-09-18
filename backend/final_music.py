"""Free, immutable music mixes over the chosen finished picture and voice."""
import json, shutil, time, uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import Field
from .auth import current_user
from .config import settings
from .db import connect, enqueue, event
from .schemas import Strict
from .music import Music
from . import final_output, assets, media, music

router=APIRouter(prefix='/api/studio')

def init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS final_music_versions(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      request_id TEXT NOT NULL, master_id TEXT NOT NULL, source_voice TEXT NOT NULL,
      expected_final TEXT NOT NULL, music TEXT, title TEXT NOT NULL, status TEXT NOT NULL,
      result TEXT, error TEXT, created DOUBLE PRECISION NOT NULL,
      UNIQUE(project_id,request_id))''')


def config_of(row, master):
    if row and row.get('delivery')=='mix': return json.loads(row['music']) if row['music'] else None
    if row and row.get('delivery')=='dub': return None
    if 'music' in master:return master['music']
    legacy=((master.get('director_timeline') or {}).get('tracks') or {}).get('music') or []
    return {k:v for k,v in legacy[0].items() if k in Music.model_fields} if legacy else None


def voice_of(row):
    if not row:return ''
    return row.get('source_voice','') if row.get('delivery')=='mix' else row['id']


def validate_track(pid, config, duration, db):
    if not config:return ''
    parsed=Music.model_validate(config)
    row=db.execute('SELECT title,metadata FROM studio_assets WHERE id=? AND project_id=?',(parsed.asset_id,pid)).fetchone()
    if not row:raise HTTPException(422,'asset_not_found')
    metadata=json.loads(row['metadata'])
    if metadata.get('kind')!='music' or parsed.source_start>=metadata['duration']-.1:raise HTTPException(422,'invalid_music_range')
    if any(p.at>duration for p in parsed.levels):raise HTTPException(422,'invalid_music_range')
    if not assets.path(pid,parsed.asset_id).is_file():raise HTTPException(422,'asset_not_found')
    return row['title']


def queue(db,p,config,voice,expected,request_id=None):
    master=p['result'];title=validate_track(p['id'],config,master['metadata']['duration'],db)
    ident=uuid.uuid4().hex
    db.execute('INSERT INTO final_music_versions(id,project_id,request_id,master_id,source_voice,expected_final,music,title,status,created) VALUES(?,?,?,?,?,?,?,?,?,?)',
      (ident,p['id'],request_id or uuid.uuid4().hex,master['render_id'],voice,expected,json.dumps(config) if config else None,title,'queued',time.time()))
    enqueue(db,p['id'],'final_music',{'id':ident})
    return ident


def base_path(pid,master,voice):
    if voice:return settings.data_dir/pid/'dubbing'/voice/'video.mp4'
    folder=settings.data_dir/pid/'renders'/master['render_id']
    if (folder/'music-free.mp4').is_file():return folder/'music-free.mp4'
    # Never layer new music over an old baked-in soundtrack that cannot be removed.
    timeline_music=((master.get('director_timeline') or {}).get('tracks') or {}).get('music')
    if master.get('music') or timeline_music:raise HTTPException(409,'music_base_unavailable')
    return folder/'result.mp4'


def promote_voice(db,p,voice):
    selected=final_output.current(db,p['id'],p['result']['render_id'])
    config=config_of(selected,p['result'])
    if config:
        source=base_path(p['id'],p['result'],voice)
        if not source.is_file():raise HTTPException(404,'not_ready')
        queue(db,p,config,voice,selected['id'] if selected else 'master')
        return selected['id'] if selected else 'master'
    final_output.select(db,p['id'],p['result']['render_id'],voice or 'master')
    return voice or 'master'


class Apply(Strict):
    request_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    revision:int=Field(ge=1)
    master_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    final_id:str=Field(pattern=r'^(?:master|[a-f0-9]{32})$')


@router.get('/projects/{pid}/final-music')
def listing(pid:str,user=Depends(current_user)):
    from .studio import owned
    p=owned(pid,user);master=p['result'] or {}
    with connect() as db:
        selected=final_output.current(db,pid,master.get('render_id',''))
        config=config_of(selected,master)
        title=''
        if config:
            asset=db.execute('SELECT title FROM studio_assets WHERE project_id=? AND id=?',(pid,config['asset_id'])).fetchone()
            title=asset['title'] if asset else ''
        jobs=[dict(r) for r in db.execute('SELECT id,status,error,master_id,title FROM final_music_versions WHERE project_id=? ORDER BY created DESC LIMIT 5',(pid,))]
    return {'master_id':master.get('render_id',''),'final_id':selected['id'] if selected else 'master','music':config,'title':title,'voice_id':voice_of(selected),'jobs':jobs}


@router.post('/projects/{pid}/final-music',status_code=202)
def apply(pid:str,body:Apply,request:Request,user=Depends(current_user)):
    from .studio import owned
    from .manual import locked_state,read
    from .app import rate_limit
    owned(pid,user);rate_limit(request,'final_music',20,3600)
    if shutil.disk_usage(settings.data_dir).free<1024**3:raise HTTPException(507,'storage_full')
    with connect() as db:
        db.lock();p=owned(pid,user)
        existing=db.execute('SELECT id FROM final_music_versions WHERE project_id=? AND request_id=?',(pid,body.request_id)).fetchone()
        if existing:return {'id':existing['id']}
        locked_state(pid,body.revision,db)
        master=p['result'] or {}
        if master.get('render_id')!=body.master_id:raise HTTPException(409,'master_changed')
        selected=final_output.current(db,pid,body.master_id)
        if (selected['id'] if selected else 'master')!=body.final_id:raise HTTPException(409,'final_changed')
        edit=read(pid,db)
        if edit is None:raise HTTPException(422,'save_manual_first')
        voice=voice_of(selected)
        if not base_path(pid,master,voice).is_file():raise HTTPException(404,'not_ready')
        ident=queue(db,p,edit.get('music'),voice,body.final_id,body.request_id)
    return {'id':ident}


@router.get('/projects/{pid}/final-music/{ident}/video.mp4')
def file(pid:str,ident:str,download:bool=False,user=Depends(current_user)):
    from .studio import owned
    owned(pid,user)
    with connect() as db:row=db.execute("SELECT id FROM final_music_versions WHERE id=? AND project_id=? AND status='ready'",(ident,pid)).fetchone()
    if not row:raise HTTPException(404,'not_ready')
    path=settings.data_dir/pid/'audio-mixes'/row['id']/'video.mp4'
    if not path.is_file():raise HTTPException(404,'not_ready')
    return FileResponse(path,media_type='video/mp4',filename=f'lumen-{pid[:8]}-music.mp4',content_disposition_type='attachment' if download else 'inline')


def run_job(p,payload):
    with connect() as db:row=db.execute('SELECT * FROM final_music_versions WHERE id=? AND project_id=?',(payload['id'],p['id'])).fetchone()
    if not row:raise ValueError('mix_not_found')
    ident=row['id'];folder=settings.data_dir/p['id']/'audio-mixes'/ident;folder.mkdir(parents=True,exist_ok=True)
    try:
        if (p['result'] or {}).get('render_id')!=row['master_id']:raise ValueError('master_changed')
        source=base_path(p['id'],p['result'],row['source_voice'])
        config=json.loads(row['music']) if row['music'] else None
        with connect() as db:
            validate_track(p['id'],config,p['result']['metadata']['duration'],db)
            db.execute("UPDATE final_music_versions SET status='mixing' WHERE id=?",(ident,))
        destination=folder/'video.mp4'
        if config:
            meta=media.probe(source)
            output=music.mix(source,assets.path(p['id'],config['asset_id']),folder,config,meta['duration'],meta['has_audio'])
            output.replace(destination)
        else:shutil.copyfile(source,destination)
        meta=media.probe(destination)
        if abs(meta['duration']-p['result']['metadata']['duration'])>.2:raise ValueError('output_duration_mismatch')
        with connect() as db:
            db.lock()
            latest=db.execute('SELECT result FROM projects WHERE id=?',(p['id'],)).fetchone()
            master=json.loads(latest['result'] or '{}') if latest else {}
            selected=final_output.current(db,p['id'],master.get('render_id',''))
            if master.get('render_id')!=row['master_id'] or (selected['id'] if selected else 'master')!=row['expected_final']:raise ValueError('final_changed')
            db.execute("UPDATE final_music_versions SET status='ready',result=? WHERE id=?",(json.dumps(meta),ident))
            final_output.select(db,p['id'],row['master_id'],ident)
        event(p['id'],'final_music_ready',ident)
    except Exception as exc:
        code=str(exc) if str(exc) in {'master_changed','final_changed','output_duration_mismatch'} else 'music_mix_failed'
        with connect() as db:db.execute("UPDATE final_music_versions SET status='failed',error=? WHERE id=?",(code,ident))
        raise
