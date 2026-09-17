import time
from urllib.parse import urlparse, parse_qs
import pytest
from fastapi.testclient import TestClient
import backend.app as module
from backend.config import settings
from backend.db import connect

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'data_dir',tmp_path)
    monkeypatch.setattr(settings,'secure_cookies',False)
    monkeypatch.setattr(settings,'google_sso_only',True)
    monkeypatch.setattr(settings,'google_client_id','test-client')
    monkeypatch.setattr(settings,'google_client_secret','test-secret')
    monkeypatch.setattr(settings,'google_allowed_emails','andreykatruk@gmail.com')
    module.limits.clear()
    with TestClient(module.app) as c: yield c

def start(c):
    r=c.get('/api/auth/google',follow_redirects=False)
    assert r.status_code==303
    q=parse_qs(urlparse(r.headers['location']).query)
    assert q['code_challenge_method']==['S256']
    assert q['scope']==['openid email']
    return q['state'][0]

def callback(c,state):
    return c.get('/api/auth/google/callback',params={'state':state,'code':'test-code'},follow_redirects=False)

def test_allowed_identity_and_replay(client,monkeypatch):
    calls=[]
    def identity(code,verifier):
        calls.append(code)
        assert len(verifier)>=43
        return {'sub':'google-sub','email':'andreykatruk@gmail.com','email_verified':True}
    monkeypatch.setattr(module,'google_identity',identity)
    state=start(client)
    assert callback(client,state).headers['location']=='/#studio'
    assert client.get('/api/session').json()['email']=='andreykatruk@gmail.com'
    assert callback(client,state).headers['location']=='/?auth_error=google_failed'
    assert len(calls)==1
    monkeypatch.setattr(settings,'google_allowed_emails','other@example.com')
    assert client.get('/api/projects').status_code==401

@pytest.mark.parametrize('info',[{'sub':'x','email':'other@gmail.com','email_verified':True},{'sub':'x','email':'andreykatruk@gmail.com','email_verified':False},{'email':'andreykatruk@gmail.com','email_verified':True}])
def test_denied_identity(client,monkeypatch,info):
    monkeypatch.setattr(module,'google_identity',lambda *args: info)
    assert callback(client,start(client)).headers['location']=='/?auth_error=access_denied'
    assert client.get('/api/session').status_code==401
    with connect() as db: assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0

def test_bad_binding_expired_state_and_provider_failure(client,monkeypatch):
    def fail(*args): raise AssertionError('must not exchange invalid state')
    monkeypatch.setattr(module,'google_identity',fail)
    state=start(client)
    cookie=client.cookies.get('lumen_oauth')
    client.cookies.clear()
    assert callback(client,state).headers['location']=='/?auth_error=google_failed'
    client.cookies.set('lumen_oauth',cookie,path='/api/auth/google/callback')
    with connect() as db: db.execute('UPDATE oauth_states SET expires=?',(time.time()-1,))
    assert callback(client,state).headers['location']=='/?auth_error=google_failed'
    assert callback(client,start(client)).headers['location']=='/?auth_error=google_failed'
    assert client.get('/api/session').status_code==401

def test_password_routes_and_old_session_blocked(client,monkeypatch):
    payload={'email':'andreykatruk@gmail.com','password':'some-long-password','invite':'x'}
    assert client.post('/api/register',json=payload).status_code==403
    assert client.post('/api/login',json=payload).status_code==403
    monkeypatch.setattr(settings,'google_sso_only',False)
    monkeypatch.setattr(settings,'lumen_invite_code','x')
    assert client.post('/api/register',json=payload).status_code==200
    monkeypatch.setattr(settings,'google_sso_only',True)
    assert client.get('/api/session').status_code==401
    monkeypatch.setattr(module,'google_identity',lambda *args:{'sub':'existing','email':payload['email'],'email_verified':True})
    assert callback(client,start(client)).headers['location']=='/#studio'
    with connect() as db: assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0]==1
