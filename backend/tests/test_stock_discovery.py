import json
from backend.tests.test_studio import client,create,seed_plan,T
from backend.tests.test_stock import page
from backend import stock,stock_discovery,worker,ai
from backend.db import connect,project

def setup(client):
    pid=create(client).json()['id'];seed_plan(pid)
    url=f'/api/studio/projects/{pid}/manual'
    edit=client.get(url).json()['edit']
    revision=client.put(url,json={'revision':1,'edit':edit}).json()['revision']
    return pid,url,edit,revision

def test_scene_discovery_searches_deduplicates_and_preserves_edit(client,monkeypatch):
    pid,url,edit,revision=setup(client);base=f'/api/studio/projects/{pid}/stock'
    plan=stock_discovery.SearchPlan(rationale=T,queries=[{'query':'ocean','purpose':T},{'query':'sea waves','purpose':T}],cautions=[T])
    prompts=[]
    def model(*args,**kw):prompts.append(args[2]);return plan
    monkeypatch.setattr(ai,'json_call',model);queries=[]
    def search(**kw):queries.append(kw['gsrsearch']);return [page()]
    monkeypatch.setattr(stock,'query',search)
    r=client.post(base+'/discover',json={'revision':revision,'clip_id':edit['clips'][0]['id']});assert r.status_code==202,r.text
    assert worker.run_once()
    result=client.get(base+'/discoveries').json()[0]
    assert result['status']=='ready' and not result['stale']
    assert len(queries)==2 and len(result['result']['hits'])==1
    hit=result['result']['hits'][0]
    assert 'media_url' not in hit and hit['purpose']==T
    assert 'transcript' in prompts[0] and 'clip' in prompts[0]
    assert client.get(url).json()['edit']==edit
    assert project(pid)['status']=='ready'
    assert client.post(base+'/imports',json={'result_id':hit['id'],'license_reviewed':True}).status_code==202

def test_discovery_failure_does_not_fail_project(client,monkeypatch):
    pid,url,edit,revision=setup(client);base=f'/api/studio/projects/{pid}/stock'
    def fail(*a,**k):raise ValueError('provider_request_failed')
    monkeypatch.setattr(ai,'json_call',fail)
    assert client.post(base+'/discover',json={'revision':revision,'clip_id':edit['clips'][0]['id']}).status_code==202
    assert worker.run_once()
    assert client.get(base+'/discoveries').json()[0]['status']=='failed'
    assert project(pid)['status']=='ready'
    assert client.get(url).json()['edit']==edit

def test_discovery_rejects_stale_locked_and_foreign_scene(client):
    pid,url,edit,revision=setup(client);base=f'/api/studio/projects/{pid}/stock'
    body={'revision':revision,'clip_id':edit['clips'][0]['id']}
    assert client.post(base+'/discover',json=body|{'revision':1}).status_code==409
    assert client.post(base+'/discover',json=body|{'clip_id':'unknown'}).status_code==422
    edit['clips'][0]['locked']=True
    saved=client.put(url,json={'revision':revision,'edit':edit}).json()
    assert client.post(base+'/discover',json=body|{'revision':saved['revision']}).status_code==409
    from backend.app import app
    from backend.auth import current_user
    app.dependency_overrides[current_user]=lambda:{'id':'other','email':'other@example.com'}
    assert client.get(base+'/discoveries').status_code==404
    assert client.post(base+'/discover',json=body).status_code==404
