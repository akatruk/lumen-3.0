"""Opt-in real AI analysis → editable plan → approved rendered output.

Synthetic footage only. Dedicated QA schema; at most the existing bounded repair
per analysis stage and one render review. Set LUMEN_LIVE_REVISION=1 to execute
the queued low-score revision draft too, with a $2 project budget instead of $1.
No generated footage or customer data. The revision remains unaccepted.
"""
import os,json
import pytest
from backend.tests.test_studio import client,create
from backend.config import settings
from backend import media,worker
from backend.db import project,connect
REAL_PROBE=media.probe

@pytest.mark.skipif(os.environ.get('LUMEN_LIVE_DIRECTOR')!='1',reason='Paid real director test requires opt-in')
def test_live_analysis_plan_and_render(client,monkeypatch):
    revise=os.environ.get('LUMEN_LIVE_REVISION')=='1'
    pid=create(client,budget=2 if revise else 1,language='en',script='A synthetic packing tutorial: pack light, choose one bag, check documents. Improve pacing using the reference structure. No spoken audio.').json()['id']
    monkeypatch.setattr(media,'probe',REAL_PROBE)
    folder=settings.data_dir/pid
    from backend.schemas import Caption
    def make(dest,length):
        dest.parent.mkdir(parents=True,exist_ok=True)
        ass=dest.parent/'synthetic.ass'
        media.write_subtitles(ass,[Caption(start=i*length/3,end=(i+1)*length/3,original=text,en=text,zh=text) for i,text in enumerate(['PACK LIGHT','ONE BAG','CHECK DOCUMENTS'])],[(0,length)],'en',320,568)
        media.ffmpeg('-f','lavfi','-i',f'testsrc2=s=320x568:r=12:d={length}','-vf',f"ass='{ass}'",'-c:v','libx264','-preset','veryfast','-f','mp4',dest)
    make(folder/'source',30)
    make(folder/'references'/'1234567890123456789'/'source',12)
    assert worker.run_once()
    assert project(pid)['status']=='ready',project(pid)['error']
    assert worker.run_once()
    base=f'/api/studio/projects/{pid}'
    proposed=client.get(base+'/creative-plans').json()[0]
    assert proposed['status']=='ready',proposed.get('error')
    revision=client.get(base).json()['revision']
    assert client.post(base+'/creative-plans/'+proposed['id']+'/accept',json={'revision':revision}).status_code==200
    saved=client.get(base+'/manual').json()
    for clip in saved['edit']['clips']:clip['approved']=True
    response=client.put(base+'/manual',json={'revision':saved['revision'],'edit':saved['edit']});assert response.status_code==200,response.text
    assert client.post(base+'/manual/render',json={'revision':response.json()['revision'],'quality_review':True}).status_code==200
    assert worker.run_once()
    output=project(pid)
    revision_draft=None
    if revise and output['result'].get('quality_revision_id'):
        assert worker.run_once()
        revision_draft=next(item for item in client.get(base+'/creative-plans').json() if item['id']==output['result']['quality_revision_id'])
    with connect() as db:
        spend=[dict(r) for r in db.execute('SELECT purpose,amount,actual FROM spend WHERE project_id=?',(pid,))]
        events=[dict(r) for r in db.execute('SELECT kind,detail FROM events WHERE project_id=?',(pid,))]
    (folder/'live-report.json').write_text(json.dumps({'result':output['result'],'proposal':proposed,'revision_draft':revision_draft,'spend':spend,'events':events},ensure_ascii=False))
    if revision_draft is not None:
        assert revision_draft['status']=='ready',revision_draft.get('error')
        responses=revision_draft['result']['quality_revision_reviews']
        assert {r['revision_index'] for r in responses}==set(range(len(output['result']['qa']['revisions'])))
        assert client.get(base+'/manual').json()['edit']==saved['edit']
        assert project(pid)['result']['render_id']==output['result']['render_id']
    assert output['status'] in ('complete','needs_review'),output['error']
    assert output['result']['qa_status']!='unavailable'
    path=folder/'renders'/output['result']['render_id']/'result.mp4'
    assert REAL_PROBE(path)['duration']>1
    print('LIVE_DIRECTOR_OK',json.dumps({'shots':len(saved['edit']['clips']),'quality_status':output['result']['qa_status'],'duration':REAL_PROBE(path)['duration']}))
