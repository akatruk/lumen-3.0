"""Reviewed Commons video discovery and bounded private-library imports."""
import json,re,time,uuid,shutil
from html.parser import HTMLParser
from urllib.parse import urlsplit
import httpx
from fastapi import APIRouter,Depends,HTTPException,Request,Query
from typing import Literal
from pydantic import Field
from .schemas import Strict
from .auth import current_user
from .config import settings
from .db import connect,enqueue

router=APIRouter(prefix='/api/studio')
API='https://commons.wikimedia.org/w/api.php'
HEADERS={'User-Agent':'Lumen/2.0 (https://lumen-fix.universalgravity.org; video asset discovery)'}
MAX_BYTES=50*1024*1024

class Plain(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,text):self.parts.append(text)
def plain(value,limit=1000):
    parser=Plain();parser.feed(str(value));return ' '.join(' '.join(parser.parts).split())[:limit]
def safe_media(url):
    try:
        p=urlsplit(url)
        return p.scheme=='https' and p.hostname=='upload.wikimedia.org' and p.port in (None,443) and not p.username and not p.password and p.path.startswith('/wikipedia/commons/')
    except ValueError:return False

def creative_commons(url,prefix):
    try:p=urlsplit(str(url).strip())
    except ValueError:return False
    return p.scheme in ('http','https') and (p.hostname or '').lower()=='creativecommons.org' and p.port in (None,80,443) and not p.username and not p.password and (p.path or '').startswith(prefix)

def query(**params):
    try:
        r=httpx.get(API,params={'action':'query','format':'json','prop':'videoinfo','viprop':'url|size|mime|extmetadata|derivatives',**params},headers=HEADERS,timeout=25)
        r.raise_for_status();data=r.json()
        if not isinstance(data,dict) or 'error' in data:raise ValueError('stock_unavailable')
        body=data.get('query') or {}
        if not isinstance(body,dict):return []
        pages=body.get('pages') or {}
        if isinstance(pages,dict):return list(pages.values())
        return list(pages) if isinstance(pages,list) else []
    except (httpx.HTTPError,ValueError):raise ValueError('stock_unavailable') from None

def _number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)):return None
    return float(value)

def candidate(page):
    # One malformed Commons record must not abort the whole scene search.
    try:
        if not isinstance(page,dict):return None
        info=(page.get('videoinfo') or [{}])[0]
        if not isinstance(info,dict):return None
        meta=info.get('extmetadata') or {}
        if not isinstance(meta,dict):meta={}
        def get(key):
            raw=meta.get(key) or {}
            return plain(raw.get('value','') if isinstance(raw,dict) else '')
        license=get('LicenseShortName');license_url=get('LicenseUrl')
        # Keep the first integration to attribution-only / public-domain licenses.
        by=bool(re.fullmatch(r'CC BY (?:1\.0|2\.0|2\.5|3\.0|4\.0)',license))
        public=license in ('Public domain','CC0','CC0 1.0')
        if not (by or public):return None
        if by and (not creative_commons(license_url,'/licenses/by/') or not get('Artist')):return None
        if public and license_url and not creative_commons(license_url,'/publicdomain/'):return None
        if get('Restrictions') or 'license review needed' in get('Categories').lower():return None
        duration=_number(info.get('duration',0))
        if duration is None or not .1<=duration<=420:return None
        versions=[]
        for derivative in info.get('derivatives') or []:
            if not isinstance(derivative,dict):continue
            height=_number(derivative.get('height'))
            if height is None or not derivative.get('type','').startswith('video/webm') or not safe_media(derivative.get('src','')) or not 240<=height<=1080:continue
            versions.append(derivative)
        if not versions:return None
        chosen=min(versions,key=lambda d:abs(d['height']-720))
        title,page_id=page.get('title'),page.get('pageid')
        if not isinstance(title,str) or isinstance(page_id,bool) or not isinstance(page_id,int):return None
        return {'page_id':page_id,'title':plain(title.removeprefix('File:'),120),'description':get('ImageDescription'),
                'artist':get('Artist'),'license':license,'license_url':license_url,
                'source_url':f'https://commons.wikimedia.org/?curid={page_id}',
                'media_url':chosen['src'],'duration':duration,'width':chosen.get('width'),'height':chosen['height']}
    except (TypeError,ValueError,KeyError,AttributeError):
        return None

def init(db):
    from .stock_discovery import init as init_discovery
    init_discovery(db)
    db.execute('CREATE TABLE IF NOT EXISTS stock_results(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,data TEXT NOT NULL,created REAL NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS stock_imports(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,result_id TEXT NOT NULL,status TEXT NOT NULL,asset_id TEXT,error TEXT,created REAL NOT NULL,UNIQUE(project_id,result_id))')

