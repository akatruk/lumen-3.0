import pytest
from backend.tests.test_studio import client,create,seed_plan,T
from backend import creative_plans as creative
from backend.manual import Edit,Clip
from backend.db import connect,project
from backend.auth import current_user
from backend.app import app

def proposal():
 return creative.Proposal(recommendation_reviews=[creative.RecommendationReview(recommendation_id='cut',outcome='not_applied',reason=T)],decisions=[creative.CreativeDecision(clip_index=i,title=T,observation=T,change=T,reason=T) for i in range(2)],reason=T,notes=[T],edit=Edit(clips=[Clip(start=0,end=10,zoom=1,zoom_end=1.2),Clip(start=12,end=20,transition='fade')]))

def test_whole_plan_is_reviewed_then_renderable_only_after_approval(client,monkeypatch):
 pid=create(client).json()['id'];seed_plan(pid)
 base=f'/api/studio/projects/{pid}/creative-plans';manual=f'/api/studio/projects/{pid}/manual'
 monkeypatch.setattr(creative.ai,'json_call',lambda *a,**kw:proposal())
 r=client.post(base,json={'revision':1});assert r.status_code==202,r.text
 ident=r.json()['id'];creative.run_job(project(pid),{'id':ident})
 listed=client.get(base).json()[0]
 assert listed['audit']['has_changes']
 assert listed['audit']['removed_seconds']==22
 assert listed['audit']['clips'][0]['operations']==['motion']
 assert client.get(manual).json()['saved'] is False
 with connect() as db:db.execute("UPDATE jobs SET status='complete' WHERE project_id=?",(pid,))
 assert client.post(base+'/'+ident+'/accept',json={'revision':1}).status_code==200
 saved=client.get(manual).json()
 assert len(saved['edit']['clips'])==2 and not any(c['approved'] for c in saved['edit']['clips'])
 assert saved['edit']['clips'][0]['zoom_end']==1.2
 assert client.post(manual+'/render',json={'revision':2}).status_code==422
 saved['edit']['clips'][0]['approved']=True
 assert client.put(manual,json={'revision':2,'edit':saved['edit']}).status_code==200
 assert client.post(manual+'/render',json={'revision':3}).status_code==200
 assert client.post(base+'/'+ident+'/accept',json={'revision':1}).status_code==409

def test_ownership_and_locks(client):
 pid=create(client).json()['id'];seed_plan(pid);base=f'/api/studio/projects/{pid}/creative-plans'
 from backend.tests.test_studio import seed_plan as seed
 ds=seed(pid);ds[0].update(approved=True,locked=True)
 assert client.put(f'/api/studio/projects/{pid}/plan',json={'revision':1,'decisions':ds}).status_code==200
 assert client.post(base,json={'revision':2}).status_code==409
 app.dependency_overrides[current_user]=lambda:{'id':'v','email':'other@example.com'}
 assert client.get(base).status_code==404
 assert client.post(base,json={'revision':2}).status_code==404

def test_invalid_media_and_speech_boundaries_rejected():
 p=proposal();p.edit.clips[0].end=41
 with pytest.raises(ValueError):creative.validate(p,40)
 from backend.manual import ExternalBroll
 p=proposal();p.edit.clips[0].external_broll=ExternalBroll(start=0,end=2,source_start=0,asset_id='a'*32)
 with pytest.raises(ValueError):creative.validate(p,40)
 from backend.schemas import Caption
 p=proposal()
 with pytest.raises(ValueError,match='analysis_timestamps_invalid'):
  creative.validate(p,40,[Caption(start=9,end=11,original='Speech',en='Speech',zh='讲话')])

def test_failed_proposal_does_not_break_ready_project(client,monkeypatch):
 from backend.worker import run_once
 pid=create(client).json()['id'];seed_plan(pid);base=f'/api/studio/projects/{pid}/creative-plans'
 r=client.post(base,json={'revision':1});assert r.status_code==202
 def fail(*a,**kw):raise ValueError('provider_invalid_analysis')
 monkeypatch.setattr(creative.ai,'json_call',fail)
 run_once()
 assert project(pid)['status']=='ready'
 assert client.get(base).json()[0]['status']=='failed'
 assert client.get(f'/api/studio/projects/{pid}/manual').json()['saved'] is False

