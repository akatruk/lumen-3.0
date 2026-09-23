import array,subprocess
import pytest
from backend.media import ass_available
from backend.manual import Clip,Edit,check
from backend.timeline_proposals import Proposal,validate_proposal
from backend.timeline import compile_timeline
from backend.visuals import VisualCard
from backend.sound_effects import SoundEffect,mix
T={'en':'Source script','zh':'原脚本'}

def test_graphic_and_sound_proposals_only_change_their_layer():
 original=Clip(start=0,end=5,id='clip');snapshot={'mode':'visual_card','edit':Edit(clips=[original]).model_dump()}
 proposed=original.model_copy(deep=True);proposed.card=VisualCard(start=0,end=2,title=T,primary=T,source=T)
 result=Proposal(clip=proposed,reason=T)
 validate_proposal(result,snapshot,'clip',5)
 assert not result.clip.approved
 proposed.zoom=2
 with pytest.raises(ValueError):validate_proposal(result,snapshot,'clip',5)
 proposed=original.model_copy(deep=True);proposed.sound_effects=[SoundEffect(at=1)]
 result=Proposal(clip=proposed,reason=T);snapshot['mode']='sound_effects'
 validate_proposal(result,snapshot,'clip',5)
 proposed.card=VisualCard(start=0,end=2,title=T,primary=T,source=T)
 with pytest.raises(ValueError):validate_proposal(result,snapshot,'clip',5)

def test_sounds_are_bounded_and_follow_approved_clip_order():
 a=Clip(start=2,end=5,sound_effects=[SoundEffect(at=1)]);b=Clip(start=0,end=2,approved=False,sound_effects=[SoundEffect(at=0)])
 timeline=compile_timeline(Edit(clips=[b,a]))
 assert timeline['tracks']['sound_effects'][0]['at']==1
 a.sound_effects[0].at=2.8
 with pytest.raises(Exception):check(Edit(clips=[a]),5)

def test_sound_mix_is_audible_only_at_scheduled_time(tmp_path):
 from backend.media import ffmpeg,probe
 src=tmp_path/'source.mp4'
 ffmpeg('-f','lavfi','-i','color=red:s=160x240:d=3:r=12','-c:v','libx264',src)
 out=mix(src,tmp_path,[{'kind':'chime','at':1,'gain_db':-18}],3,False)
 assert probe(out)['has_audio'] and abs(probe(out)['duration']-3)<.1
 def energy(at):
  raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(at),'-i',str(out),'-t','0.15','-vn','-ac','1','-ar','48000','-f','s16le','-'])
  samples=array.array('h',raw);return sum(v*v for v in samples)/len(samples)
 assert energy(.3)<5 and energy(1.05)>10000 and energy(2)<5

from backend.tests.test_studio import client,create,seed_plan
from backend.db import connect,project
from backend import timeline_proposals as proposals

@pytest.mark.parametrize('mode',['visual_card','sound_effects'])
def test_creative_proposal_is_reviewed_and_saved_through_api(client,monkeypatch,mode):
 pid=create(client).json()['id'];seed_plan(pid);url=f'/api/studio/projects/{pid}/manual'
 state=client.get(url).json();edit=state['edit'];target=edit['clips'][0]['id']
 r=client.put(url,json={'revision':1,'edit':edit});assert r.status_code==200
 proposed=Clip.model_validate(edit['clips'][0])
 if mode=='visual_card':proposed.card=VisualCard(start=1,end=3,title=T,primary=T,source=T)
 else:proposed.sound_effects=[SoundEffect(at=1)]
 monkeypatch.setattr(proposals.ai,'json_call',lambda *a,**k:Proposal(clip=proposed,reason=T))
 base=f'/api/studio/projects/{pid}/timeline-proposals'
 r=client.post(base,json={'revision':2,'clip_id':target,'instruction':'Clarify the point','mode':mode});assert r.status_code==202,r.text
 proposals.run_job(project(pid),{'id':r.json()['id']})
 assert client.get(url).json()['edit']==Edit.model_validate(edit).model_dump()
 with connect() as db:db.execute("UPDATE jobs SET status='complete' WHERE project_id=?",(pid,))
 assert client.post(base+'/'+r.json()['id']+'/accept',json={'revision':2}).status_code==200
 saved=client.get(url).json()['edit']['clips'][0]
 assert saved['approved'] is False
 assert saved['card'] if mode=='visual_card' else saved['sound_effects']

