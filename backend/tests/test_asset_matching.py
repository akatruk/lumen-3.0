import json,time,uuid,shutil
import pytest
from backend.tests.test_studio import client,create,seed_plan
from backend.db import connect,project
from backend import timeline_proposals as proposals
from backend.manual import Clip,ExternalBroll

@pytest.mark.parametrize("matched",[True,False])
def test_visual_library_match_is_scoped_reviewed_and_bounded(client,monkeypatch,matched):
 from backend import asset_matching
 pid=create(client).json()['id'];seed_plan(pid)
 asset=uuid.uuid4().hex
 with connect() as db:db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)',(asset,pid,uuid.uuid4().hex,'Interior','Owned',json.dumps({'duration':10}),time.time()))
 manual=f'/api/studio/projects/{pid}/manual';edit=client.get(manual).json()['edit'];target=edit['clips'][0]['id']
 assert client.put(manual,json={'revision':1,'edit':edit}).status_code==200
 url=f'/api/studio/projects/{pid}/timeline-proposals'
 body={'revision':2,'clip_id':target,'instruction':'Show a relevant interior detail.','mode':'library_broll','asset_ids':[asset]}
 assert client.post(url,json=body|{'asset_ids':['f'*32]}).status_code==422
 r=client.post(url,json=body);assert r.status_code==202
 result=proposals.Proposal(clip=Clip.model_validate(edit['clips'][0]),reason={'en':'Visible detail supports the narration.','zh':'可见细节支持旁白。'})
 if matched:result.clip.external_broll=ExternalBroll(asset_id=asset,start=1,end=2.5,source_start=4)
 monkeypatch.setattr(asset_matching,'build_reel',lambda *args:'sample-reel.mp4')
 def fake_ai(*args,**kwargs):
  assert kwargs['reference']=='sample-reel.mp4'
  assert 'CANDIDATE SAMPLE REEL' in args[2]
  return result
 monkeypatch.setattr(proposals.ai,'json_call',fake_ai)
 proposals.run_job(project(pid),{'id':r.json()['id']})
 assert client.get(manual).json()['edit']['clips'][0]['external_broll'] is None
 with connect() as db:db.execute("UPDATE jobs SET status='complete' WHERE project_id=?",(pid,))
 listing=client.get(url).json()[0];assert listing['has_match']==matched and listing['mode']=='library_broll'
 if not matched:
  assert client.post(url+'/'+r.json()['id']+'/accept',json={'revision':2}).status_code==422
  assert client.get(manual).json()['edit']['clips'][0]['external_broll'] is None
  return
 assert client.post(url+'/'+r.json()['id']+'/accept',json={'revision':2}).status_code==200
 updated=client.get(manual).json()['edit']['clips'][0]
 assert updated['external_broll']['asset_id']==asset and updated['approved'] is False
 assert updated['start']==0 and updated['end']==40

def test_match_rejects_unseen_ranges_and_unrelated_changes():
 clip=Clip(id='target',start=0,end=10)
 snapshot={'mode':'library_broll','edit':{'clips':[clip.model_dump()]},'candidates':[{'id':'a'*32,'samples':[{'start':4,'end':6}]}]}
 result=proposals.Proposal(clip=clip.model_copy(deep=True),reason={'en':'Match','zh':'匹配'})
 result.clip.external_broll=ExternalBroll(asset_id='a'*32,start=0,end=1,source_start=4)
 proposals.validate_proposal(result,snapshot,'target',10)
 result.clip.external_broll.source_start=7
 with pytest.raises(ValueError,match='analysis_timestamps_invalid'):proposals.validate_proposal(result,snapshot,'target',10)
 result.clip.external_broll.source_start=4;result.clip.zoom=2
 with pytest.raises(ValueError,match='provider_invalid_analysis'):proposals.validate_proposal(result,snapshot,'target',10)

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg required')
def test_candidate_reel_contains_bounded_labeled_samples(tmp_path,monkeypatch):
 from backend.config import settings
 from backend.asset_matching import build_reel,sample_ranges
 from backend.media import ffmpeg,probe
 monkeypatch.setattr(settings,'data_dir',tmp_path)
 pid='b'*32;ident='a'*32;folder=tmp_path/pid/'assets';folder.mkdir(parents=True)
 ffmpeg('-f','lavfi','-i','color=blue:s=320x240:d=6:r=12','-c:v','libx264','-f','mp4',folder/ident)
 candidates=[{'id':ident,'label':'A1','duration':6,'samples':sample_ranges(6)}]
 reel=build_reel(pid,candidates,tmp_path/'reel')
 assert abs(probe(reel)['duration']-6)<.2
 assert 'A1 | source 2.00-4.00s' in (tmp_path/'reel'/'sample-1.ass').read_text()
