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
    def model(*args,**kw):
        prompts.append(args[2])
        if args[4]=='stock_ranking':
            from backend.stock_ranking import Ranking,CandidateReview
            return Ranking(reviews=[CandidateReview(page_id=page()['pageid'],score=85,suitability='illustration',reason=T)])
        return plan
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
    assert hit['relevance']['score']==85 and result['result']['ranking_status']=='complete'
    assert len(prompts)==2
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
    item=client.get(base+'/discoveries').json()[0]
    assert item['status']=='failed' and item['error']=='provider_request_failed'
    assert project(pid)['status']=='ready'
    assert client.get(url).json()['edit']==edit

def test_malformed_commons_page_does_not_fail_scene_search(client,monkeypatch):
    pid,url,edit,revision=setup(client);base=f'/api/studio/projects/{pid}/stock'
    bad=page();bad['pageid']=13;bad['videoinfo'][0]['duration']=None
    def model(*args,**kwargs):
        if args[4]=='stock_ranking':
            from backend.stock_ranking import Ranking,CandidateReview
            return Ranking(reviews=[CandidateReview(page_id=page()['pageid'],score=80,suitability='illustration',reason=T)])
        return stock_discovery.SearchPlan(rationale=T,queries=[{'query':'ocean','purpose':T}],cautions=[])
    monkeypatch.setattr(ai,'json_call',model)
    monkeypatch.setattr(stock,'query',lambda **kw:[bad,page()])
    assert client.post(base+'/discover',json={'revision':revision,'clip_id':edit['clips'][0]['id']}).status_code==202
    assert worker.run_once()
    item=client.get(base+'/discoveries').json()[0]
    assert item['status']=='ready',item
    assert [hit['page_id'] for hit in item['result']['hits']]==[page()['pageid']]
    assert client.get(url).json()['edit']==edit

def test_scene_search_keeps_twenty_four_candidates_and_writes_nothing_for_an_empty_plan(client,monkeypatch):
    pid,url,edit,revision=setup(client);base=f'/api/studio/projects/{pid}/stock'
    pages=[]
    for n in range(25):
        item=page();item['pageid']=100+n;item['title']=f'File:Clip{n}.webm';pages.append(item)
    seen=[]
    def fake_rank(pid,snapshot,items):
        seen.append(len(items));return items[:1]
    monkeypatch.setattr(ai,'json_call',lambda *a,**k:stock_discovery.SearchPlan(rationale=T,queries=[{'query':'ocean','purpose':T}],cautions=[]))
    monkeypatch.setattr(stock,'query',lambda **kw:pages)
    monkeypatch.setattr('backend.stock_ranking.rank',fake_rank)
    assert client.post(base+'/discover',json={'revision':revision,'clip_id':edit['clips'][0]['id']}).status_code==202
    assert worker.run_once()
    item=client.get(base+'/discoveries').json()[0]
    assert item['status']=='ready' and seen==[24],item
    assert client.get(url).json()['edit']==edit
    with connect() as db:before=db.execute('SELECT COUNT(*) FROM stock_results WHERE project_id=?',(pid,)).fetchone()[0]
    assert before==1
    monkeypatch.setattr(ai,'json_call',lambda *a,**k:stock_discovery.SearchPlan(rationale=T,queries=[],cautions=[T]))
    revision=client.get(url).json()['revision']
    assert client.post(base+'/discover',json={'revision':revision,'clip_id':edit['clips'][0]['id']}).status_code==202
    assert worker.run_once()
    second=client.get(base+'/discoveries').json()[0]
    assert second['status']=='ready' and second['result']['hits']==[] and second['result']['queries']==[]
    with connect() as db:assert db.execute('SELECT COUNT(*) FROM stock_results WHERE project_id=?',(pid,)).fetchone()[0]==before

def test_missing_scene_proxy_plans_without_failing(client,monkeypatch):
    pid,url,edit,revision=setup(client);base=f'/api/studio/projects/{pid}/stock'
    calls=[]
    def model(*args,**kwargs):
        calls.append(kwargs)
        return stock_discovery.SearchPlan(rationale=T,queries=[],cautions=[])
    monkeypatch.setattr(ai,'json_call',model)
    assert client.post(base+'/discover',json={'revision':revision,'clip_id':edit['clips'][0]['id']}).status_code==202
    assert worker.run_once()
    item=client.get(base+'/discoveries').json()[0]
    assert item['status']=='ready' and calls[0]['attach_video'] is False and item['result']['hits']==[]
    with connect() as db:assert db.execute('SELECT COUNT(*) FROM stock_results WHERE project_id=?',(pid,)).fetchone()[0]==0
    assert client.get(url).json()['edit']==edit

def test_commons_outage_names_the_failure_and_writes_nothing(client,monkeypatch):
    pid,url,edit,revision=setup(client);base=f'/api/studio/projects/{pid}/stock'
    monkeypatch.setattr(ai,'json_call',lambda *a,**k:stock_discovery.SearchPlan(rationale=T,queries=[{'query':'ocean','purpose':T}],cautions=[]))
    monkeypatch.setattr(stock,'query',lambda **kw:(_ for _ in ()).throw(ValueError('stock_unavailable')))
    assert client.post(base+'/discover',json={'revision':revision,'clip_id':edit['clips'][0]['id']}).status_code==202
    assert worker.run_once()
    item=client.get(base+'/discoveries').json()[0]
    assert item['status']=='failed' and item['error']=='stock_unavailable' and item['result'] is None
    with connect() as db:assert db.execute('SELECT COUNT(*) FROM stock_results WHERE project_id=?',(pid,)).fetchone()[0]==0
    assert client.get(url).json()['edit']==edit
    assert project(pid)['status']=='ready'

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


def test_ranking_failure_returns_explicit_unranked_results(client,monkeypatch):
    pid,url,edit,revision=setup(client);base=f'/api/studio/projects/{pid}/stock'
    def model(*args,**kwargs):
        if args[4]=='stock_ranking':raise ValueError('budget_limit')
        return stock_discovery.SearchPlan(rationale=T,queries=[{'query':'ocean','purpose':T}],cautions=[])
    monkeypatch.setattr(ai,'json_call',model)
    monkeypatch.setattr(stock,'query',lambda **kw:[page()])
    assert client.post(base+'/discover',json={'revision':revision,'clip_id':edit['clips'][0]['id']}).status_code==202
    assert worker.run_once()
    result=client.get(base+'/discoveries').json()[0]['result']
    assert result['ranking_status']=='unavailable' and len(result['hits'])==1
    assert 'relevance' not in result['hits'][0]
    assert client.get(url).json()['edit']==edit


def test_all_candidates_can_be_rejected_without_changing_edit(client,monkeypatch):
    from backend.stock_ranking import Ranking,CandidateReview
    pid,url,edit,revision=setup(client);base=f'/api/studio/projects/{pid}/stock'
    def model(*args,**kwargs):
        if args[4]=='stock_ranking':return Ranking(reviews=[CandidateReview(page_id=page()['pageid'],score=0,suitability='reject',reason=T)])
        return stock_discovery.SearchPlan(rationale=T,queries=[{'query':'ocean','purpose':T}],cautions=[])
    monkeypatch.setattr(ai,'json_call',model);monkeypatch.setattr(stock,'query',lambda **kw:[page()])
    client.post(base+'/discover',json={'revision':revision,'clip_id':edit['clips'][0]['id']});assert worker.run_once()
    result=client.get(base+'/discoveries').json()[0]['result']
    assert result['ranking_status']=='complete' and result['excluded_count']==1 and not result['hits']
    assert client.get(url).json()['edit']==edit
