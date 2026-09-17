import json
import pytest
from backend import stock,media,worker
from backend.tests.test_studio import client,create,seed_plan
from backend.db import connect,project
REAL_PROBE=media.probe

def page():
    return {'pageid':12,'title':'File:Ocean.webm','videoinfo':[{'duration':2,'extmetadata':{'LicenseShortName':{'value':'CC BY 4.0'},'LicenseUrl':{'value':'https://creativecommons.org/licenses/by/4.0/'},'Artist':{'value':'<b>Author</b>'},'ImageDescription':{'value':'<p>Ocean waves</p>'}},'derivatives':[{'src':'https://upload.wikimedia.org/wikipedia/commons/test.webm','height':480,'width':854,'type':'video/webm'}]}]}

def test_metadata_filters_and_download_host_guard():
    p=page();c=stock.candidate(p)
    assert c['artist']=='Author' and c['source_url']=='https://commons.wikimedia.org/?curid=12'
    for url in ['http://upload.wikimedia.org/wikipedia/commons/x','https://127.0.0.1/x','https://upload.wikimedia.org.evil.test/wikipedia/commons/x','https://user@upload.wikimedia.org/wikipedia/commons/x','https://upload.wikimedia.org:bad/wikipedia/commons/x']:
        assert not stock.safe_media(url)
    p['videoinfo'][0]['extmetadata']['LicenseShortName']['value']='All rights reserved'
    assert stock.candidate(p) is None
    p=page();p['videoinfo'][0]['extmetadata']['Categories']={'value':'License review needed (video)'}
    assert stock.candidate(p) is None

def test_search_import_and_preview_preserve_saved_edit(client,monkeypatch,tmp_path):
    pid=create(client).json()['id'];seed_plan(pid);base=f'/api/studio/projects/{pid}'
    monkeypatch.setattr(stock,'query',lambda **kw:[page()])
    hits=client.get(base+'/stock/search',params={'q':'ocean'}).json();assert len(hits)==1
    assert 'media_url' not in hits[0]
    body={'result_id':hits[0]['id'],'license_reviewed':True}
    assert client.post(base+'/stock/imports',json=body|{'license_reviewed':False}).status_code==422
    r=client.post(base+'/stock/imports',json=body);assert r.status_code==202
    assert client.post(base+'/stock/imports',json=body).json()==r.json()
    def fake_download(url,target):media.ffmpeg('-f','lavfi','-i','color=blue:s=160x240:d=2:r=12','-c:v','libvpx-vp9',target)
    monkeypatch.setattr(stock,'download',fake_download);monkeypatch.setattr(media,'probe',REAL_PROBE)
    assert worker.run_once()
    item=client.get(base+'/stock/imports').json()[0];assert item['status']=='complete'
    asset=client.get(base+'/assets').json()[0]
    assert asset['metadata']['provenance']['license']=='CC BY 4.0'
    assert 'Author' in asset['attribution']
    assert 'data' not in item and item['title']=='Ocean.webm'
    repeated=client.get(base+'/stock/search',params={'q':'ocean'}).json()[0]
    assert client.post(base+'/stock/imports',json={'result_id':repeated['id'],'license_reviewed':True}).status_code==202
    assert client.get(base+'/stock/imports').json()[0]['asset_id']==item['asset_id']
    assert len(client.get(base+'/assets').json())==1
    assert client.get(base+'/assets/'+item['asset_id']+'/media').status_code==200
    assert project(pid)['status']=='ready'
    assert not client.get(base+'/manual').json()['saved']
    from backend.app import app
    from backend.auth import current_user
    app.dependency_overrides[current_user]=lambda:{'id':'v','email':'other@example.com'}
    assert client.get(base+'/stock/imports').status_code==404
    assert client.post(base+'/stock/imports',json=body).status_code==404

def test_changed_license_rejected_without_failing_project(client,monkeypatch):
    pid=create(client).json()['id'];seed_plan(pid);base=f'/api/studio/projects/{pid}/stock'
    monkeypatch.setattr(stock,'query',lambda **kw:[page()])
    hit=client.get(base+'/search',params={'q':'ocean'}).json()[0]
    assert client.post(base+'/imports',json={'result_id':hit['id'],'license_reviewed':True}).status_code==202
    p=page();p['videoinfo'][0]['extmetadata']['LicenseShortName']['value']='CC BY-SA 4.0'
    monkeypatch.setattr(stock,'query',lambda **kw:[p])
    assert worker.run_once()
    assert client.get(base+'/imports').json()[0]['error']=='stock_license_changed'
    assert project(pid)['status']=='ready'
