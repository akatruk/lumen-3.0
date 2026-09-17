"""Douyin discovery through TikHub. Clients never supply download URLs."""
import hashlib
import ipaddress
import json
import re
import socket
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse,urljoin
import httpx
from .config import settings
from .db import connect

SEARCH_PATH='/api/v1/douyin/search/fetch_general_search_v1'
MEDIA_HOSTS=('douyinvod.com','douyin.com','byteimg.com','bytecdn.cn','ibytedtos.com','pstatp.com','ixigua.com','douyinpic.com','bytedance.com','bytednsdoc.com','zjcdn.com','snssdk.com')

class DouyinError(ValueError): pass

def safe_url(url):
    p=urlparse(url)
    host=(p.hostname or '').lower()
    if p.scheme not in ('http','https') or p.username or p.password or p.port not in (None,80,443): raise DouyinError('douyin_media_unavailable')
    if not any(host==d or host.endswith('.'+d) for d in MEDIA_HOSTS): raise DouyinError('douyin_media_unavailable')
    try:
        addresses=socket.getaddrinfo(host,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses): raise DouyinError('douyin_media_unavailable')
    except OSError: raise DouyinError('douyin_media_unavailable') from None
    return url

def provider(path,payload,method='POST'):
    if not settings.tikhub_api_key: raise DouyinError('douyin_not_configured')
    base=settings.tikhub_base_url.rstrip('/')
    if base not in ('https://api.tikhub.io','https://api.tikhub.dev'): raise DouyinError('douyin_not_configured')
    with connect() as db:
        db.lock()
        if db.execute('SELECT COUNT(*) FROM tikhub_calls WHERE created>?',(time.time()-86400,)).fetchone()[0]>=settings.tikhub_daily_requests:
            raise DouyinError('douyin_daily_limit')
        db.execute('INSERT INTO tikhub_calls(created) VALUES(?)',(time.time(),))
    try:
        with httpx.Client(timeout=45) as client:
            r=client.request(method,base+path,headers={'Authorization':'Bearer '+settings.tikhub_api_key,'User-Agent':'Lumen/1.0','Accept':'application/json'},**({'json':payload} if method=='POST' else {'params':payload}))
        if r.status_code in (401,403): raise DouyinError('douyin_auth_failed')
        if r.status_code==402: raise DouyinError('douyin_credits_required')
        if r.status_code==429: raise DouyinError('douyin_rate_limited')
        if path.endswith('/fetch_one_video') and r.status_code in (400,404,410):
            raise DouyinError('douyin_media_unavailable')
        r.raise_for_status();data=r.json()
        if data.get('code',200)!=200: raise DouyinError('douyin_search_failed')
        inner=data.get('data') or {}
        if isinstance(inner,dict) and inner.get('status_code',0) not in (0,None):raise DouyinError('douyin_search_failed')
        return inner
    except (httpx.HTTPError,ValueError) as e:
        if isinstance(e,DouyinError): raise
        raise DouyinError('douyin_search_failed') from None

def fetch_video(aweme_id):
    """Bounded fallback for the same identity; never retry auth/credit failures."""
    for endpoint in ('/api/v1/douyin/web/fetch_one_video','/api/v1/douyin/app/v3/fetch_one_video_v2'):
        try:
            raw=provider(endpoint,{'aweme_id':aweme_id},'GET')
            video=normalize(raw.get('aweme_detail') or raw)
            if video and video['aweme_id']==aweme_id and video['media_url']:
                return video
            raise DouyinError('douyin_media_unavailable')
        except DouyinError as exc:
            if str(exc) not in ('douyin_media_unavailable','douyin_search_failed'):
                raise
    raise DouyinError('douyin_media_unavailable')

def first_url(value):
    if isinstance(value,str):return value
    if isinstance(value,dict):
        urls=value.get('url_list') or []
        return next((u for u in urls if isinstance(u,str) and u.startswith(('https://','http://'))),'')
    return ''

