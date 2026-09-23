import subprocess
import pytest
from backend.visuals import VisualCard,write_card
from backend.manual import Clip,Edit
from backend.media import ass_available,ffmpeg,probe,render
from backend.schemas import Analysis
T={'en':'Trip','zh':'旅程'}
def card():
 return VisualCard(kind='timeline',start=1,end=3,title=T,primary=T,source=T,milestones=[{'when':{'en':'2024','zh':'2024年'},'label':{'en':'Start','zh':'开始'}},{'when':{'en':'2025','zh':'2025年'},'label':{'en':'Arrival','zh':'抵达'}}])
def test_milestone_validation_and_order(tmp_path):
 c=card();out=tmp_path/'timeline.ass';write_card(out,c.model_dump(),'zh',320,568)
 text=out.read_text();assert text.index('2024年')<text.index('2025年') and 'Arrival' not in text
 with pytest.raises(ValueError):VisualCard.model_validate(c.model_dump()|{'milestones':[]})
 with pytest.raises(ValueError):VisualCard.model_validate(c.model_dump()|{'kind':'number'})
 with pytest.raises(ValueError):VisualCard.model_validate(c.model_dump()|{'items':[{'label':T,'value':1}]})
@pytest.mark.skipif(not ass_available(),reason='FFmpeg ass filter required')
def test_event_timeline_is_burned_only_in_its_interval(tmp_path):
 src=tmp_path/'source.mp4';ffmpeg('-f','lavfi','-i','color=red:s=320x568:d=4:r=12','-c:v','libx264',src)
 analysis=Analysis(summary=T,strongest_moment=T,audience=T,scores=[dict(category='clarity',value=50,reason=T)],scenes=[dict(start=0,end=4,title=T,observation=T,role='context')],transcript=[],recommendations=[],uncertainties=[])
 result=render(src,tmp_path,probe(src),analysis,[],'zh','original',manual=Edit(clips=[Clip(start=0,end=4,card=card())]).model_dump())
 def pixel(t):return subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(tmp_path/'result.mp4'),'-vf','crop=2:2:36:260,scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
 assert pixel(.3)[0]>180 and pixel(2)[1]>100 and pixel(3.5)[0]>180
 assert result['director_timeline']['tracks']['inserts'][0]['kind']=='timeline'
 ffmpeg('-ss',2,'-i',tmp_path/'result.mp4','-frames:v','1',tmp_path/'preview.png')
