import json
import time
from pathlib import Path
import httpx
import pytest
from backend.tests.test_api import clients
from backend import douyin
from backend.config import settings
from backend.db import connect

def raw(vid='7396640996995370275',duration=21000,likes=12,kind=0):
    return {'aweme_id':vid,'aweme_type':kind,'desc':'Coffee story','author':{'nickname':'Creator'},'create_time':int(time.time()),'statistics':{'digg_count':likes},'video':{'duration':duration,'play_addr':{'url_list':['https://v3-search.douyinvod.com/source.mp4']},'cover':{'url_list':['https://p3-sign.douyinpic.com/cover.jpg']}}}

def test_normalization_filters_and_sorting():
    data={'data':[{'type':1,'aweme_info':raw()}, {'type':6,'aweme_info':raw('7396640996995370276')}, {'type':1,'aweme_info':raw('7396640996995370277',421000)}, {'type':1,'aweme_info':raw('7396640996995370278',kind=68)}, {'type':1,'aweme_info':raw('7396640996995370279',likes=100)}, {'type':1,'aweme_info':raw()}]}
    results=douyin.parse_results(data)
    assert len(results)==2 and results[0]['likes']==100 and results[1]['duration']==21
    old=raw();old['create_time']=int(time.time())-10*86400
    assert not douyin.parse_results({'data':[old]},7)

def test_search_cache_pagination_and_private_results(clients,monkeypatch):
    a,b=clients;calls=[]
    def provider(path,payload):
        calls.append(payload)
        return {'data':[{'type':1,'aweme_info':raw()}],'cursor':12 if payload['cursor']==0 else 24,'has_more':payload['cursor']==0,'log_pb':{'impr_id':'s1'},'backtrace':'trace'}
    monkeypatch.setattr(douyin,'provider',provider)
    body={'keyword':'coffee','sort':'1','publish_time':0}
    r=a.post('/api/douyin/search',json=body);assert r.status_code==200
    data=r.json();rid=data['items'][0]['id'];assert 'media_url' not in data['items'][0] and 'cover_url' not in data['items'][0]
    assert a.post('/api/douyin/search',json=body).json()==data and len(calls)==1
    assert b.post('/api/douyin/import',json={'result_id':rid}).status_code==404
    assert b.get('/api/douyin/results/'+rid+'/cover').status_code==404
    assert b.post('/api/douyin/search',json=body|{'continuation':data['continuation']}).status_code==503
    page=a.post('/api/douyin/search',json=body|{'continuation':data['continuation']});assert page.status_code==200
    assert calls[-1]['cursor']==12 and calls[-1]['search_id']=='s1'
    a.post('/api/logout');assert a.post('/api/douyin/search',json=body).status_code==401

def test_import_idempotent_provenance_queue_retry(clients,monkeypatch):
    a,_=clients
    monkeypatch.setattr(douyin,'provider',lambda *args:{'data':[raw()]})
    rid=a.post('/api/douyin/search',json={'keyword':'coffee'}).json()['items'][0]['id']
    request={'result_id':rid,'language':'zh','brief':'Keep the product clear','auto_render':False}
    r=a.post('/api/douyin/import',json=request);assert r.status_code==201
    p=r.json();assert p['stage']=='importing' and p['source']['aweme_id']==raw()['aweme_id'] and 'media_url' not in p['source']
    assert a.post('/api/douyin/import',json=request).json()['id']==p['id']
    with connect() as db:
        assert db.execute('SELECT COUNT(*) FROM jobs WHERE project_id=?',(p['id'],)).fetchone()[0]==1
        db.execute("UPDATE jobs SET status='failed' WHERE project_id=?",(p['id'],))
        db.execute("UPDATE projects SET status='failed' WHERE id=?",(p['id'],))
    assert a.post('/api/projects/'+p['id']+'/retry').status_code==200
    assert a.post('/api/douyin/import',json=request|{'language':'bad'}).status_code==422

def test_import_checks_selected_identity_before_download(clients,monkeypatch):
    a,_=clients;monkeypatch.setattr(douyin,'provider',lambda *args:{'data':[raw()]})
    rid=a.post('/api/douyin/search',json={'keyword':'coffee'}).json()['items'][0]['id']
    p=a.post('/api/douyin/import',json={'result_id':rid}).json()
    monkeypatch.setattr(douyin,'provider',lambda *args:raw('7396640996995370999'))
    with pytest.raises(douyin.DouyinError):douyin.import_source(p)
    assert not (settings.data_dir/p['id']/'source').exists()