def test_creative_plan_reaches_real_renderer(tmp_path):
 from backend.media import ffmpeg,probe,render
 from backend.tests.test_studio import plan
 from backend.visuals import VisualCard
 from backend.sound_effects import SoundEffect
 source=tmp_path/'source.mp4'
 ffmpeg('-f','lavfi','-i','testsrc2=s=160x240:d=4:r=12','-f','lavfi','-i','sine=frequency=440:duration=4','-c:v','libx264','-c:a','aac',source)
 proposed=creative.Proposal(reason=T,notes=[],edit=Edit(clips=[Clip(start=2,end=4,zoom_end=1.2,card=VisualCard(start=.2,end=1.5,title=T,primary=T,source=T),sound_effects=[SoundEffect(at=.5)]),Clip(start=0,end=2,transition='fade')]))
 creative.validate(proposed,4)
 for c in proposed.edit.clips:c.approved=True
 result=render(source,tmp_path,probe(source),plan(),[],'zh','original',manual=proposed.edit.model_dump())
 assert result['timeline']==[(2,4),(0,2)]
 assert result['metadata']['has_audio'] and abs(result['metadata']['duration']-4)<.2
 assert len(result['director_timeline']['tracks']['sound_effects'])==1

def test_planning_reuses_transcript_and_supplies_safe_cut_points(client,monkeypatch):
 import json
 from backend.tests.test_studio import plan
 from backend.schemas import Caption
 pid=create(client).json()['id'];seed_plan(pid)
 p=plan();p.transcript=[Caption(start=0,end=10,original='Verified speech',en='Verified speech',zh='已转录的讲话')]
 with connect() as db:db.execute('UPDATE studio_projects SET plan=? WHERE project_id=?',(p.model_dump_json(),pid))
 def response(*args,**kwargs):
  assert 'safe_cut_times' in args[2]
  return proposal()
 monkeypatch.setattr(creative.ai,'json_call',response)
 base=f'/api/studio/projects/{pid}/creative-plans'
 ident=client.post(base,json={'revision':1}).json()['id']
 creative.run_job(project(pid),{'id':ident})
 result=client.get(base).json()[0]['result']
 assert result['edit']['captions']==[c.model_dump() for c in p.transcript]

def test_decisions_must_map_to_clips_and_real_reference_ranges():
 p=proposal();dna=[{'reference_id':'ref','duration':10}]
 with pytest.raises(ValueError):creative.validate_evidence(p,dna)
 p.decisions[0].reference=creative.ReferenceEvidence(reference_id='ref',start=0,end=4,technique=T)
 creative.validate_evidence(p,dna)
 p.decisions[0].reference.end=11
 with pytest.raises(ValueError):creative.validate_evidence(p,dna)
 p.decisions[0].reference.end=4;p.decisions[1].clip_index=0
 with pytest.raises(ValueError):creative.validate_evidence(p,dna)

def test_review_cannot_claim_trim_while_retaining_the_same_footage():
 from backend.manual import Cutaway
 analysis={'recommendations':[{'id':'cut','action':'remove','start':2,'end':4}]}
 p=proposal();p.recommendation_reviews[0].outcome='implemented'
 with pytest.raises(ValueError):creative.validate_recommendation_reviews(p,analysis)
 p.edit.clips=[Clip(start=0,end=2),Clip(start=4,end=20)]
 creative.validate_recommendation_reviews(p,analysis)
 p.edit.clips[1].cutaway=Cutaway(start=0,end=2,source_start=2)
 with pytest.raises(ValueError):creative.validate_recommendation_reviews(p,analysis)

def test_review_requires_all_ids_and_allows_explained_non_application():
 p=proposal();analysis={'recommendations':[{'id':'cut','action':'remove','start':2,'end':4}]}
 creative.validate_recommendation_reviews(p,analysis)
 p.recommendation_reviews=[]
 with pytest.raises(ValueError) as exc:creative.validate_recommendation_reviews(p,analysis)
 assert 'exactly one' in exc.value.feedback

def test_hook_claim_requires_the_complete_recommended_opening():
 p=proposal();p.recommendation_reviews[0].outcome='implemented'
 analysis={'recommendations':[{'id':'cut','action':'move_to_front','start':12,'end':20}]}
 with pytest.raises(ValueError):creative.validate_recommendation_reviews(p,analysis)
 p.edit.clips.reverse()
 creative.validate_recommendation_reviews(p,analysis)

def test_unavailable_generation_cannot_be_claimed_as_implemented():
 p=proposal();p.recommendation_reviews[0].outcome='implemented'
 with pytest.raises(ValueError):
  creative.validate_recommendation_reviews(p,{'recommendations':[{'id':'cut','action':'generate_broll','start':2,'end':4}]})