@router.get('/projects/{pid}/stock/search')
def search(pid:str,request:Request,q:str=Query(min_length=2,max_length=120),user=Depends(current_user)):
    from .studio import owned
    from .app import rate_limit
    owned(pid,user);rate_limit(request,'stock_search',15,3600)
    try:pages=query(generator='search',gsrsearch=q+' filetype:video',gsrnamespace=6,gsrlimit=20)
    except ValueError:raise HTTPException(502,'stock_unavailable') from None
    hits=[]
    with connect() as db:
        db.execute('DELETE FROM stock_results WHERE created<? AND id NOT IN (SELECT result_id FROM stock_imports)',(time.time()-86400,))
        for page in sorted(pages,key=lambda p:p.get('index',0)):
            item=candidate(page)
            if not item:continue
            ident=uuid.uuid4().hex
            db.execute('INSERT INTO stock_results VALUES(?,?,?,?)',(ident,pid,json.dumps(item,ensure_ascii=False),time.time()))
            hits.append({k:v for k,v in item.items() if k!='media_url'}|{'id':ident})
    return hits

class Import(Strict):
    result_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    license_reviewed:Literal[True]

@router.get('/projects/{pid}/stock/imports')
def imports(pid:str,user=Depends(current_user)):
    from .studio import owned
    owned(pid,user)
    with connect() as db:
        rows=[dict(r) for r in db.execute('SELECT i.id,i.result_id,i.status,i.asset_id,i.error,r.data FROM stock_imports i JOIN stock_results r ON r.id=i.result_id WHERE i.project_id=? ORDER BY i.created DESC LIMIT 20',(pid,))]
    for r in rows:r['title']=json.loads(r.pop('data'))['title']
    return rows

@router.post('/projects/{pid}/stock/imports',status_code=202)
def start(pid:str,body:Import,request:Request,user=Depends(current_user)):
    from .studio import owned
    from .app import rate_limit
    owned(pid,user);rate_limit(request,'stock_import',10,3600)
    with connect() as db:
        db.lock()
        row=db.execute('SELECT * FROM stock_results WHERE id=? AND project_id=?',(body.result_id,pid)).fetchone()
        if not row or row['created']<time.time()-86400:raise HTTPException(404,'stock_result_expired')
        old=db.execute('SELECT * FROM stock_imports WHERE project_id=? AND result_id=?',(pid,body.result_id)).fetchone()
        if old and old['status']!='failed':return {'id':old['id']}
        page_id=json.loads(row['data'])['page_id']
        duplicate=next((r['id'] for r in db.execute('SELECT id,metadata FROM studio_assets WHERE project_id=?',(pid,)) if json.loads(r['metadata']).get('provenance',{}).get('page_id')==page_id),None)
        if duplicate:
            ident=old['id'] if old else uuid.uuid4().hex
            if old:db.execute("UPDATE stock_imports SET status='complete',asset_id=?,error=NULL WHERE id=?",(duplicate,ident))
            else:db.execute('INSERT INTO stock_imports VALUES(?,?,?,?,?,?,?)',(ident,pid,body.result_id,'complete',duplicate,None,time.time()))
            return {'id':ident}
        count=db.execute('SELECT count(*) FROM studio_assets WHERE project_id=?',(pid,)).fetchone()[0]
        pending=db.execute("SELECT count(*) FROM stock_imports WHERE project_id=? AND status IN ('queued','running')",(pid,)).fetchone()[0]
        if count+pending>=20:raise HTTPException(422,'asset_limit')
        ident=old['id'] if old else uuid.uuid4().hex
        if old:db.execute("UPDATE stock_imports SET status='queued',error=NULL WHERE id=?",(ident,))
        else:db.execute('INSERT INTO stock_imports VALUES(?,?,?,?,?,?,?)',(ident,pid,body.result_id,'queued',None,None,time.time()))
        enqueue(db,pid,'stock_import',{'id':ident})
    return {'id':ident}

def download(url,target):
    if not safe_media(url):raise ValueError('stock_media_invalid')
    began=time.monotonic();size=0
    with httpx.stream('GET',url,headers=HEADERS,timeout=30,follow_redirects=False) as r:
        if r.status_code!=200:raise ValueError('stock_unavailable')
        if int(r.headers.get('content-length',0))>MAX_BYTES:raise ValueError('stock_media_too_large')
        with target.open('wb') as f:
            for chunk in r.iter_bytes(256*1024):
                size+=len(chunk)
                if size>MAX_BYTES or time.monotonic()-began>120:raise ValueError('stock_media_too_large')
                f.write(chunk)

