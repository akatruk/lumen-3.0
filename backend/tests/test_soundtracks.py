import json,time,uuid
from backend.tests.test_studio import client,create,seed_plan
from backend.app import app
from backend.auth import current_user
from backend.db import connect,project
from backend.config import settings
from backend import soundtracks


def seed(monkeypatch):
    row={'id':'calm','title':'Calm','duration':10,'attribution':'Composer — CC BY 4.0'}
    monkeypatch.setattr(soundtracks,'curated',lambda:[row])
    folder=settings.data_dir/'soundtracks';folder.mkdir(exist_ok=True)
    (folder/'calm.mp3').write_bytes(b'music')
    return row


def test_catalogue_import_is_private_idempotent_and_preserves_edit(client,monkeypatch):
    seed(monkeypatch);pid=create(client).json()['id'];seed_plan(pid)
    before=project(pid)
    assert client.get('/api/studio/soundtracks').json()[0]['available']
    assert client.get('/api/studio/soundtracks/curated:calm/media').content==b'music'
    url=f'/api/studio/projects/{pid}/soundtracks/curated:calm'
    r=client.post(url);assert r.status_code==201;ident=r.json()['id']
    assert client.post(url).json()=={'id':ident,'existing':True}
    assert project(pid)['result']==before['result'] and project(pid)['cost']==before['cost']
    with connect() as db:
        row=db.execute('SELECT * FROM studio_assets WHERE id=?',(ident,)).fetchone()
        assert row['attribution']=='Composer — CC BY 4.0'
        assert json.loads(row['metadata'])['kind']=='music'
    (settings.data_dir/'soundtracks/calm.mp3').unlink()
    assert (settings.data_dir/pid/'assets'/ident).read_bytes()==b'music'
    app.dependency_overrides[current_user]=lambda:{'id':'v','email':'other@example.com'}
    assert client.post(url).status_code==404
    assert client.get(f'/api/studio/soundtracks/asset:{ident}/media').status_code==404
    assert client.put(f'/api/studio/soundtracks/asset:{ident}/favorite',json={'favorite':True}).status_code==404


def test_favorites_missing_media_and_capacity(client,monkeypatch):
    seed(monkeypatch);pid=create(client).json()['id'];seed_plan(pid)
    fav='/api/studio/soundtracks/curated:calm/favorite'
    assert client.put(fav,json={'favorite':True}).status_code==200
    assert client.get('/api/studio/soundtracks').json()[0]['favorite']
    assert client.put(fav,json={'favorite':False}).status_code==200
    assert not client.get('/api/studio/soundtracks').json()[0]['favorite']
    with connect() as db:
        for _ in range(20):db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)',(uuid.uuid4().hex,pid,uuid.uuid4().hex,'Asset','Owned',json.dumps({'duration':1}),time.time()))
    assert client.post(f'/api/studio/projects/{pid}/soundtracks/curated:calm').status_code==422
    assert client.post(f'/api/studio/projects/{pid}/soundtracks/curated:missing').status_code==404
    (settings.data_dir/'soundtracks/calm.mp3').unlink()
    assert not client.get('/api/studio/soundtracks').json()[0]['available']
    assert client.get('/api/studio/soundtracks/curated:calm/media').status_code==404


def test_owned_upload_can_be_reused_without_exposing_other_users(client,monkeypatch):
    seed(monkeypatch);first=create(client).json()['id'];second=create(client).json()['id']
    ident=uuid.uuid4().hex;folder=settings.data_dir/first/'assets';folder.mkdir();(folder/ident).write_bytes(b'owned music')
    with connect() as db:db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)',(ident,first,uuid.uuid4().hex,'Mine','My license',json.dumps({'kind':'music','duration':12,'mime':'audio/mpeg'}),time.time()))
    key='asset:'+ident
    assert client.get('/api/studio/soundtracks').json()[1]['key']==key
    assert client.post(f'/api/studio/projects/{first}/soundtracks/{key}').json()['id']==ident
    added=client.post(f'/api/studio/projects/{second}/soundtracks/{key}').json()['id']
    (folder/ident).unlink()
    assert (settings.data_dir/second/'assets'/added).read_bytes()==b'owned music'
    app.dependency_overrides[current_user]=lambda:{'id':'v','email':'other@example.com'}
    assert len(client.get('/api/studio/soundtracks').json())==1
    app.dependency_overrides.clear()
    assert client.get('/api/studio/soundtracks').status_code==401
    assert client.get('/api/studio/soundtracks/curated:calm/media').status_code==401