def test_import_source_then_analysis_uses_same_original(clients,monkeypatch):
    import backend.worker as worker
    a,_=clients;monkeypatch.setattr(douyin,'provider',lambda *args:{'data':[raw()]})
    rid=a.post('/api/douyin/search',json={'keyword':'coffee'}).json()['items'][0]['id']
    p=a.post('/api/douyin/import',json={'result_id':rid,'auto_render':False}).json()
    monkeypatch.setattr(douyin,'provider',lambda *args:raw())
    def download(url,path,max_bytes):Path(path).write_bytes(b'original-douyin-bytes')
    monkeypatch.setattr(douyin,'download',download)
    monkeypatch.setattr(worker.media,'probe',lambda path:{'duration':21,'width':320,'height':240,'has_audio':False,'size':21})
    douyin.import_source(p)
    source=settings.data_dir/p['id']/'source';assert source.read_bytes()==b'original-douyin-bytes'
    monkeypatch.setattr(douyin,'download',lambda *args:pytest.fail('retry must reuse completed download'))
    douyin.import_source(p)

@pytest.mark.parametrize('url',['http://127.0.0.1/a','http://169.254.169.254/latest','https://douyinvod.com.evil.example/a','https://user:pass@v3.douyinvod.com/a','file:///etc/passwd','https://v3.douyinvod.com:22/a'])
def test_download_rejects_untrusted_url(url):
    with pytest.raises(douyin.DouyinError):douyin.safe_url(url)

def test_redirect_and_oversize_download_are_rejected(tmp_path,monkeypatch):
    monkeypatch.setattr(douyin.socket,'getaddrinfo',lambda *args,**kwargs:[(2,1,6,'',('8.8.8.8',443))])
    client_class=httpx.Client
    for response in [httpx.Response(302,headers={'location':'http://127.0.0.1/secret'}),httpx.Response(200,content=b'a'*101)]:
        monkeypatch.setattr(douyin.httpx,'Client',lambda **kwargs:client_class(transport=httpx.MockTransport(lambda request:response),**kwargs))
        with pytest.raises(douyin.DouyinError):douyin.download('https://v3.douyinvod.com/a',tmp_path/'video',100)
        assert not (tmp_path/'video').exists()

def test_daily_provider_cap(clients,monkeypatch):
    monkeypatch.setattr(settings,'tikhub_api_key','test')
    monkeypatch.setattr(settings,'tikhub_daily_requests',0)
    with pytest.raises(douyin.DouyinError,match='douyin_daily_limit'):douyin.provider('/unused',{})

@pytest.mark.parametrize('status',[400,404,410])
def test_unavailable_detail_is_not_reported_as_search_failure(clients,monkeypatch,status):
    monkeypatch.setattr(settings,'tikhub_api_key','test-key')
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def request(self,method,url,**kwargs):return httpx.Response(status,request=httpx.Request(method,url))
    monkeypatch.setattr(douyin.httpx,'Client',Client)
    with pytest.raises(douyin.DouyinError,match='douyin_media_unavailable'):
        douyin.provider('/api/v1/douyin/web/fetch_one_video',{'aweme_id':'7309788558154321192'},'GET')

def test_detail_fallback_preserves_identity(monkeypatch):
    calls=[]
    def provider(path,*args):
        calls.append(path)
        if len(calls)==1:raise douyin.DouyinError('douyin_media_unavailable')
        return {'aweme_detail':raw()}
    monkeypatch.setattr(douyin,'provider',provider)
    assert douyin.fetch_video(raw()['aweme_id'])['aweme_id']==raw()['aweme_id']
    assert len(calls)==2 and '/app/v3/' in calls[1]

def test_detail_fallback_does_not_retry_auth_or_accept_other_video(monkeypatch):
    calls=[]
    def provider(*args):
        calls.append(args)
        raise douyin.DouyinError('douyin_auth_failed')
    monkeypatch.setattr(douyin,'provider',provider)
    with pytest.raises(douyin.DouyinError,match='douyin_auth_failed'):douyin.fetch_video(raw()['aweme_id'])
    assert len(calls)==1
    monkeypatch.setattr(douyin,'provider',lambda *args:{'aweme_detail':raw('7396640996995370276')})
    with pytest.raises(douyin.DouyinError,match='douyin_media_unavailable'):douyin.fetch_video(raw()['aweme_id'])