def test_render_includes_only_approved_sound_decisions(tmp_path):
 from backend.media import ffmpeg,render,probe
 from backend.schemas import Analysis
 src=tmp_path/'source.mp4'
 ffmpeg('-f','lavfi','-i','color=red:s=160x240:d=3:r=12','-f','lavfi','-i','sine=frequency=440:duration=3','-c:v','libx264','-c:a','aac',src)
 analysis=Analysis(summary=T,strongest_moment=T,audience=T,scores=[dict(category='clarity',value=50,reason=T)],scenes=[dict(start=0,end=3,title=T,observation=T,role='context')],transcript=[],recommendations=[],uncertainties=[])
 edit=Edit(clips=[Clip(start=0,end=3,sound_effects=[SoundEffect(at=1)]),Clip(start=0,end=1,approved=False,sound_effects=[SoundEffect(at=0)])])
 result=render(src,tmp_path,probe(src),analysis,[],'en','original',manual=edit.model_dump())
 assert result['metadata']['has_audio'] and abs(result['metadata']['duration']-3)<.2
 assert len(result['director_timeline']['tracks']['sound_effects'])==1

@pytest.mark.parametrize('kind',['bar_chart','ranking'])
def test_data_graphics_have_validated_values_and_bilingual_output(tmp_path,kind):
 from backend.visuals import write_card
 card=VisualCard(kind=kind,start=1,end=3,title=T,primary=T,source=T,items=[{'label':{'en':'Small','zh':'小'},'value':10},{'label':{'en':'Large','zh':'大'},'value':20}])
 out=tmp_path/'chart.ass';write_card(out,card.model_dump(),'zh',320,568)
 text=out.read_text();assert '小  10' in text and '大  20' in text and 'Small' not in text
 if kind=='ranking':assert text.index('1. 大')<text.index('2. 小')
 with pytest.raises(ValueError):VisualCard.model_validate(card.model_dump()|{'items':[]})
 with pytest.raises(ValueError):VisualCard.model_validate(card.model_dump()|{'items':[{'label':T,'value':float('nan')},{'label':T,'value':1}]})

@pytest.mark.skipif(not ass_available(),reason='FFmpeg ass filter required')
@pytest.mark.parametrize('kind',['bar_chart','ranking'])
def test_chart_is_rendered_with_proportional_bars(tmp_path,kind):
 from backend.media import ffmpeg,probe,render
 from backend.schemas import Analysis
 src=tmp_path/'source.mp4';ffmpeg('-f','lavfi','-i','color=red:s=320x568:d=4:r=12','-c:v','libx264',src)
 card=VisualCard(kind=kind,start=1,end=3,title=T,primary=T,source=T,items=[{'label':T,'value':10},{'label':T,'value':20}])
 analysis=Analysis(summary=T,strongest_moment=T,audience=T,scores=[dict(category='clarity',value=50,reason=T)],scenes=[dict(start=0,end=4,title=T,observation=T,role='context')],transcript=[],recommendations=[],uncertainties=[])
 render(src,tmp_path,probe(src),analysis,[],'zh','original',manual=Edit(clips=[Clip(start=0,end=4,card=card)]).model_dump())
 def pixel(x,y,t=2):return subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(tmp_path/'result.mp4'),'-vf',f'crop=2:2:{x}:{y},scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
 # Top row bar: half-width for chart, full width for descending ranking.
 assert pixel(80,252)[1]>150
 assert (pixel(220,252)[1]>150)==(kind=='ranking')
 assert pixel(80,252,.3)[0]>180 and pixel(80,252,3.5)[0]>180
 ffmpeg('-ss',2,'-i',tmp_path/'result.mp4','-frames:v','1',tmp_path/'preview.png')
