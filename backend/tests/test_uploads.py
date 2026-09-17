import uuid
from backend.tests.test_studio import client
from backend.db import connect
from backend.config import settings
from backend.app import app
from backend.auth import current_user

def test_resumable_upload_ownership_offsets_and_idempotent_complete(client):
 data=b'owned-source-only';token=uuid.uuid4().hex
 r=client.post('/api/studio/uploads',json={'size':len(data),'token':token});assert r.status_code==201
 ident=r.json()['id'];url='/api/studio/uploads/'+ident
 assert client.put(url+'?offset=0',content=data[:5]).json()['offset']==5
 # Lost response: inspect committed offset, don't append the same bytes twice.
 assert client.put(url+'?offset=0',content=data[:5]).status_code==409
 assert client.get(url).json()['offset']==5
 app.dependency_overrides[current_user]=lambda:{'id':'v','email':'other@example.com'}
 assert client.get(url).status_code==404
 assert client.put(url+'?offset=5',content=data[5:]).status_code==404
 app.dependency_overrides[current_user]=lambda:{'id':'u','email':'test@example.com'}
 requestid=uuid.uuid4().hex
 config=dict(request_id=requestid,references=['a'*32],title='Chunked',script='My script',creator=dict(topic='travel',audience='Families',tone='Calm'),owned_rights_confirmed=True,language='zh',budget=5)
 assert client.post(url+'/complete',json=config).status_code==409
 with connect() as db:assert db.execute('SELECT count(*) FROM jobs').fetchone()[0]==0
 assert client.put(url+'?offset=5',content=data[5:]).status_code==200
 result=client.post(url+'/complete',json=config);assert result.status_code==201
 pid=result.json()['id'];assert (settings.data_dir/pid/'source').read_bytes()==data
 assert client.post(url+'/complete',json=config).json()['id']==pid
 assert client.get('/api/studio/uploads/completed/'+requestid).json()['id']==pid
 with connect() as db:assert db.execute('SELECT count(*) FROM jobs').fetchone()[0]==1
 assert not (settings.data_dir/'uploads'/ident).exists()

def test_chunk_limits_and_restart_recovery(client):
 token=uuid.uuid4().hex
 r=client.post('/api/studio/uploads',json={'size':8,'token':token}).json();url='/api/studio/uploads/'+r['id']
 assert client.post('/api/studio/uploads',json={'size':8,'token':token}).json()['id']==r['id']
 assert client.put(url+'?offset=0',content=b'123456789').status_code==413
 assert client.get(url).json()['offset']==0
 # Simulate a crash after disk write but before database commit.
 (settings.data_dir/'uploads'/r['id']).write_bytes(b'stale')
 assert client.put(url+'?offset=0',content=b'abcd').status_code==200
 assert (settings.data_dir/'uploads'/r['id']).read_bytes()==b'abcd'

def test_frontend_entry_never_reuses_stale_conditional_html(client):
 first=client.get('/')
 assert first.status_code==200
 assert 'no-store' in first.headers['cache-control']
 second=client.get('/',headers={'If-None-Match':first.headers.get('etag',''),'If-Modified-Since':first.headers.get('last-modified','')})
 assert second.status_code==200
 assert second.text==first.text

def test_large_upload_bytes_survive_mid_transfer_retry(client):
 import hashlib
 chunk=bytes(range(256))*16384  # 4 MiB, deterministic non-empty content
 count=8;size=len(chunk)*count
 state=client.post('/api/studio/uploads',json={'size':size,'token':uuid.uuid4().hex}).json()
 url='/api/studio/uploads/'+state['id']
 for i in range(count):
  assert client.put(url+'?offset='+str(i*len(chunk)),content=chunk).status_code==200
  if i==1:
   assert client.put(url+'?offset='+str(i*len(chunk)),content=chunk).status_code==409
   assert client.get(url).json()['offset']==2*len(chunk)
 assert client.get(url).json()['offset']==size
 stored=settings.data_dir/'uploads'/state['id']
 expected=hashlib.sha256()
 for _ in range(count):expected.update(chunk)
 with stored.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected.hexdigest()