def import_licensed(pid, item):
    """Save one clip that already passed the CC BY / CC0 / public-domain filter."""
    from . import media
    from .assets import path
    pages = query(pageids=item['page_id'])
    fresh = candidate(pages[0]) if pages else None
    if not fresh or (fresh['license'], fresh['license_url'], fresh['artist']) != (item['license'], item['license_url'], item['artist']):
        raise ValueError('stock_license_changed')
    if shutil.disk_usage(settings.data_dir).free < 1024**3 or sum(f.stat().st_size for f in settings.data_dir.rglob('*') if f.is_file()) > settings.max_storage_gb * 1024**3 - MAX_BYTES:
        raise ValueError('storage_full')
    ident = uuid.uuid4().hex
    folder = settings.data_dir / pid / 'stock' / ident
    folder.mkdir(parents=True, exist_ok=True)
    try:
        source = folder / 'source.webm'
        download(fresh['media_url'], source)
        meta = media.probe(source)
        if not .1 <= meta['duration'] <= 420:
            raise ValueError('stock_media_invalid')
        output = folder / 'asset.mp4'
        media.ffmpeg('-protocol_whitelist', 'file,pipe', '-i', source, '-map', '0:v:0', '-map', '0:a:0?', '-vf', 'scale=1280:1280:force_original_aspect_ratio=decrease:force_divisible_by=2', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', 23, '-c:a', 'aac', '-movflags', '+faststart', output)
        probed = media.probe(output)
        fresh = dict(fresh)
        fresh['approval'] = 'written'
        metadata = probed | {'kind': 'video', 'mime': 'video/mp4', 'provenance': {k: v for k, v in fresh.items() if k != 'media_url'}}
        attribution = f'{fresh["title"]} — {fresh["artist"]}; {fresh["license"]}; {fresh["license_url"]}; {fresh["source_url"]}; converted to MP4; editing may crop or trim.'
        with connect() as db:
            db.lock()
            if db.execute('SELECT count(*) FROM studio_assets WHERE project_id=?', (pid,)).fetchone()[0] >= 20:
                raise ValueError('asset_limit')
            aid = uuid.uuid4().hex
            target = path(pid, aid)
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(output, target)
            db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)', (aid, pid, ident, fresh['title'], attribution, json.dumps(metadata), time.time()))
        return aid, float(probed['duration'])
    finally:
        shutil.rmtree(folder, ignore_errors=True)

def run_job(p,payload):
    from . import media
    from .assets import path
    pid=p['id'];ident=payload['id'];folder=settings.data_dir/pid/'stock'/ident;folder.mkdir(parents=True,exist_ok=True)
    with connect() as db:
        row=db.execute('SELECT * FROM stock_imports WHERE id=? AND project_id=?',(ident,pid)).fetchone()
        stored=json.loads(db.execute('SELECT data FROM stock_results WHERE id=?',(row['result_id'],)).fetchone()[0])
        db.execute("UPDATE stock_imports SET status='running' WHERE id=?",(ident,))
    try:
        pages=query(pageids=stored['page_id']);fresh=candidate(pages[0]) if pages else None
        if not fresh or (fresh['license'],fresh['license_url'],fresh['artist'])!=(stored['license'],stored['license_url'],stored['artist']):raise ValueError('stock_license_changed')
        if shutil.disk_usage(settings.data_dir).free<1024**3 or sum(f.stat().st_size for f in settings.data_dir.rglob('*') if f.is_file())>settings.max_storage_gb*1024**3-MAX_BYTES:raise ValueError('storage_full')
        source=folder/'source.webm';download(fresh['media_url'],source)
        meta=media.probe(source)
        if not .1<=meta['duration']<=420:raise ValueError('stock_media_invalid')
        output=folder/'asset.mp4'
        media.ffmpeg('-protocol_whitelist','file,pipe','-i',source,'-map','0:v:0','-map','0:a:0?','-vf','scale=1280:1280:force_original_aspect_ratio=decrease:force_divisible_by=2','-c:v','libx264','-preset','veryfast','-crf',23,'-c:a','aac','-movflags','+faststart',output)
        metadata=media.probe(output)|{'kind':'video','mime':'video/mp4','provenance':{k:v for k,v in fresh.items() if k!='media_url'}}
        attribution=f'{fresh["title"]} — {fresh["artist"]}; {fresh["license"]}; {fresh["license_url"]}; {fresh["source_url"]}; converted to MP4; editing may crop or trim.'
        with connect() as db:
            db.lock();old=db.execute('SELECT id FROM studio_assets WHERE project_id=? AND request_id=?',(pid,ident)).fetchone()
            aid=old['id'] if old else uuid.uuid4().hex
            if not old:
                if db.execute('SELECT count(*) FROM studio_assets WHERE project_id=?',(pid,)).fetchone()[0]>=20:raise ValueError('asset_limit')
                target=path(pid,aid);target.parent.mkdir(exist_ok=True);shutil.copyfile(output,target)
                db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)',(aid,pid,ident,fresh['title'],attribution,json.dumps(metadata),time.time()))
            db.execute("UPDATE stock_imports SET status='complete',asset_id=? WHERE id=?",(aid,ident))
    except Exception as exc:
        code=str(exc) if str(exc) in {'stock_unavailable','stock_license_changed','stock_media_invalid','stock_media_too_large','asset_limit','storage_full'} else 'stock_import_failed'
        with connect() as db:db.execute("UPDATE stock_imports SET status='failed',error=? WHERE id=?",(code,ident))
        raise ValueError(code) from None
    finally:
        for name in ('source.webm','asset.mp4'):(folder/name).unlink(missing_ok=True)

# Register scene discovery on the same private router.
from . import stock_discovery
