import json
import pytest
from backend.tests.test_studio import client,create,seed_plan
from backend.db import connect,project
from backend.auth import current_user
from backend.app import app
from backend import studio

def manual():
 return dict(clips=[dict(start=20,end=30,zoom=1.5,x=.2,y=.8,text='Hello 中文'),dict(start=0,end=10)],captions=[dict(start=1,end=3,original='hello',en='Edited line',zh='修改后的字幕')],subtitles=True,normalize=True,font_size='large',color='yellow',position='bottom')

def test_manual_ownership_revision_and_immutable_render(client):
 pid=create(client).json()['id'];seed_plan(pid)
 url=f'/api/studio/projects/{pid}/manual'
 initial=client.get(url).json();assert initial['saved'] is False
 assert client.post(url+'/render',json={'revision':1}).status_code==422
 assert client.put(url,json={'revision':1,'edit':manual()}).status_code==200
 assert client.put(url,json={'revision':1,'edit':manual()}).status_code==409
 assert studio.state(pid)['plan']['recommendations'][0]['id']=='cut'
 assert client.post(url+'/render',json={'revision':2}).status_code==200
 assert client.put(url,json={'revision':2,'edit':manual()}).status_code==409
 with connect() as db:
  payload=json.loads(db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='studio_render'",(pid,)).fetchone()[0])
 assert payload['manual']['clips'][0]['text']=='Hello 中文'
 assert payload['decisions']==[] and payload['revision']==2
 app.dependency_overrides[current_user]=lambda:{'id':'v','email':'other@example.com'}
 assert client.get(url).status_code==404
 assert client.put(url,json={'revision':2,'edit':manual()}).status_code==404

def test_manual_ranges_and_no_approved_ai_needed(client):
 pid=create(client).json()['id'];seed_plan(pid);url=f'/api/studio/projects/{pid}/manual'
 bad=manual();bad['clips'][0]['end']=50
 assert client.put(url,json={'revision':1,'edit':bad}).status_code==422
 bad=manual();bad['clips'][0]['zoom']=float('inf')
 # JSON transport must stay finite; backend schema also forbids non-finite values.
 from backend.manual import Edit
 with pytest.raises(ValueError):Edit.model_validate(bad)
 assert client.put(url,json={'revision':1,'edit':manual()}).status_code==200
 assert not any(d['approved'] for d in studio.state(pid)['decisions'])
 assert client.post(url+'/render',json={'revision':2}).status_code==200

def test_manual_worker_never_calls_ai(client,monkeypatch):
 from backend import worker
 pid=create(client).json()['id'];seed_plan(pid)
 monkeypatch.setattr(worker.media,'render',lambda *args,**kw:{'metadata':{'duration':20},'timeline':[(20,30),(0,10)],'applied':[]})
 def forbidden(*args,**kwargs):pytest.fail('Manual render cannot call AI')
 monkeypatch.setattr(worker.ai,'review',forbidden)
 monkeypatch.setattr(worker.ai,'generate_broll',forbidden)
 worker.render_job(project(pid),{'recommendations':[],'manual':manual()})
 result=project(pid)
 assert result['status']=='needs_review'
 assert result['result']['qa_status']=='manual_review_required'
 assert result['result']['manual_transcript'][0]['en']=='Edited line'

def test_locked_clip_cannot_be_replaced_retimed_or_moved(client):
 pid=create(client).json()['id'];seed_plan(pid);url=f'/api/studio/projects/{pid}/manual'
 edit=client.get(url).json()['edit'];edit['clips'][0]['locked']=True
 assert client.put(url,json={'revision':1,'edit':edit}).status_code==200
 edit['clips'][0]['end']=20
 assert client.put(url,json={'revision':2,'edit':edit}).status_code==409
 edit['clips'][0]['end']=40;edit['clips'][0]['locked']=False
 assert client.put(url,json={'revision':2,'edit':edit}).status_code==200
 edit['clips'][0]['approved']=False
 assert client.put(url,json={'revision':3,'edit':edit}).status_code==200
 assert client.post(url+'/render',json={'revision':4}).status_code==422

def test_compiled_tracks_follow_approved_order_and_remap_subtitles():
 from backend.manual import Edit
 from backend.timeline import compile_timeline
 edit=Edit.model_validate({'clips':[{'id':'second','start':5,'end':8,'text':'Hook','zoom_end':2},{'id':'first','start':0,'end':2},{'id':'omit','start':2,'end':5,'approved':False}], 'subtitles':True,'captions':[{'start':6,'end':7,'en':'Hello','zh':'你好','original':'Hello'}]})
 timeline=compile_timeline(edit)
 assert timeline['duration']==5
 assert [c['id'] for c in timeline['tracks']['video']]==['second','first']
 assert timeline['tracks']['captions'][0]['start']==1
 assert timeline['tracks']['video'][0]['motion']['to'][0]==2

def test_import_approved_plan_preserves_only_selected_edits(client):
 pid=create(client).json()['id'];decisions=seed_plan(pid)
 decisions[0]['approved']=True
 assert client.put(f'/api/studio/projects/{pid}/plan',json={'revision':1,'decisions':decisions}).status_code==200
 r=client.post(f'/api/studio/projects/{pid}/manual/from-plan',json={'revision':2})
 assert r.status_code==200
 assert [(c['start'],c['end']) for c in r.json()['edit']['clips']]==[(0,2),(4,40)]

def test_ai_timeline_proposal_is_reviewed_scoped_and_not_auto_approved(client,monkeypatch):
 from backend import timeline_proposals as proposals
 from backend.manual import Clip
 pid=create(client).json()['id'];seed_plan(pid);url=f'/api/studio/projects/{pid}/manual'
 edit=client.get(url).json()['edit'];target=edit['clips'][0]['id']
 assert client.put(url,json={'revision':1,'edit':edit}).status_code==200
 endpoint=f'/api/studio/projects/{pid}/timeline-proposals'
 r=client.post(endpoint,json={'revision':2,'clip_id':target,'instruction':'Use a gentle push-in.'});assert r.status_code==202
 result=proposals.Proposal(clip=Clip(id='wrong',start=0,end=20,zoom_end=1.5,approved=True,locked=True),reason={'en':'Closer view','zh':'更近的画面'})
 monkeypatch.setattr(proposals.ai,'json_call',lambda *args,**kwargs:result)
 proposals.run_job(project(pid),{'id':r.json()['id']})
 with connect() as db:db.execute("UPDATE jobs SET status='complete' WHERE project_id=?",(pid,))
 assert client.get(url).json()['edit']['clips'][0]['end']==40
 assert client.post(endpoint+'/'+r.json()['id']+'/accept',json={'revision':2}).status_code==200
 updated=client.get(url).json()['edit']['clips'][0]
 assert updated['id']==target and updated['end']==20 and updated['approved'] is False and updated['locked'] is False
 assert client.post(endpoint+'/'+r.json()['id']+'/accept',json={'revision':2}).status_code==409

def test_ai_clip_replacement_rejects_mid_sentence_cut():
 from backend.manual import Clip,Edit
 from backend.timeline_proposals import Proposal,validate_proposal
 snapshot={'edit':Edit(clips=[Clip(id='target',start=0,end=10)]).model_dump(),'transcript':[{'start':2,'end':5}]}
 proposal=Proposal(clip=Clip(start=3,end=10),reason={'en':'Trim','zh':'剪辑'})
 with pytest.raises(ValueError,match='analysis_timestamps_invalid'):
  validate_proposal(proposal,snapshot,'target',10)
 proposal.clip.start=5
 assert validate_proposal(proposal,snapshot,'target',10).clip.start==5

def test_visual_cards_validate_timing_and_compile_output():
 from backend.manual import Edit,check
 from backend.timeline import compile_timeline
 card={'kind':'comparison','start':1,'end':3,'title':{'en':'Price','zh':'价格'},'primary':{'en':'100','zh':'100'},'secondary':{'en':'200','zh':'200'},'source':{'en':'Owner data','zh':'业主资料'}}
 edit=Edit.model_validate({'clips':[{'start':5,'end':9,'card':card},{'start':0,'end':2,'approved':False}]})
 check(edit,10)
 assert compile_timeline(edit)['tracks']['inserts'][0]['start']==1
 edit.clips[0].card.end=5
 with pytest.raises(Exception):check(edit,10)
 edit.clips[0].card.end=3;edit.clips[0].card.secondary=None
 with pytest.raises(Exception):check(edit,10)

def test_cutaway_timing_compiles_and_invalid_source_is_rejected():
 from backend.manual import Edit,check
 from backend.timeline import compile_timeline
 edit=Edit.model_validate({'clips':[{'start':5,'end':8,'cutaway':{'start':1,'end':2,'source_start':0}}]})
 check(edit,10)
 insert=compile_timeline(edit)['tracks']['cutaways'][0]
 assert (insert['start'],insert['end'],insert['source_start'],insert['audio'])==(1,2,0,'base_source')
 edit.clips[0].cutaway.source_start=10
 with pytest.raises(Exception):check(edit,10)
