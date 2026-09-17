import json,time,uuid
import pytest
from fastapi.testclient import TestClient
from backend.app import app,limits
from backend.auth import current_user
from backend.config import settings
from backend.db import connect,project
from backend import studio

T={'en':'A measured change','zh':'调整'}
def plan():
 return studio.Director(summary=T,strongest_moment=T,audience=T,scores=[dict(category='clarity',value=50,reason=T)],scenes=[dict(start=0,end=40,title=T,observation=T,role='context')],transcript=[],recommendations=[dict(id='cut',start=2,end=4,title=T,evidence=T,improvement=T,category='pacing',confidence=.7,auto_apply=False,action='remove',generation_prompt='')],uncertainties=[],transfers=[dict(recommendation_id='cut',reference_id='1234567890123456789',reference_start=0,reference_end=2,method=T,fit=T)])

@pytest.fixture
def client(tmp_path,monkeypatch):
 monkeypatch.setattr(settings,'data_dir',tmp_path);limits.clear()
 app.dependency_overrides[current_user]=lambda:{'id':'u','email':'test@example.com'}
 with TestClient(app) as c:
  with connect() as db:
   db.execute('INSERT INTO users VALUES(?,?,?,?)',('u','test@example.com','disabled',time.time()))
   db.execute('INSERT INTO users VALUES(?,?,?,?)',('v','other@example.com','disabled',time.time()))
   ref=dict(aweme_id='1234567890123456789',title='Reference',author='Author',share_url='https://www.douyin.com/video/1234567890123456789',duration=20)
   db.execute('INSERT INTO douyin_results VALUES(?,?,?,?)',('a'*32,'u',json.dumps(ref),time.time()))
  monkeypatch.setattr(studio.media,'probe',lambda _:dict(duration=40,width=320,height=568,has_audio=False,size=16))
  yield c
 app.dependency_overrides.clear()

def create(c,**overrides):
 config=dict(request_id=uuid.uuid4().hex,references=['a'*32],title='Owned project',script='My original script',creator=dict(topic='travel',audience='Families',tone='Calm',rules='No invented claims'),owned_rights_confirmed=True,language='zh',budget=5)
 config.update(overrides)
 return c.post('/api/studio/projects',data={'config':json.dumps(config)},files={'file':('owned.mp4',b'owned-source-only','video/mp4')})

def seed_plan(pid):
 p=plan()
 ds=[dict(id='cut',approved=False,locked=False,start=2,end=4)]
 with connect() as db:
  db.execute("UPDATE jobs SET status='complete' WHERE project_id=?",(pid,))
  db.execute('UPDATE studio_projects SET plan=?,decisions=?,revision=1 WHERE project_id=?',(p.model_dump_json(),json.dumps(ds),pid))
  db.execute("UPDATE projects SET analysis=?,status='ready' WHERE id=?",(json.dumps(p.model_dump(exclude={'transfers'})),pid))
 return ds

def test_roles_and_validation(client,monkeypatch):
 assert create(client,owned_rights_confirmed=False).status_code==422
 assert create(client,references=[]).status_code==422
 assert create(client,references=['b'*32]).status_code==422
 r=create(client);assert r.status_code==201
 pid=r.json()['id'];assert r.json()['studio'] is True
 s=client.get('/api/studio/projects/'+pid).json()
 assert s['context']['references'][0]['role']=='reference_only'
 assert s['context']['platforms']==['douyin','instagram_reels','youtube_shorts','tiktok','xiaohongshu']
 assert (settings.data_dir/pid/'source').read_bytes()==b'owned-source-only'
 with connect() as db:assert db.execute('SELECT kind FROM jobs WHERE project_id=?',(pid,)).fetchone()[0]=='studio_analyze'
 app.dependency_overrides[current_user]=lambda:{'id':'v','email':'other@example.com'}
 assert client.get('/api/studio/projects/'+pid).status_code==404
 assert client.get('/api/studio/projects/'+pid+'/references/1234567890123456789').status_code==404

