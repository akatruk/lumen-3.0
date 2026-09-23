import json,time,uuid,shutil
import pytest
from backend.tests.test_studio import client,create,seed_plan
from backend.db import connect,project
from backend import timeline_proposals as proposals
from backend.manual import Clip,ExternalBroll
from backend.media import ass_available

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
  assert kwargs['reference_label']=='CANDIDATE SAMPLE REEL'
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

@pytest.mark.skipif(not shutil.which('ffmpeg') or not ass_available(),reason='FFmpeg ass filter required')
def test_candidate_reel_contains_bounded_labeled_samples(tmp_path,monkeypatch):
 from backend.config import settings
 from backend.asset_matching import build_reel,video_ranges
 from backend.media import ffmpeg,probe
 monkeypatch.setattr(settings,'data_dir',tmp_path)
 pid='b'*32;ident='a'*32;folder=tmp_path/pid/'assets';folder.mkdir(parents=True)
 ffmpeg('-f','lavfi','-i','color=blue:s=320x240:d=6:r=12','-c:v','libx264','-f','mp4',folder/ident)
 candidates=[{'id':ident,'label':'A1','duration':6,'samples':video_ranges(6,40)}]
 reel=build_reel(pid,candidates,tmp_path/'reel')
 assert abs(probe(reel)['duration']-6)<.2
 assert 'A1 | source 3.00-6.00s' in (tmp_path/'reel'/'sample-1.ass').read_text()

@pytest.mark.parametrize('duration,target',[(.1,1),(2,40),(6,40),(19,40),(20,40),(21,40),(420,40),(60,1)])
def test_video_samples_are_bounded_and_cover_short_assets(duration,target):
 from backend.asset_matching import video_ranges
 spans=video_ranges(duration,target)
 assert 1<=len(spans)<=5
 assert spans[0]['start']==0 and spans[-1]['end']==duration
 assert all(0<=s['start']<s['end']<=duration and s['end']-s['start']<=min(4,target)+.001 for s in spans)
 assert sum(s['end']-s['start'] for s in spans)<=20.001
 if duration<=5*min(4,target):
  assert all(a['end']==b['start'] for a,b in zip(spans,spans[1:]))


def test_four_second_match_is_allowed_but_unseen_gap_is_not():
 from backend.asset_matching import video_ranges
 clip=Clip(id='target',start=0,end=40)
 snapshot={'mode':'library_broll','edit':{'clips':[clip.model_dump()]},'candidates':[{'id':'a'*32,'samples':video_ranges(60,40)}]}
 result=proposals.Proposal(clip=clip.model_copy(deep=True),reason={'en':'Match','zh':'匹配'})
 result.clip.external_broll=ExternalBroll(asset_id='a'*32,start=1,end=5,source_start=14)
 proposals.validate_proposal(result,snapshot,'target',40)
 result.clip.external_broll.source_start=16
 with pytest.raises(ValueError,match='analysis_timestamps_invalid'):proposals.validate_proposal(result,snapshot,'target',40)


def test_single_clip_edit_preserves_manually_corrected_speech_boundaries():
 clip=Clip(id='target',start=0,end=10)
 caption={'start':3,'end':6,'original':'Corrected speech','en':'Corrected speech','zh':'修正后的讲话'}
 snapshot={'mode':'edit','edit':{'clips':[clip.model_dump()],'captions':[caption]},'transcript':[]}
 result=proposals.Proposal(clip=clip.model_copy(deep=True),reason={'en':'Trim','zh':'剪辑'})
 result.clip.start=4
 with pytest.raises(ValueError,match='analysis_timestamps_invalid'):
  proposals.validate_proposal(result,snapshot,'target',10)
 result.clip.start=3
 proposals.validate_proposal(result,snapshot,'target',10)
