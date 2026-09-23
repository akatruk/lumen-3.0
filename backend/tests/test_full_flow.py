"""Full API/worker/media chain; external AI is deterministic, never billed."""
import json,uuid,subprocess
import pytest
from backend.tests.test_studio import client,plan
from backend import media,worker,studio,timeline_proposals
from backend.media import ass_available
from backend.config import settings
from backend.db import connect,project
from backend.manual import Clip,ExternalBroll
REAL_PROBE=media.probe

@pytest.mark.skipif(not ass_available(),reason='FFmpeg ass filter required')
@pytest.mark.parametrize('quality_review',[False,True])
def test_upload_analyze_match_approve_render_download(client,tmp_path,monkeypatch,quality_review):
 monkeypatch.setattr(media,'probe',REAL_PROBE)
 src=tmp_path/'fixture.mp4'
 media.ffmpeg('-f','lavfi','-i','color=red:s=320x568:d=40:r=12','-f','lavfi','-i','sine=frequency=440:duration=40','-c:v','libx264','-c:a','aac',src)
 def upload(path):
  data=path.read_bytes();token=uuid.uuid4().hex
  r=client.post('/api/studio/uploads',json={'size':len(data),'token':token});assert r.status_code==201,r.text
  endpoint='/api/studio/uploads/'+r.json()['id']
  for offset in range(0,len(data),16384):
   r=client.put(endpoint+'?offset='+str(offset),content=data[offset:offset+16384]);assert r.status_code==200,r.text
   assert client.get(endpoint).json()['offset']==min(offset+16384,len(data))
  return endpoint
 endpoint=upload(src)
 config=dict(request_id=uuid.uuid4().hex,references=['a'*32],title='Flow QA',script='Original narration',creator=dict(topic='travel',audience='Families',tone='Calm',rules='No invented facts'),owned_rights_confirmed=True,language='zh',budget=5)
 r=client.post(endpoint+'/complete',json=config);assert r.status_code in (200,201),r.text
 pid=r.json()['id'];assert (settings.data_dir/pid/'source').read_bytes()==src.read_bytes()
 # Reuse cached reference DNA: no external download or paid reference analysis.
 with connect() as db:db.execute('UPDATE studio_projects SET dna=? WHERE project_id=?',(json.dumps([dict(reference_id='1234567890123456789',duration=20,analysis={})]),pid))
 director=plan();director.scenes[0].end=40
 monkeypatch.setattr(studio.ai,'json_call',lambda *a,**k:director)
 assert worker.run_once();assert project(pid)['status']=='ready',project(pid).get('error')
 assert (settings.data_dir/pid/'analysis.mp4').exists()
 # The new primary path automatically creates DNA-linked decisions before manual review.
 from backend.creative_plans import Proposal,CreativeDecision,ReferenceEvidence,RecommendationReview
 from backend.manual import Edit
 text=dict(en='Use the reference rhythm',zh='采用参考节奏')
 creative=Proposal(recommendation_reviews=[RecommendationReview(recommendation_id='cut',outcome='not_applied',reason=text)],reason=text,notes=[],edit=Edit(clips=[Clip(start=0,end=40)]),decisions=[CreativeDecision(clip_index=0,title=text,observation=text,change=text,reason=text,reference=ReferenceEvidence(reference_id='1234567890123456789',start=0,end=2,technique=text))])
 monkeypatch.setattr(studio.ai,'json_call',lambda *a,**k:creative)
 assert worker.run_once()
 generated=client.get(f'/api/studio/projects/{pid}/creative-plans').json()[0]
 assert generated['status']=='ready'
 assert generated['result']['decisions'][0]['reference']['reference_id']=='1234567890123456789'
 assert client.post(f'/api/studio/projects/{pid}/creative-plans/'+generated['id']+'/accept',json={'revision':generated['revision']}).status_code==200

 asset_src=tmp_path/'asset.mp4';media.ffmpeg('-f','lavfi','-i','color=lime:s=320x240:d=4:r=12','-c:v','libx264',asset_src)
 r=client.post(upload(asset_src)+'/asset',json=dict(asset_project_id=pid,request_id=uuid.uuid4().hex,title='Owned insert',attribution='QA synthetic',owned_rights_confirmed=True));assert r.status_code==201,r.text
 aid=r.json()['id'];url=f'/api/studio/projects/{pid}/manual'
 state=client.get(url).json();edit=state['edit'];revision=state['revision']
 r=client.put(url,json=dict(revision=revision,edit=edit));assert r.status_code==200,r.text
 revision=r.json()['revision'];clip=Clip.model_validate(edit['clips'][0]);clip.external_broll=ExternalBroll(asset_id=aid,start=1,end=2,source_start=0)
 proposal=timeline_proposals.Proposal(clip=clip,reason=dict(en='Synthetic visual test',zh='测试'))
 monkeypatch.setattr(studio.ai,'json_call',lambda *a,**k:proposal)
 base=f'/api/studio/projects/{pid}/timeline-proposals'
 r=client.post(base,json=dict(revision=revision,clip_id=clip.id,instruction='Find relevant detail',mode='library_broll',asset_ids=[aid]));assert r.status_code==202,r.text
 ident=r.json()['id'];assert worker.run_once()
 listing=client.get(base).json();assert listing[0]['status']=='ready',listing
 r=client.post(base+'/'+ident+'/accept',json={'revision':revision});assert r.status_code==200,r.text
 state=client.get(url).json();edit=state['edit'];revision=state['revision']
 assert not edit['clips'][0]['approved']
 assert client.post(url+'/render',json={'revision':revision}).status_code==422
 music_src=tmp_path/'music.wav';media.ffmpeg('-f','lavfi','-i','sine=frequency=220:duration=3',music_src)
 music_response=client.post(upload(music_src)+'/asset',json=dict(kind='music',asset_project_id=pid,request_id=uuid.uuid4().hex,title='Music bed',attribution='QA synthetic',owned_rights_confirmed=True))
 assert music_response.status_code==201,music_response.text
 from backend.music import Music
 edit['music']=Music(asset_id=music_response.json()['id']).model_dump()
 edit['clips'][0]['approved']=True
 r=client.put(url,json={'revision':revision,'edit':edit});assert r.status_code==200,r.text
 from backend.schemas import QualityReview,Score
 from backend import ai
 monkeypatch.setattr(ai,'review',lambda *a:QualityReview(passed=False,observations=[],issues=[text],revisions=[text],scores=[Score(category=c,value=50,reason=text) for c in ['hook','clarity','pacing','visuals','audio']]))
 assert client.post(url+'/render',json={'revision':r.json()['revision'],'quality_review':quality_review}).status_code==200
 assert worker.run_once();p=project(pid);assert p['status']=='needs_review',p.get('error')
 assert p['result']['qa_status']==('needs_review' if quality_review else 'manual_review_required')
 if quality_review:
  assert p['result']['quality_score']==50
  assert p['result']['quality_revision_id']
  assert p['result']['render_id']==project(pid)['result']['render_id']
 assert p['result']['director_timeline']['tracks']['music'][0]['asset_id']==music_response.json()['id']
 result=settings.data_dir/pid/'renders'/p['result']['render_id']/'result.mp4'
 assert REAL_PROBE(result)['has_audio'];assert abs(REAL_PROBE(result)['duration']-40)<.2
 def pixel(t):return subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(result),'-vf','scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
 assert pixel(.5)[0]>180 and pixel(1.5)[1]>180 and pixel(2.5)[0]>180
 download=client.get(f'/api/projects/{pid}/media/result');assert download.status_code==200
 assert download.content==result.read_bytes()