def test_revision_lock_and_render_snapshot(client):
 pid=create(client).json()['id'];ds=seed_plan(pid)
 assert client.post('/api/projects/'+pid+'/render',json={'recommendations':['cut']}).status_code==409
 assert client.post('/api/studio/projects/'+pid+'/render',json={'revision':1}).status_code==422
 ds[0].update(approved=True,locked=True)
 r=client.put('/api/studio/projects/'+pid+'/plan',json={'revision':1,'decisions':ds});assert r.status_code==200
 assert r.json()['revision']==2
 assert client.put('/api/studio/projects/'+pid+'/plan',json={'revision':1,'decisions':ds}).status_code==409
 ds[0]['end']=5
 assert client.put('/api/studio/projects/'+pid+'/plan',json={'revision':2,'decisions':ds}).status_code==409
 ds[0]['end']=4
 assert client.post('/api/studio/projects/'+pid+'/render',json={'revision':2}).status_code==200
 assert client.post('/api/studio/projects/'+pid+'/render',json={'revision':2}).status_code==409
 assert client.put('/api/studio/projects/'+pid+'/plan',json={'revision':2,'decisions':ds}).status_code==409
 with connect() as db:
  payload=json.loads(db.execute("SELECT payload FROM jobs WHERE kind='studio_render'").fetchone()[0])
 assert payload['revision']==2 and payload['decisions'][0]['locked']

def test_director_evidence_validation():
 p=plan();dna=[dict(reference_id='1234567890123456789',duration=20)]
 studio.validate_director(p,dna)
 p.transfers[0].reference_id='invented'
 with pytest.raises(ValueError):studio.validate_director(p,dna)
 p=plan();p.transfers=[]
 with pytest.raises(ValueError):studio.validate_director(p,dna)

def test_render_uses_owned_source_and_edited_times(client,monkeypatch):
 import backend.worker as worker
 pid=create(client).json()['id'];seed_plan(pid);captured=[]
 def fake(p,payload):
  captured.append((p,payload))
  from backend.db import update
  update(pid,result=dict(render_id='f'*32))
 monkeypatch.setattr(worker,'render_job',fake)
 studio.render_job(project(pid),dict(revision=3,plan=plan().model_dump(),decisions=[dict(id='cut',start=3,end=4,approved=True,locked=True)]))
 assert captured[0][0]['id']==pid
 assert captured[0][0]['analysis']['recommendations'][0]['start']==3
 assert captured[0][1]=={'recommendations':['cut']}
 assert project(pid)['result']['plan_revision']==3


def test_create_retry_is_idempotent(client):
 token='b'*32
 first=create(client,request_id=token)
 second=create(client,request_id=token)
 assert first.status_code==201 and second.status_code==201
 assert first.json()['id']==second.json()['id']
 with connect() as db:
  assert db.execute('SELECT COUNT(*) FROM projects').fetchone()[0]==1
  assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==1

def test_retry_with_cached_reference_reaches_review_without_reanalyzing_reference(client,monkeypatch):
 pid=create(client).json()['id']
 cached=[dict(reference_id='1234567890123456789',duration=20,analysis={'summary':T})]
 with connect() as db:
  db.execute('UPDATE studio_projects SET dna=? WHERE project_id=?',(json.dumps(cached),pid))
 monkeypatch.setattr(studio.media,'prepare',lambda *args:None)
 def unexpected_reference(*args,**kwargs):
  pytest.fail('Retry must not pay to analyze an already cached reference')
 monkeypatch.setattr(studio.ai,'reference_dna',unexpected_reference)
 calls=[]
 def director_response(project_id,path,prompt,schema,purpose,**kwargs):
  calls.append(purpose)
  assert project_id==pid and path.name=='analysis.mp4'
  assert 'sentence level' in prompt
  return plan()
 monkeypatch.setattr(studio.ai,'json_call',director_response)
 studio.analyze(project(pid))
 assert calls==['director_plan']
 assert project(pid)['status']=='ready'
 assert studio.state(pid)['revision']==1
 assert all(not d['approved'] for d in studio.state(pid)['decisions'])
 assert studio.state(pid)['dna']==cached


def test_analysis_automatically_queues_dna_based_decisions(client,monkeypatch):
 pid=create(client).json()['id']
 cached=[dict(reference_id='1234567890123456789',duration=20,analysis={'summary':T})]
 with connect() as db:db.execute('UPDATE studio_projects SET dna=? WHERE project_id=?',(json.dumps(cached),pid))
 monkeypatch.setattr(studio.media,'prepare',lambda *args:None)
 monkeypatch.setattr(studio.ai,'json_call',lambda *args,**kwargs:plan())
 studio.analyze(project(pid))
 with connect() as db:
  row=db.execute('SELECT revision,snapshot,status FROM creative_plans WHERE project_id=?',(pid,)).fetchone()
  assert row['revision']==1 and row['status']=='queued'
  assert json.loads(row['snapshot'])['dna']==cached
  assert json.loads(row['snapshot'])['decision_evidence'] is True
  assert db.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND kind='creative_plan'",(pid,)).fetchone()[0]==1
