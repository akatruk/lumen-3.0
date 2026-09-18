import hashlib
import hmac
import json
import re
import secrets
import shutil
import time
import uuid
from collections import defaultdict,deque
from contextlib import asynccontextmanager
from pathlib import Path
from pydantic import BaseModel,Field
from fastapi import FastAPI,Depends,HTTPException,Request,Response,UploadFile,File,Form
from fastapi.responses import FileResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from .config import ROOT,settings
from .db import init_db,connect,project,enqueue
from .auth import current_user,hash_password,verify,allowed_google_email
from .schemas import Credentials,RenderRequest,Analysis
from .media import probe,build_timeline

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app=FastAPI(title='Lumen Studio',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
limits=defaultdict(deque)

def rate_limit(request,category,count,seconds=60):
    key=(request.client.host if request.client else 'unknown',category)
    now=time.time(); q=limits[key]
    while q and q[0]<now-seconds: q.popleft()
    if len(q)>=count: raise HTTPException(429,'rate_limited')
    q.append(now)

@app.middleware('http')
async def security(request,call_next):
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        if origin and origin!=settings.public_origin:
            return Response('Invalid origin',status_code=403)
        if request.headers.get('sec-fetch-site')=='cross-site': return Response(status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'"
    if request.url.path.startswith('/api') or request.url.path in ('/','/index.html'):
        response.headers['Cache-Control']='no-store'
    return response

@app.get('/api/health')
def health():
    with connect() as db: db.execute('SELECT 1')
    return {'status':'ok','version':'0.1.0'}

@app.get('/api/session')
def session(user=Depends(current_user)):
    return user

@app.post('/api/register')
def register(body:Credentials,request:Request,response:Response):
    if settings.google_sso_only: raise HTTPException(403,'google_sign_in_required')
    rate_limit(request,'auth',10,300)
    if not settings.lumen_invite_code or not hmac.compare_digest(body.invite,settings.lumen_invite_code):
        raise HTTPException(403,'invalid_invite')
    email=body.email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise HTTPException(422,'invalid_email')
    uid=uuid.uuid4().hex
    with connect() as db:
        if db.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone(): raise HTTPException(409,'email_exists')
        db.execute('INSERT INTO users VALUES(?,?,?,?)',(uid,email,hash_password(body.password),time.time()))
    set_session(response,uid)
    return {'id':uid,'email':email}

def set_session(response,uid,method='password'):
    token=secrets.token_urlsafe(40)
    with connect() as db:
        db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
        db.execute('INSERT INTO sessions(token,user_id,expires,auth_method) VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),uid,time.time()+86400*7,method))
    response.set_cookie('lumen_session',token,httponly=True,secure=settings.secure_cookies,samesite='lax',max_age=86400*7)

@app.post('/api/login')
def login(body:Credentials,request:Request,response:Response):
    if settings.google_sso_only: raise HTTPException(403,'google_sign_in_required')
    rate_limit(request,'auth',10,300)
    with connect() as db: user=db.execute('SELECT * FROM users WHERE email=?',(body.email.strip().lower(),)).fetchone()
    if not user or not verify(body.password,user['password']): raise HTTPException(401,'invalid_credentials')
    set_session(response,user['id'])
    return {'id':user['id'],'email':user['email']}

@app.get('/api/auth/config')
def auth_config():
    return {'google_ready':bool(settings.google_client_id and settings.google_client_secret)}

@app.get('/api/auth/google')
def google_start(request:Request):
    import base64
    from urllib.parse import urlencode
    rate_limit(request,'oauth',20,300)
    if not settings.google_client_id or not settings.google_client_secret:
        return RedirectResponse('/?auth_error=google_unavailable',status_code=303)
    state=secrets.token_urlsafe(32); binding=secrets.token_urlsafe(32); verifier=secrets.token_urlsafe(48)
    with connect() as db:
        db.execute('DELETE FROM oauth_states WHERE expires<?',(time.time(),))
        db.execute('INSERT INTO oauth_states VALUES(?,?,?,?)',(hashlib.sha256(state.encode()).hexdigest(),hashlib.sha256(binding.encode()).hexdigest(),verifier,time.time()+600))
    params={'client_id':settings.google_client_id,'redirect_uri':settings.public_origin+'/api/auth/google/callback',
            'response_type':'code','scope':'openid email','state':state,'prompt':'select_account',
            'code_challenge':base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode(),
            'code_challenge_method':'S256'}
    response=RedirectResponse('https://accounts.google.com/o/oauth2/v2/auth?'+urlencode(params),status_code=303)
    response.set_cookie('lumen_oauth',binding,max_age=600,httponly=True,secure=settings.secure_cookies,samesite='lax',path='/api/auth/google/callback')
    return response

def google_identity(code,verifier):
    import httpx
    with httpx.Client(timeout=20) as client:
        token=client.post('https://oauth2.googleapis.com/token',data={
            'code':code,'client_id':settings.google_client_id,'client_secret':settings.google_client_secret,
            'redirect_uri':settings.public_origin+'/api/auth/google/callback','grant_type':'authorization_code','code_verifier':verifier})
        token.raise_for_status()
        # Retrieve identity directly from Google using the server-exchanged access token.
        info=client.get('https://openidconnect.googleapis.com/v1/userinfo',headers={'Authorization':'Bearer '+token.json()['access_token']})
        info.raise_for_status()
        return info.json()

@app.get('/api/auth/google/callback')
def google_callback(request:Request,state:str='',code:str='',error:str=''):
    response=RedirectResponse('/?auth_error=google_failed',status_code=303)
    response.delete_cookie('lumen_oauth',path='/api/auth/google/callback')
    binding=hashlib.sha256(request.cookies.get('lumen_oauth','').encode()).hexdigest()
    with connect() as db:
        db.lock()
        row=db.execute('SELECT * FROM oauth_states WHERE state=?',(hashlib.sha256(state.encode()).hexdigest(),)).fetchone()
        if not row or row['expires']<time.time() or not hmac.compare_digest(row['binding'],binding):
            return response
        db.execute('DELETE FROM oauth_states WHERE state=?',(row['state'],))
    if error or not code: return response
    try:
        info=google_identity(code,row['verifier'])
        email=info.get('email','').strip().lower()
        subject=info.get('sub')
        if info.get('email_verified') is not True or not isinstance(subject,str) or not subject or not allowed_google_email(email):
            response.headers['location']='/?auth_error=access_denied'
            return response
        with connect() as db:
            db.lock()
            identity=db.execute('SELECT user_id FROM google_identities WHERE subject=?',(subject,)).fetchone()
            user=db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
            if identity and (not user or user['id']!=identity['user_id']): return response
            uid=user['id'] if user else uuid.uuid4().hex
            other=db.execute('SELECT subject FROM google_identities WHERE user_id=?',(uid,)).fetchone()
            if other and other['subject']!=subject: return response
            if not user:
                db.execute('INSERT INTO users VALUES(?,?,?,?)',(uid,email,hash_password(secrets.token_urlsafe(48)),time.time()))
            db.execute('INSERT INTO google_identities VALUES(?,?) ON CONFLICT DO NOTHING',(subject,uid))
        set_session(response,uid,'google')
        response.headers['location']='/#studio'
    except Exception:
        # Never expose provider responses, tokens or codes to the browser/logs.
        return response
    return response

@app.post('/api/logout')
def logout(request:Request,response:Response):
    with connect() as db:
        db.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(request.cookies.get('lumen_session','').encode()).hexdigest(),))
    response.delete_cookie('lumen_session')
    return {'ok':True}

@app.get('/api/capabilities')
def capabilities(user=Depends(current_user)):
    return {'analysis':bool(settings.openrouter_api_key),'generation':bool(settings.openrouter_api_key),
            'max_upload_mb':settings.max_upload_mb,'max_duration_seconds':settings.max_duration_seconds,
            'douyin':bool(settings.tikhub_api_key),'analysis_model':settings.analysis_model,'generation_model':settings.generation_model}

@app.get('/api/projects')
def projects(user=Depends(current_user)):
    with connect() as db:
        return [dict(r) for r in db.execute('SELECT id,title,status,stage,progress,language,created,metadata FROM projects WHERE user_id=? ORDER BY created DESC',(user['id'],))]

@app.get('/api/projects/{pid}')
def detail(pid:str,user=Depends(current_user)):
    p=project(pid,user['id'])
    if not p: raise HTTPException(404,'not_found')
    return p

class DouyinSearchRequest(BaseModel):
    keyword: str = Field(min_length=1,max_length=120)
    sort: str = '1'
    publish_time: int = 0
    continuation: str = Field(default='',max_length=32)

class DouyinImportRequest(BaseModel):
    result_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    brief: str = Field(default='',max_length=6000)
    language: str = 'zh'
    aspect: str = 'original'
    auto_render: bool = True
    generative: bool = False
    budget: float = Field(default=3,ge=1,le=10)

@app.post('/api/douyin/search')
def douyin_search(body:DouyinSearchRequest,request:Request,user=Depends(current_user)):
    from . import douyin
    rate_limit(request,'douyin_search',15,60)
    if body.sort not in ('0','1','2') or body.publish_time not in (0,1,7,180):raise HTTPException(422,'invalid_settings')
    keyword=body.keyword.strip().rstrip('。，！？、；：.!?,;:').strip()
    if not keyword:raise HTTPException(422,'invalid_settings')
    try:return douyin.search(user['id'],keyword,body.sort,body.publish_time,body.continuation)
    except douyin.DouyinError as e:raise HTTPException(503,str(e)) from None

@app.get('/api/douyin/results/{rid}/cover')
def douyin_cover(rid:str,user=Depends(current_user)):
    from . import douyin
    if not re.fullmatch(r'[a-f0-9]{32}',rid):raise HTTPException(404,'not_found')
    try:
        result=douyin.owned_result(rid,user['id'])
        folder=settings.data_dir/'douyin_covers';folder.mkdir(exist_ok=True)
        path=folder/rid
        if not path.exists():
            if shutil.disk_usage(settings.data_dir).free<1.5*1024**3:raise ValueError('storage_full')
            import tempfile
            with tempfile.NamedTemporaryFile(dir=folder,delete=False) as f:temp=Path(f.name)
            try:
                douyin.download(result['cover_url'],temp,2*1024*1024)
                head=temp.read_bytes()[:16]
                if not (head.startswith(b'\xff\xd8\xff') or head.startswith(b'\x89PNG\r\n\x1a\n') or (head.startswith(b'RIFF') and head[8:12]==b'WEBP')):raise ValueError('invalid_image')
                temp.replace(path)
            finally:temp.unlink(missing_ok=True)
        head=path.read_bytes()[:16]
        mime='image/jpeg' if head.startswith(b'\xff\xd8') else 'image/png' if head.startswith(b'\x89PNG') else 'image/webp'
        return FileResponse(path,media_type=mime)
    except Exception:raise HTTPException(404,'not_found') from None

@app.post('/api/douyin/import',status_code=201)
def douyin_import(body:DouyinImportRequest,request:Request,user=Depends(current_user)):
    from . import douyin
    rate_limit(request,'douyin_import',8,3600)
    if body.language not in ('en','zh') or body.aspect not in ('original','9:16','16:9','1:1'):raise HTTPException(422,'invalid_settings')
    try:result=douyin.owned_result(body.result_id,user['id'])
    except douyin.DouyinError as e:raise HTTPException(404,str(e)) from None
    if shutil.disk_usage(settings.data_dir).free<1.5*1024**3:raise HTTPException(507,'storage_full')
    if sum(p.stat().st_size for p in settings.data_dir.rglob('*') if p.is_file())>settings.max_storage_gb*1024**3:raise HTTPException(507,'storage_full')
    source={k:result[k] for k in ('aweme_id','title','author','share_url','likes','published_at')}
    source.update(platform='douyin',imported_at=time.time())
    with connect() as db:
        db.lock()
        existing=db.execute('SELECT p.id FROM projects p JOIN project_sources s ON s.project_id=p.id WHERE p.user_id=? AND s.result_id=?',(user['id'],body.result_id)).fetchone()
        if existing:pid=existing['id']
        else:
            pending=db.execute("SELECT COUNT(*) FROM projects WHERE user_id=? AND status IN ('queued','analyzing','rendering')",(user['id'],)).fetchone()[0]
            if pending>=3:raise HTTPException(429,'too_many_jobs')
            pid=uuid.uuid4().hex;now=time.time()
            db.execute('INSERT INTO projects(id,user_id,title,brief,language,aspect,auto_render,generative,budget,status,stage,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (pid,user['id'],result['title'][:120],body.brief,body.language,body.aspect,int(body.auto_render),int(body.generative),body.budget,'queued','importing',now,now))
            db.execute('INSERT INTO project_sources VALUES(?,?,?)',(pid,body.result_id,json.dumps(source,ensure_ascii=False)))
            enqueue(db,pid,'analyze')
    return project(pid,user['id'])

@app.post('/api/projects',status_code=201)
async def upload(request:Request,file:UploadFile=File(...),title:str=Form(''),brief:str=Form(''),language:str=Form('en'),
                 aspect:str=Form('original'),auto_render:bool=Form(True),generative:bool=Form(False),budget:float=Form(3),user=Depends(current_user)):
    rate_limit(request,'upload',8,3600)
    if language not in ('en','zh') or aspect not in ('original','9:16','16:9','1:1') or not 1<=budget<=10:
        raise HTTPException(422,'invalid_settings')
    if len(brief)>6000 or len(title)>120: raise HTTPException(422,'text_too_long')
    with connect() as db:
        pending=db.execute("SELECT COUNT(*) FROM projects WHERE user_id=? AND status IN ('queued','analyzing','rendering')",(user['id'],)).fetchone()[0]
        if pending>=3: raise HTTPException(429,'too_many_jobs')
    if shutil.disk_usage(settings.data_dir).free<1.5*1024**3: raise HTTPException(507,'storage_full')
    used=await run_in_threadpool(lambda:sum(p.stat().st_size for p in settings.data_dir.rglob('*') if p.is_file()))
    if used>settings.max_storage_gb*1024**3: raise HTTPException(507,'storage_full')
    pid=uuid.uuid4().hex; folder=settings.data_dir/pid; folder.mkdir()
    try:
        size=0
        with (folder/'source').open('wb') as out:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>settings.max_upload_mb*1024*1024: raise HTTPException(413,'upload_too_large')
                out.write(chunk)
        with (folder/'source').open('rb') as header_file: header=header_file.read(32)
        if not (header[:4]==b'\x1a\x45\xdf\xa3' or header[4:8] in (b'ftyp',b'moov',b'mdat',b'wide',b'free')):
            raise HTTPException(422,'not_a_video')
        try: metadata=await run_in_threadpool(probe,folder/'source')
        except Exception: raise HTTPException(422,'not_a_video') from None
        if metadata['duration']>settings.max_duration_seconds: raise HTTPException(422,'video_too_long')
        now=time.time()
        with connect() as db:
            db.lock()
            pending=db.execute("SELECT COUNT(*) FROM projects WHERE user_id=? AND status IN ('queued','analyzing','rendering')",(user['id'],)).fetchone()[0]
            if pending>=3: raise HTTPException(429,'too_many_jobs')
            db.execute('INSERT INTO projects(id,user_id,title,brief,language,aspect,auto_render,generative,budget,status,stage,metadata,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
             (pid,user['id'],title.strip() or Path(file.filename or 'Untitled video').stem[:120],brief,language,aspect,int(auto_render),int(generative),budget,'queued','queued',json.dumps(metadata),now,now))
            enqueue(db,pid,'analyze')
    except Exception:
        shutil.rmtree(folder,ignore_errors=True)
        raise
    finally: await file.close()
    return project(pid,user['id'])

@app.post('/api/projects/{pid}/render')
def render_project(pid:str,body:RenderRequest,request:Request,user=Depends(current_user)):
    rate_limit(request,'render',12,3600)
    p=project(pid,user['id'])
    if not p: raise HTTPException(404,'not_found')
    if p.get('studio'): raise HTTPException(409,'use_director_plan')
    if not p['analysis']: raise HTTPException(409,'analysis_required')
    analysis=Analysis.model_validate(p['analysis'])
    selected=[r for r in analysis.recommendations if r.id in body.recommendations]
    if len(selected)!=len(set(body.recommendations)): raise HTTPException(422,'invalid_recommendation')
    if any(r.action=='generate_broll' for r in selected) and not p['generative']: raise HTTPException(422,'generation_not_enabled')
    if sum(r.action=='generate_broll' for r in selected)>2: raise HTTPException(422,'too_many_generated_clips')
    try: build_timeline(p['metadata']['duration'],selected)
    except ValueError as e: raise HTTPException(422,str(e)) from None
    with connect() as db:
        db.lock()
        if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')",(pid,)).fetchone(): raise HTTPException(409,'job_already_running')
        enqueue(db,pid,'render',body.model_dump())
        db.execute("UPDATE projects SET status='queued',stage='render_queued',progress=0,error=NULL,updated=? WHERE id=?",(time.time(),pid))
    return {'ok':True}

@app.post('/api/projects/{pid}/retry')
def retry(pid:str,request:Request,user=Depends(current_user)):
    rate_limit(request,'retry',5,3600)
    with connect() as db:
        db.lock()
        p=db.execute("SELECT * FROM projects WHERE id=? AND user_id=? AND status='failed'",(pid,user['id'])).fetchone()
        if not p: raise HTTPException(409,'retry_unavailable')
        if p['analysis']: raise HTTPException(409,'choose_render_again')
        is_studio=db.execute('SELECT 1 FROM studio_projects WHERE project_id=?',(pid,)).fetchone()
        enqueue(db,pid,'studio_analyze' if is_studio else 'analyze')
        db.execute("UPDATE projects SET status='queued',stage='queued',progress=0,error=NULL WHERE id=?",(pid,))
    return {'ok':True}

@app.get('/api/projects/{pid}/media/{kind}')
def media_file(pid:str,kind:str,user=Depends(current_user)):
    p=project(pid,user['id'])
    if not p: raise HTTPException(404,'not_found')
    files={'source':('analysis.mp4','video/mp4'),'original':('source','application/octet-stream'),'poster':('poster.jpg','image/jpeg'),
           'result':('result.mp4','video/mp4'),'captions':('captions.ass','text/plain')}
    if kind not in files: raise HTTPException(404,'not_found')
    if kind in ('result','captions') and not p['result']: raise HTTPException(404,'not_ready')
    name,mime=files[kind]
    folder=settings.data_dir/pid
    if kind in ('result','captions'):
        render_id=p['result'].get('render_id','')
        if not re.fullmatch(r'[a-f0-9]{32}',render_id): raise HTTPException(404,'not_ready')
        folder=folder/'renders'/render_id
    path=folder/name
    if not path.is_file(): raise HTTPException(404,'not_ready')
    return FileResponse(path,media_type=mime,filename=('lumen-'+pid[:8]+'.mp4') if kind=='result' else None,
                        content_disposition_type='inline' if kind not in ('original','captions') else 'attachment')

@app.delete('/api/projects/{pid}')
def delete_project(pid:str,user=Depends(current_user)):
    with connect() as db:
        db.lock()
        p=db.execute('SELECT * FROM projects WHERE id=? AND user_id=?',(pid,user['id'])).fetchone()
        if not p: raise HTTPException(404,'not_found')
        if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')",(pid,)).fetchone(): raise HTTPException(409,'job_already_running')
        # Keep cost accounting after deleting media, to prevent budget bypass.
        db.execute('UPDATE spend SET project_id=NULL WHERE project_id=?',(pid,))
        db.execute('DELETE FROM projects WHERE id=?',(pid,))
    shutil.rmtree(settings.data_dir/pid,ignore_errors=True)
    return {'ok':True}

from .studio import router as studio_router
app.include_router(studio_router)
from .manual import router as manual_router
app.include_router(manual_router)
from .creative_plans import router as creative_plans_router
app.include_router(creative_plans_router)
from .timeline_proposals import router as timeline_proposals_router
app.include_router(timeline_proposals_router)
from .variants import router as variants_router
from . import variant_revisions
app.include_router(variants_router)

from .director_revisions import router as director_revisions_router
app.include_router(director_revisions_router)

from .uploads import router as uploads_router
app.include_router(uploads_router)

@app.api_route('/',methods=['GET','HEAD'])
@app.api_route('/index.html',methods=['GET','HEAD'])
def frontend_entry():
    # Always return the current entry point, including conditional requests.
    # Hashed JS assets stay compatible with already-open tabs.
    return FileResponse(ROOT/'frontend'/'dist'/'index.html',headers={'Cache-Control':'no-store, max-age=0'})

from .assets import router as assets_router
app.include_router(assets_router)
from .music_plans import router as music_plans_router
app.include_router(music_plans_router)
from .stock import router as stock_router
app.include_router(stock_router)

from .dubbing import router as dubbing_router
app.include_router(dubbing_router)

from .soundtracks import router as soundtracks_router
app.include_router(soundtracks_router)

static=ROOT/'frontend'/'dist'
if static.is_dir():
    app.mount('/',StaticFiles(directory=static,html=True),name='web')