def normalize(raw):
    if not isinstance(raw,dict) or raw.get('aweme_type',0)!=0 or raw.get('is_ads'): return None
    video=raw.get('video') or {}
    if not video or (raw.get('images') and not first_url(video.get('play_addr'))):return None
    vid=str(raw.get('aweme_id',''))
    if not re.fullmatch(r'\d{10,25}',vid):return None
    duration=float(video.get('duration') or raw.get('duration') or 0)/1000
    stats=raw.get('statistics') or {};author=raw.get('author') or {}
    media=first_url(video.get('play_addr')) or first_url(video.get('play_addr_h264')) or first_url(video.get('download_addr'))
    if media.split('?',1)[0].lower().endswith('.mp3'):return None
    return {'aweme_id':vid,'title':str(raw.get('desc') or 'Douyin video')[:1000], 'author':str(author.get('nickname') or ''),
            'duration':duration,'likes':int(stats.get('digg_count') or 0),'comments':int(stats.get('comment_count') or 0),
            'published_at':int(raw.get('create_time') or 0),'share_url':'https://www.douyin.com/video/'+vid,
            'cover_url':first_url(video.get('cover')) or first_url(video.get('origin_cover')),'media_url':media}

def parse_results(inner,publish_time=0,sort='1'):
    raw_items=inner if isinstance(inner,list) else inner.get('data') or inner.get('aweme_list') or inner.get('item_list') or []
    results=[];seen=set();cutoff=time.time()-publish_time*86400 if publish_time else 0
    for item in raw_items:
        if not isinstance(item,dict) or item.get('type',1)!=1:continue
        raw=item.get('aweme_info') or item
        try:video=normalize(raw)
        except (TypeError,ValueError):continue
        if not video or video['aweme_id'] in seen:continue
        if video['duration']>settings.max_duration_seconds:continue
        if cutoff and video['published_at'] and video['published_at']<cutoff:continue
        seen.add(video['aweme_id']);results.append(video)
    if sort=='1':results.sort(key=lambda v:v['likes'],reverse=True)
    if sort=='2':results.sort(key=lambda v:v['published_at'],reverse=True)
    return results[:30]

def search(user_id,keyword,sort,publish_time,continuation=''):
    cursor=0;search_id='';backtrace='';parent=''
    if continuation:
        with connect() as db: row=db.execute('SELECT * FROM douyin_searches WHERE id=? AND user_id=? AND created>?',(continuation,user_id,time.time()-1800)).fetchone()
        if not row:raise DouyinError('douyin_search_expired')
        previous=json.loads(row['data']);n=previous['next']
        if not n:raise DouyinError('douyin_search_expired')
        keyword=previous['keyword'];sort=previous['sort'];publish_time=previous['publish_time']
        cursor=n['cursor'];search_id=n['search_id'];backtrace=n['backtrace'];parent=continuation
    cache_key=hashlib.sha256(json.dumps([keyword,sort,publish_time,parent],ensure_ascii=False).encode()).hexdigest()
    with connect() as db:
        cached=db.execute('SELECT data FROM douyin_searches WHERE user_id=? AND cache_key=? AND created>? ORDER BY created DESC LIMIT 1',(user_id,cache_key,time.time()-300)).fetchone()
    if cached:return public_search(json.loads(cached['data']))
    inner=provider(SEARCH_PATH,{'keyword':keyword,'cursor':cursor,'sort_type':sort,'publish_time':str(publish_time),'filter_duration':'0','content_type':'1','search_id':search_id,'backtrace':backtrace})
    videos=parse_results(inner,publish_time,sort);sid=uuid.uuid4().hex
    more=None
    if isinstance(inner,dict) and inner.get('has_more') and inner.get('cursor') is not None and inner.get('cursor')!=cursor:
        log_pb=inner.get('log_pb') or {}
        more={'cursor':inner['cursor'],'search_id':inner.get('search_id') or log_pb.get('impr_id') or search_id,'backtrace':inner.get('backtrace') or ''}
    result={'id':sid,'keyword':keyword,'sort':sort,'publish_time':publish_time,'items':[], 'next':more,'continuation':sid if more else None}
    with connect() as db:
        for v in videos:
            rid=uuid.uuid4().hex
            db.execute('INSERT INTO douyin_results VALUES(?,?,?,?)',(rid,user_id,json.dumps(v,ensure_ascii=False),time.time()))
            result['items'].append(dict(v,id=rid))
        db.execute('INSERT INTO douyin_searches VALUES(?,?,?,?,?)',(sid,user_id,cache_key,json.dumps(result,ensure_ascii=False),time.time()))
    return public_search(result)

