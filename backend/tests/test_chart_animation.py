import subprocess
import pytest
from backend.visuals import VisualCard
from backend.manual import Edit,Clip
from backend.media import ass_available,ffmpeg,probe,render
from backend.schemas import Analysis
T={'en':'Verified data','zh':'已核实数据'}
def card(kind='bar_chart'):
 return VisualCard(kind=kind,start=1,end=3,animation='grow',animation_seconds=1,title=T,primary=T,source=T,items=[{'label':T,'value':10},{'label':T,'value':20}])
def test_animation_scope_and_duration_validation():
 c=card()
 for changes in [{'kind':'number','items':[]},{'animation_seconds':2},{'animation_seconds':float('nan')}]:
  with pytest.raises(ValueError):VisualCard.model_validate(c.model_dump()|changes)
 assert VisualCard.model_validate(c.model_dump()|{'animation':'none'}).animation=='none'

@pytest.mark.skipif(not ass_available(),reason='FFmpeg ass filter required')
@pytest.mark.parametrize('kind',['bar_chart','ranking'])
def test_bar_growth_is_visible_in_rendered_frames(tmp_path,kind):
 src=tmp_path/'source.mp4';ffmpeg('-f','lavfi','-i','color=red:s=320x568:d=4:r=30','-c:v','libx264',src)
 a=Analysis(summary=T,strongest_moment=T,audience=T,scores=[dict(category='clarity',value=50,reason=T)],scenes=[dict(start=0,end=4,title=T,observation=T,role='context')],transcript=[],recommendations=[],uncertainties=[])
 result=render(src,tmp_path,probe(src),a,[],'en','original',manual=Edit(clips=[Clip(start=0,end=4,card=card(kind))]).model_dump())
 def pixel(t,x):return subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(tmp_path/'result.mp4'),'-vf',f'crop=2:2:{x}:252,scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
 x=140 if kind=='bar_chart' else 240
 assert pixel(1.25,x)[1]<80 and pixel(2.2,x)[1]>150
 assert pixel(.5,x)[0]>180 and pixel(3.5,x)[0]>180
 assert result['director_timeline']['tracks']['inserts'][0]['animation']=='grow'
 for t in [1.25,2.2]:ffmpeg('-ss',t,'-i',tmp_path/'result.mp4','-frames:v','1',tmp_path/f'frame-{t}.png')
