"""Bounded resumable uploads. No analysis is queued until explicit completion."""
import time,uuid
from fastapi import APIRouter,Depends,HTTPException,Request,UploadFile
from pydantic import Field
from .schemas import Strict
from .auth import current_user
from .config import settings
from .db import connect,project
router=APIRouter(prefix='/api/studio/uploads')
CHUNK=4*1024*1024
class Begin(Strict):
    size:int=Field(gt=0,le=250*1024*1024)
    token:str=Field(pattern=r'^[a-f0-9]{32}$')

def init(db):
    db.execute('CREATE TABLE IF NOT EXISTS studio_uploads(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,token TEXT NOT NULL,size INTEGER NOT NULL,received INTEGER NOT NULL,created REAL NOT NULL,UNIQUE(user_id,token))')

def path(ident):return settings.data_dir/'uploads'/ident

def owned(db,ident,user):
    r=db.execute('SELECT * FROM studio_uploads WHERE id=? AND user_id=?',(ident,user['id'])).fetchone()
    if not r:raise HTTPException(404,'upload_not_found')
    if r['created']<time.time()-86400:raise HTTPException(410,'upload_expired')
    return r

def status(r):return {'id':r['id'],'offset':r['received'],'size':r['size'],'chunk_size':CHUNK}

@router.post('',status_code=201)
def begin(body:Begin,request:Request,user=Depends(current_user)):
    from .app import rate_limit
    rate_limit(request,'upload_begin',30,3600)
    with connect() as db:
        db.lock()
        # Expired temporary transfers cannot be resumed and are never source projects.
        expired=db.execute('SELECT id FROM studio_uploads WHERE created<?',(time.time()-86400,)).fetchall()
        for r in expired:path(r['id']).unlink(missing_ok=True)
        db.execute('DELETE FROM studio_uploads WHERE created<?',(time.time()-86400,))
        old=db.execute('SELECT * FROM studio_uploads WHERE user_id=? AND token=?',(user['id'],body.token)).fetchone()
        if old:
            if old['size']!=body.size:raise HTTPException(409,'upload_changed')
            return status(old)
        import shutil
        if shutil.disk_usage(settings.data_dir).free<body.size+1024**3:raise HTTPException(507,'storage_full')
        if db.execute('SELECT count(*) FROM studio_uploads WHERE user_id=?',(user['id'],)).fetchone()[0]>=5:raise HTTPException(429,'too_many_uploads')
        ident=uuid.uuid4().hex
        path(ident).parent.mkdir(exist_ok=True)
        path(ident).touch(mode=0o600)
        db.execute('INSERT INTO studio_uploads VALUES(?,?,?,?,?,?)',(ident,user['id'],body.token,body.size,0,time.time()))
    return {'id':ident,'offset':0,'size':body.size,'chunk_size':CHUNK}

@router.get('/completed/{token}')
def completed(token:str,user=Depends(current_user)):
    with connect() as db:
        r=db.execute('SELECT project_id FROM studio_requests WHERE user_id=? AND token=?',(user['id'],token)).fetchone()
    return {'id':r['project_id']} if r else {}

@router.get('/{ident}')
def get(ident:str,user=Depends(current_user)):
    with connect() as db:return status(owned(db,ident,user))

@router.put('/{ident}')
async def append(ident:str,request:Request,offset:int,user=Depends(current_user)):
    with connect() as db:owned(db,ident,user)
    data=bytearray()
    async for block in request.stream():
        data.extend(block)
        if len(data)>CHUNK:raise HTTPException(413,'chunk_too_large')
    if not data:raise HTTPException(422,'empty_chunk')
    with connect() as db:
        db.lock();r=owned(db,ident,user)
        if offset!=r['received']:raise HTTPException(409,'upload_offset_changed')
        if offset+len(data)>r['size']:raise HTTPException(413,'upload_too_large')
        with path(ident).open('r+b') as f:
            f.truncate(offset);f.seek(offset);f.write(data);f.flush()
        db.execute('UPDATE studio_uploads SET received=? WHERE id=?',(offset+len(data),ident))
    return {'offset':offset+len(data)}

@router.post('/{ident}/complete',status_code=201)
async def complete(ident:str,request:Request,user=Depends(current_user)):
    from .studio import Create,create
    from pydantic import ValidationError
    try:body=Create.model_validate(await request.json())
    except (ValidationError,ValueError):raise HTTPException(422,'invalid_settings') from None
    # A lost completion response must not upload or analyze the same source twice.
    with connect() as db:
        old=db.execute('SELECT project_id FROM studio_requests WHERE user_id=? AND token=?',(user['id'],body.request_id)).fetchone()
        if old:return project(old['project_id'],user['id'])
        r=owned(db,ident,user)
        if r['received']!=r['size']:raise HTTPException(409,'upload_incomplete')
    with path(ident).open('rb') as source:
        result=await create(request,body.model_dump_json(),UploadFile(file=source,filename='source.mp4'),user)
    with connect() as db:
        db.execute('DELETE FROM studio_uploads WHERE id=? AND user_id=?',(ident,user['id']))
    path(ident).unlink(missing_ok=True)
    return result

@router.get('/completed-asset/{token}')
def completed_asset(token:str,user=Depends(current_user)):
    from .assets import completed
    return completed(token,user)

@router.post('/{ident}/asset',status_code=201)
async def complete_asset(ident:str,request:Request,user=Depends(current_user)):
    from .assets import AssetCreate,ingest
    from pydantic import ValidationError
    try:body=AssetCreate.model_validate(await request.json())
    except (ValueError,ValidationError):raise HTTPException(422,'invalid_settings') from None
    return await ingest(ident,body,user)
