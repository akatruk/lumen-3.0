import os
import pytest
from backend.tests.test_studio import client,create,seed_plan
from backend import media,worker
REAL_PROBE=media.probe

@pytest.mark.skipif(os.environ.get('LUMEN_LIVE_STOCK')!='1',reason='External Commons smoke test requires opt-in')
def test_commons_search_import_preview(client,monkeypatch):
    pid=create(client).json()['id'];seed_plan(pid);base=f'/api/studio/projects/{pid}'
    response=client.get(base+'/stock/search',params={'q':'NASA Earth'})
    assert response.status_code==200,response.text
    hit=next(h for h in response.json() if h['duration']<10 and h['license']=='Public domain')
    monkeypatch.setattr(media,'probe',REAL_PROBE)
    assert client.post(base+'/stock/imports',json={'result_id':hit['id'],'license_reviewed':True}).status_code==202
    assert worker.run_once()
    imported=client.get(base+'/stock/imports').json()[0]
    assert imported['status']=='complete',imported
    asset=client.get(base+'/assets').json()[0]
    assert asset['metadata']['provenance']['page_id']==hit['page_id']
    preview=client.get(base+'/assets/'+imported['asset_id']+'/media')
    assert preview.status_code==200 and len(preview.content)>1000
    print('LIVE_STOCK_OK',hit['title'],asset['metadata']['duration'])
