import json
from backend.tests.test_studio import client,create,seed_plan,plan
from backend import director_revisions as dr
from backend.db import connect,project
from backend.worker import run_once
from backend.app import app
from backend.auth import current_user

def setup(client):
 pid=create(client).json()['id'];seed_plan(pid)
 with connect() as db:
  db.execute('UPDATE projects SET metadata=? WHERE id=?',(json.dumps(dict(duration=40,has_audio=False)),pid))
  db.execute('UPDATE studio_projects SET dna=? WHERE project_id=?',(json.dumps([dict(reference_id='1234567890123456789',duration=20)]),pid))
 return pid

def test_propose_accept_and_preserve(client,monkeypatch):
 pid=setup(client);base='/api/studio/projects/'+pid;before=client.get(base).json()
 alt=dr.Alternative(recommendation=plan().recommendations[0],transfer=plan().transfers[0]);alt.recommendation.start=3
 monkeypatch.setattr(dr.ai,'json_call',lambda *a,**k:alt)
 r=client.post(base+'/alternatives',json=dict(revision=1,recommendation_id='cut',instruction='Shorter cut'));assert r.status_code==202
 assert client.post(base+'/alternatives',json=dict(revision=1,recommendation_id='cut',instruction='Again')).status_code==409
 assert run_once()
 assert client.get(base).json()==before
 items=client.get(base+'/alternatives').json();assert items[0]['status']=='ready'
 r=client.post(base+'/alternatives/'+items[0]['id']+'/accept',json={'revision':1});assert r.status_code==200
 assert r.json()['revision']==2 and r.json()['decisions'][0]['start']==3 and not r.json()['decisions'][0]['approved']
 assert client.post(base+'/alternatives/'+items[0]['id']+'/accept',json={'revision':1}).status_code==409
 app.dependency_overrides[current_user]=lambda:dict(id='other')
 assert client.get(base+'/alternatives').status_code==404

def test_failure_and_locked(client,monkeypatch):
 pid=setup(client);base='/api/studio/projects/'+pid
 ds=client.get(base).json()['decisions'];ds[0].update(approved=True,locked=True)
 assert client.put(base+'/plan',json=dict(revision=1,decisions=ds)).status_code==200
 assert client.post(base+'/alternatives',json=dict(revision=2,recommendation_id='cut',instruction='Change')).status_code==409
 ds[0]['locked']=False;client.put(base+'/plan',json=dict(revision=2,decisions=ds))
 before=client.get(base).json()
 def fail(*a,**k):raise ValueError('provider_request_failed')
 monkeypatch.setattr(dr.ai,'json_call',fail)
 assert client.post(base+'/alternatives',json=dict(revision=3,recommendation_id='cut',instruction='Change')).status_code==202
 run_once()
 assert client.get(base).json()==before
 assert project(pid)['status']=='ready'
 assert client.get(base+'/alternatives').json()[0]['status']=='failed'

def test_preserves_other_approved_decisions_and_rejects_stale(client,monkeypatch):
 pid=setup(client);base='/api/studio/projects/'+pid
 with connect() as db:
  s=dr.state(pid,db);other=dict(s['plan']['recommendations'][0],id='other',start=8,end=9)
  s['plan']['recommendations'].append(other)
  s['plan']['transfers'].append(dict(s['plan']['transfers'][0],recommendation_id='other'))
  saved=dict(id='other',start=8,end=9,approved=True,locked=True);s['decisions'].append(saved)
  db.execute('UPDATE studio_projects SET plan=?,decisions=? WHERE project_id=?',(json.dumps(s['plan']),json.dumps(s['decisions']),pid))
 alt=dr.Alternative(recommendation=plan().recommendations[0],transfer=plan().transfers[0]);alt.recommendation.start=3
 monkeypatch.setattr(dr.ai,'json_call',lambda *a,**k:alt)
 client.post(base+'/alternatives',json=dict(revision=1,recommendation_id='cut',instruction='Shorter'))
 run_once();item=client.get(base+'/alternatives').json()[0]
 result=client.post(base+'/alternatives/'+item['id']+'/accept',json={'revision':1}).json()
 assert result['decisions'][1]==saved and result['plan']['recommendations'][1]==other
 client.post(base+'/alternatives',json=dict(revision=2,recommendation_id='cut',instruction='Another'))
 run_once();item=client.get(base+'/alternatives').json()[0]
 client.put(base+'/plan',json=dict(revision=2,decisions=result['decisions']))
 assert client.post(base+'/alternatives/'+item['id']+'/accept',json={'revision':2}).status_code==409

def test_rejects_speech_cut(client):
 import pytest
 pid=setup(client);s=dr.state(pid)
 s['plan']['transcript']=[dict(start=1,end=5,original='Complete phrase',en='Complete phrase',zh='完整句子')]
 alt=dr.Alternative(recommendation=plan().recommendations[0],transfer=plan().transfers[0])
 with pytest.raises(ValueError,match='analysis_timestamps_invalid'):dr.merged(s,alt,'cut',dict(duration=40))
