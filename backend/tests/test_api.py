import pytest
from fastapi.testclient import TestClient
from backend.config import settings
from backend.app import app,limits
from backend.db import connect,reserve,settle

@pytest.fixture
def clients(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'data_dir',tmp_path)
    monkeypatch.setattr(settings,'google_sso_only',False)
    monkeypatch.setattr(settings,'lumen_invite_code','test-only-invite')
    monkeypatch.setattr(settings,'secure_cookies',False)
    limits.clear()
    with TestClient(app) as a,TestClient(app) as b:
        for client,email in [(a,'one@test.example'),(b,'two@test.example')]:
            r=client.post('/api/register',json={'email':email,'password':'test-password-123','invite':'test-only-invite'})
            assert r.status_code==200
        yield a,b

def create_project(client,monkeypatch):
    import backend.app as module
    monkeypatch.setattr(module,'probe',lambda p:{'duration':10,'width':320,'height':240,'has_audio':True,'size':20})
    return client.post('/api/projects',data={'title':'Private original','budget':'3'},files={'file':('test.mp4',b'\x00\x00\x00\x20ftypfake-only-for-api-isolation-tests','video/mp4')})

def test_auth_csrf_and_invalid_file(clients):
    a,b=clients
    assert a.get('/api/session').json()['email']=='one@test.example'
    assert a.post('/api/logout',headers={'Origin':'https://attacker.example'}).status_code==403
    assert a.post('/api/projects',files={'file':('bad.mp4',b'not media','video/mp4')}).status_code==422
    assert a.get('/api/projects').json()==[]
    a.post('/api/logout')
    assert a.get('/api/projects').status_code==401

def test_project_and_media_isolation(clients,monkeypatch):
    a,b=clients
    r=create_project(a,monkeypatch); assert r.status_code==201
    pid=r.json()['id']
    assert b.get('/api/projects/'+pid).status_code==404
    assert b.get(f'/api/projects/{pid}/media/original').status_code==404
    assert b.delete('/api/projects/'+pid).status_code==404
    assert a.get(f'/api/projects/{pid}/media/original').status_code==200
    assert a.delete('/api/projects/'+pid).status_code==409
    assert len(a.get('/api/projects').json())==1
    assert b.get('/api/projects').json()==[]

def test_pending_limit_and_budget_atomicity(clients,monkeypatch):
    a,_=clients
    pid=create_project(a,monkeypatch).json()['id']
    create_project(a,monkeypatch);create_project(a,monkeypatch)
    assert create_project(a,monkeypatch).status_code==429
    token=reserve(pid,2,'test')
    with pytest.raises(ValueError,match='budget_limit'): reserve(pid,2,'test')
    settle(token,.1)
    reserve(pid,2,'test')

def test_delete_keeps_daily_spend(clients,monkeypatch):
    a,_=clients
    pid=create_project(a,monkeypatch).json()['id']
    reserve(pid,1,'test')
    with connect() as db:
        db.execute("UPDATE jobs SET status='failed' WHERE project_id=?",(pid,))
        db.execute("UPDATE projects SET status='failed' WHERE id=?",(pid,))
    assert a.delete('/api/projects/'+pid).status_code==200
    assert not (settings.data_dir/pid).exists()
    with connect() as db:
        row=db.execute('SELECT amount,project_id FROM spend').fetchone()
        assert row[0]==1 and row[1] is None

def test_retry_queues_once(clients,monkeypatch):
    a,_=clients
    pid=create_project(a,monkeypatch).json()['id']
    with connect() as db:
        db.execute("UPDATE jobs SET status='failed' WHERE project_id=?",(pid,))
        db.execute("UPDATE projects SET status='failed' WHERE id=?",(pid,))
    assert a.post(f'/api/projects/{pid}/retry').status_code==200
    assert a.post(f'/api/projects/{pid}/retry').status_code==409

def test_upload_rechecks_capacity_after_probe(clients,monkeypatch):
    """Other requests can fill all slots while this upload is being inspected."""
    import backend.app as module
    import time,uuid
    a,_=clients
    uid=a.get('/api/session').json()['id']
    def probe_with_concurrent_uploads(path):
        with connect() as db:
            for _ in range(3):
                db.execute('INSERT INTO projects(id,user_id,title,brief,language,aspect,auto_render,generative,budget,status,stage,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(uuid.uuid4().hex,uid,'Concurrent','','en','original',1,0,3,'queued','queued',time.time(),time.time()))
        return {'duration':10,'width':320,'height':240,'has_audio':True,'size':20}
    monkeypatch.setattr(module,'probe',probe_with_concurrent_uploads)
    r=a.post('/api/projects',files={'file':('test.mp4',b'\x00\x00\x00\x20ftypfake','video/mp4')})
    assert r.status_code==429
    assert len(a.get('/api/projects').json())==3
    assert not any(p.is_dir() for p in settings.data_dir.iterdir())
