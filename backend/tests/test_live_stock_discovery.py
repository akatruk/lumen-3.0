import os,json
import pytest
from backend.tests.test_stock_discovery import client,setup
from backend.config import settings
from backend import media,worker
from backend.db import connect

@pytest.mark.skipif(os.environ.get('LUMEN_LIVE_DISCOVERY')!='1',reason='Bounded paid synthetic integration test')
def test_live_scene_search(client):
    pid,url,edit,revision=setup(client)
    edit['clips'][0]['text']='Explain Earth rotation using NASA satellite views. Search for illustrative Earth rotation footage.'
    revision=client.put(url,json={'revision':revision,'edit':edit}).json()['revision']
    folder=settings.data_dir/pid
    from backend.schemas import Caption
    ass=folder/'test.ass'
    media.write_subtitles(ass,[Caption(start=0,end=40,original='EARTH ROTATION',en='EARTH ROTATION',zh='地球自转')],[(0,40)],'en',320,568)
    media.ffmpeg('-f','lavfi','-i','color=blue:s=320x568:r=12:d=40','-vf',f"ass='{ass}'",'-c:v','libx264','-preset','veryfast',folder/'analysis.mp4')
    with connect() as db:db.execute('UPDATE projects SET budget=.5 WHERE id=?',(pid,))
    base=f'/api/studio/projects/{pid}/stock'
    response=client.post(base+'/discover',json={'revision':revision,'clip_id':edit['clips'][0]['id']})
    assert response.status_code==202,response.text
    assert worker.run_once()
    item=client.get(base+'/discoveries').json()[0]
    assert item['status']=='ready',item
    assert item['result']['queries'] and item['result']['hits'],item['result']
    with connect() as db:spent=db.execute('SELECT SUM(actual) FROM spend WHERE project_id=?',(pid,)).fetchone()[0]
    print('LIVE_DISCOVERY_OK',json.dumps({'queries':[q['query'] for q in item['result']['queries']],'candidates':len(item['result']['hits']),'cost':spent}))
