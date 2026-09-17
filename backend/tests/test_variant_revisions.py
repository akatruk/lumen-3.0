import json,time
import pytest
from backend.tests.test_studio import client
from backend.tests.test_variants import ready
from backend.db import connect,project
from backend import variants


def package(client):
    pid=ready(client)
    outputs=[dict(platform=p,title='Title',description='Description',cta='Save',hashtags=['#Travel'],rationale={'en':'Specific','zh':'具体'},segments=[{'start':0,'end':40}],metadata={'duration':40,'width':1080,'height':1920},review_status='needs_human_review',locked=False) for p in variants.PLATFORMS]
    manifest=dict(master_id='a'*32,variants=outputs)
    with connect() as db:
        db.execute("UPDATE projects SET language='en' WHERE id=?",(pid,))
        db.execute('INSERT INTO platform_packages VALUES(?,?,?,?,?)',(pid,'a'*32,'b'*32,'complete',json.dumps(manifest)))
    return pid,manifest

def finish(pid):
    with connect() as db:
        job=db.execute("SELECT payload FROM jobs WHERE project_id=? AND status='queued'",(pid,)).fetchone()
        payload=json.loads(job[0]);m=payload['base_manifest'];m['variants']=[payload['override'] if v['platform']==payload['override']['platform'] else v for v in m['variants']]
        db.execute("UPDATE platform_packages SET status='complete',result=? WHERE project_id=?",(json.dumps(m),pid))
        db.execute("UPDATE jobs SET status='complete' WHERE project_id=?",(pid,))
    return payload['package_id'],m

def test_legacy_three_platform_package_remains_editable(client):
    pid,manifest=package(client)
    manifest['variants']=manifest['variants'][:3]
    with connect() as db:db.execute('UPDATE platform_packages SET result=? WHERE project_id=?',(json.dumps(manifest),pid))
    current=manifest['variants'][0]
    body={k:current[k] for k in ('title','description','cta','hashtags','segments')}
    response=client.post(f'/api/studio/projects/{pid}/variants/edit',json=body|{'package_id':'b'*32,'platform':'douyin'})
    assert response.status_code==200,response.text

def test_review_lock_history_and_stale_requests(client):
    pid,m=package(client);url=f'/api/studio/projects/{pid}/variants';base={'package_id':'b'*32,'platform':'douyin'}
    assert client.post(url+'/review',json=base|{'approved':True,'locked':True}).status_code==200
    assert client.post(url+'/review',json=base|{'approved':True,'locked':True}).status_code==409
    current,m=finish(pid)
    assert m['variants'][0]['locked'] and m['variants'][0]['review_status']=='approved'
    assert m['variants'][1]['review_status']=='needs_human_review'
    assert len(client.get(url+'/history').json())==1
    assert client.get(url+'/history/'+'b'*32).json()['result']['variants'][0]['review_status']=='needs_human_review'
    edited={k:m['variants'][0][k] for k in ('title','description','hashtags','cta','segments')}
    assert client.post(url+'/edit',json={'package_id':current,'platform':'douyin'}|edited).status_code==409
    assert client.post(url+'/review',json={'package_id':current,'platform':'douyin','approved':False,'locked':False}).status_code==409
    assert client.post(url+'/review',json={'package_id':current,'platform':'douyin','approved':True,'locked':False}).status_code==200

def test_edit_invalid_ranges_preserves_history_and_other_versions(client):
    pid,m=package(client);url=f'/api/studio/projects/{pid}/variants'
    edited={k:m['variants'][0][k] for k in ('title','description','hashtags','cta','segments')}
    body={'package_id':'b'*32,'platform':'douyin'}|edited
    assert client.post(url+'/edit',json=body|{'segments':[{'start':2,'end':40}]}).status_code==422
    assert client.post(url+'/edit',json=body|{'title':'New title'}).status_code==200
    current,updated=finish(pid)
    assert updated['variants'][0]['title']=='New title'
    assert updated['variants'][1:]==m['variants'][1:]
    assert client.post(url+'/restore',json={'package_id':'b'*32}).status_code==200
    assert client.get(url).json()['package_id']=='b'*32
    from backend.app import app
    from backend.auth import current_user
    app.dependency_overrides[current_user]=lambda:{'id':'v','email':'other@example.com'}
    assert client.get(url+'/history').status_code==404
    assert client.get(url+'/history/'+'b'*32).status_code==404
    assert client.post(url+'/restore',json={'package_id':'b'*32}).status_code==404