def public_search(result):
    return {'keyword':result['keyword'],'continuation':result['continuation'],'items':[{k:v for k,v in item.items() if k not in ('media_url','cover_url')}|{'cover':f"/api/douyin/results/{item['id']}/cover" if item.get('cover_url') else None} for item in result['items']]}

def owned_result(result_id,user_id):
    with connect() as db:row=db.execute('SELECT data FROM douyin_results WHERE id=? AND user_id=? AND created>?',(result_id,user_id,time.time()-3600)).fetchone()
    if not row:raise DouyinError('douyin_search_expired')
    return json.loads(row['data'])

def download(url,path,max_bytes):
    # Only server-returned Douyin CDN URLs are eligible, including every redirect.
    with httpx.Client(timeout=httpx.Timeout(30,connect=10),follow_redirects=False) as client:
        deadline=time.monotonic()+150
        for _ in range(6):
            safe_url(url)
            with client.stream('GET',url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.douyin.com/'}) as r:
                if r.status_code in (301,302,303,307,308):
                    url=urljoin(url,r.headers.get('location',''));continue
                if r.status_code!=200:raise DouyinError('douyin_media_unavailable')
                if int(r.headers.get('content-length',0))>max_bytes:raise DouyinError('upload_too_large')
                total=0
                try:
                    with Path(path).open('wb') as out:
                        for chunk in r.iter_bytes(65536):
                            total+=len(chunk)
                            if total>max_bytes:raise DouyinError('upload_too_large')
                            if time.monotonic()>deadline:raise DouyinError('douyin_media_unavailable')
                            out.write(chunk)
                    if total==0:raise DouyinError('douyin_media_unavailable')
                    return r.headers.get('content-type','')
                except Exception:
                    Path(path).unlink(missing_ok=True);raise
    raise DouyinError('douyin_media_unavailable')

def import_source(p):
    from . import media
    from .db import update,event
    folder=settings.data_dir/p['id'];folder.mkdir(exist_ok=True)
    if (folder/'source').exists():return
    with connect() as db:row=db.execute('SELECT data FROM project_sources WHERE project_id=?',(p['id'],)).fetchone()
    if not row:raise DouyinError('douyin_media_unavailable')
    source=json.loads(row['data'])
    update(p['id'],stage='importing',progress=3)
    # Refresh temporary playback URLs using the selected immutable Douyin ID.
    detail=provider('/api/v1/douyin/web/fetch_one_video',{'aweme_id':source['aweme_id']},'GET')
    raw=detail.get('aweme_detail') or detail
    refreshed=normalize(raw)
    if not refreshed or refreshed['aweme_id']!=source['aweme_id']:raise DouyinError('douyin_media_unavailable')
    if refreshed['duration']>settings.max_duration_seconds:raise DouyinError('video_too_long')
    temporary=folder/'source.download'
    try:
        download(refreshed['media_url'],temporary,settings.max_upload_mb*1024*1024)
        metadata=media.probe(temporary)
        if metadata['duration']>settings.max_duration_seconds:raise DouyinError('video_too_long')
        temporary.replace(folder/'source')
        update(p['id'],metadata=metadata)
        event(p['id'],'imported_from_douyin',source['share_url'])
    finally:temporary.unlink(missing_ok=True)
