import uuid
from backend.tests.test_studio import client,create,seed_plan
from backend.db import connect
from backend.config import settings
from backend.app import app
from backend.auth import current_user

def test_library_ingest_is_idempotent_private_and_executable(client):
 pid=create(client).json()['id'];seed_plan(pid)
 data=b'owned-library-video';token=uuid.uuid4().hex
 upload=client.post('/api/studio/uploads',json={'size':len(data),'token':token}).json()['id']
 endpoint='/api/studio/uploads/'+upload
 assert client.put(endpoint+'?offset=0',content=data).status_code==200
 body={'asset_project_id':pid,'request_id':uuid.uuid4().hex,'title':'Detail','attribution':'My footage','owned_rights_confirmed':True}
 r=client.post(endpoint+'/asset',json=body);assert r.status_code==201
 asset=r.json()['id'];assert client.post(endpoint+'/asset',json=body).json()['id']==asset
 assert client.get('/api/studio/uploads/completed-asset/'+body['request_id']).json()['id']==asset
 assert (settings.data_dir/pid/'assets'/asset).read_bytes()==data
 assert len(client.get(f'/api/studio/projects/{pid}/assets').json())==1
 with connect() as db:assert db.execute("SELECT count(*) FROM jobs WHERE status='queued'").fetchone()[0]==0
 manual=f'/api/studio/projects/{pid}/manual';edit=client.get(manual).json()['edit']
 edit['clips'][0]['external_broll']={'asset_id':asset,'start':1,'end':3,'source_start':0}
 assert client.put(manual,json={'revision':1,'edit':edit}).status_code==200
 edit['clips'][0]['external_broll']['source_start']=39
 assert client.put(manual,json={'revision':2,'edit':edit}).status_code==422
 second=create(client).json()['id'];seed_plan(second)
 other=client.get(f'/api/studio/projects/{second}/manual').json()['edit'];other['clips'][0]['external_broll']={'asset_id':asset,'start':1,'end':3,'source_start':0}
 assert client.put(f'/api/studio/projects/{second}/manual',json={'revision':1,'edit':other}).status_code==422
 app.dependency_overrides[current_user]=lambda:{'id':'v','email':'other@example.com'}
 assert client.get(f'/api/studio/projects/{pid}/assets').status_code==404
 assert client.get(f'/api/studio/projects/{pid}/assets/{asset}/media').status_code==404
 assert client.get('/api/studio/uploads/completed-asset/'+body['request_id']).json()=={}
