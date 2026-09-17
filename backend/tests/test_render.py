import shutil
from pathlib import Path
import pytest
from backend.media import ffmpeg,probe,render,run
from backend.schemas import Analysis,Recommendation

T={'en':'Synthetic fixture, not AI analysis','zh':'合成测试素材，非 AI 分析'}
def recommendation(id,action,start,end):
    return Recommendation(id=id,action=action,start=start,end=end,title=T,evidence=T,improvement=T,category='hook',confidence=1,auto_apply=True,generation_prompt='')

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg required')
def test_real_render_timeline_captions_and_audio(tmp_path):
    src=tmp_path/'source.mp4'
    ffmpeg('-f','lavfi','-i','color=red:s=320x240:d=2:r=30','-f','lavfi','-i','color=green:s=320x240:d=3:r=30',
           '-f','lavfi','-i','color=blue:s=320x240:d=3:r=30','-f','lavfi','-i','sine=frequency=440:duration=8',
           '-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]','-map','[v]','-map','3:a','-c:v','libx264','-c:a','aac',src)
    a=Analysis(summary=T,strongest_moment=T,audience=T,scores=[{'category':'hook','value':50,'reason':T}],
     scenes=[{'start':0,'end':8,'title':T,'observation':T,'role':'context'}],
     transcript=[{'start':1,'end':2,'original':'Test captions','en':'Test captions','zh':'测试中文字幕'},
                 {'start':5,'end':7,'original':'Opening scene','en':'Opening scene','zh':'开场画面'}],
     recommendations=[],uncertainties=[T])
    selected=[recommendation('cut','remove',0,1),recommendation('hook','move_to_front',5,8),
              recommendation('subtitles','captions',0,8),recommendation('audio','normalize_audio',0,8)]
    result=render(src,tmp_path,probe(src),a,selected,'zh','original')
    assert abs(result['metadata']['duration']-7)<.2
    assert result['metadata']['has_audio']
    assert '开场画面' in (tmp_path/'captions.ass').read_text()
    # First scene must actually be BLUE in the rendered file, not the original red opening.
    import subprocess
    first=subprocess.check_output(['ffmpeg','-v','error','-ss','0.3','-i',str(tmp_path/'result.mp4'),'-vf','crop=20:20:0:0,scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
    assert first[2]>180 and first[0]<60
    # After the 3-second hook, retained original footage resumes RED.
    next_pixel=subprocess.check_output(['ffmpeg','-v','error','-ss','3.3','-i',str(tmp_path/'result.mp4'),'-vf','crop=20:20:0:0,scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
    assert next_pixel[0]>180 and next_pixel[2]<60

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg required')
def test_manual_render_reorders_crops_and_burns_safe_text(tmp_path):
    import subprocess
    src=tmp_path/'source.mp4'
    ffmpeg('-f','lavfi','-i','color=red:s=320x240:d=2:r=30','-f','lavfi','-i','color=blue:s=320x240:d=2:r=30',
           '-f','lavfi','-i','sine=frequency=440:duration=4','-filter_complex','[0:v]drawbox=x=160:y=0:w=160:h=240:color=lime:t=fill[left];[left][1:v]concat=n=2:v=1:a=0[v]',
           '-map','[v]','-map','2:a','-c:v','libx264','-c:a','aac',src)
    a=Analysis(summary=T,strongest_moment=T,audience=T,scores=[dict(category='clarity',value=50,reason=T)],scenes=[dict(start=0,end=4,title=T,observation=T,role='context')],transcript=[],recommendations=[],uncertainties=[])
    edit={'clips':[{'start':2,'end':4,'zoom':2,'x':.25,'y':.75,'text':'新开场 {\\pos(1,1)}'},{'start':0,'end':1,'zoom':2,'x':1,'y':.5}],
          'captions':[{'start':2,'end':3,'original':'Test','en':'Edited','zh':'修改字幕'}], 'subtitles':True,'normalize':True,'font_size':'large','color':'yellow','position':'bottom'}
    result=render(src,tmp_path,probe(src),a,[],'zh','original',manual=edit)
    assert abs(result['metadata']['duration']-3)<.2 and result['metadata']['has_audio']
    assert result['timeline']==[(2,4),(0,1)]
    assert '修改字幕' in (tmp_path/'captions.ass').read_text()
    assert '&H0000FFFF' in (tmp_path/'captions.ass').read_text()
    assert '{\\pos' not in (tmp_path/'title-0.ass').read_text()
    def pixel(t):return subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(tmp_path/'result.mp4'),'-vf','crop=20:20:0:0,scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
    assert pixel(.3)[2]>180 and pixel(2.3)[1]>180 and pixel(2.3)[0]<60

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg required')
def test_animated_reframe_and_fade_are_real_pixels(tmp_path):
    import subprocess
    src=tmp_path/'motion.mp4'
    ffmpeg('-f','lavfi','-i','color=red:s=320x240:d=3:r=30','-vf','drawbox=x=160:y=0:w=160:h=240:color=lime:t=fill','-c:v','libx264',src)
    a=Analysis(summary=T,strongest_moment=T,audience=T,scores=[dict(category='clarity',value=50,reason=T)],scenes=[dict(start=0,end=3,title=T,observation=T,role='context')],transcript=[],recommendations=[],uncertainties=[])
    result=render(src,tmp_path,probe(src),a,[],'en','original',manual={'clips':[{'start':0,'end':3,'zoom':1,'zoom_end':2,'x':1,'x_end':1,'transition':'fade'}]})
    def pixel(t):return subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(tmp_path/'result.mp4'),'-vf','crop=10:10:20:100,scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
    assert max(pixel(0))<20
    assert pixel(.4)[0]>180
    assert pixel(2.7)[1]>150 and pixel(2.7)[0]<80
    assert abs(result['metadata']['duration']-3)<.2

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg required')
def test_bilingual_card_is_timed_and_burned(tmp_path):
 import subprocess
 src=tmp_path/'card-source.mp4'
 ffmpeg('-f','lavfi','-i','color=red:s=320x568:d=4:r=30','-c:v','libx264',src)
 a=Analysis(summary=T,strongest_moment=T,audience=T,scores=[dict(category='clarity',value=50,reason=T)],scenes=[dict(start=0,end=4,title=T,observation=T,role='context')],transcript=[],recommendations=[],uncertainties=[])
 card={'kind':'comparison','start':1,'end':3,'title':{'en':'Price','zh':'价格'},'primary':{'en':'100','zh':'100'},'secondary':{'en':'200','zh':'200'},'source':{'en':'Owner data','zh':'业主资料'}}
 result=render(src,tmp_path,probe(src),a,[],'zh','original',manual={'clips':[{'start':0,'end':4,'card':card}]})
 assert '业主资料' in (tmp_path/'card-0.ass').read_text()
 assert 'Owner data' not in (tmp_path/'card-0.ass').read_text()
 def pixel(t):return subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(tmp_path/'result.mp4'),'-vf','crop=10:10:25:210,scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
 assert pixel(.3)[0]>180 and pixel(3.5)[0]>180
 assert pixel(2)[0]<80
 assert result['director_timeline']['tracks']['inserts'][0]['start']==1

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg required')
def test_cutaway_changes_picture_but_preserves_base_speech(tmp_path):
 import subprocess,array
 src=tmp_path/'cutaway-source.mp4'
 ffmpeg('-f','lavfi','-i','color=red:s=320x568:d=3:r=30','-f','lavfi','-i','color=blue:s=320x568:d=3:r=30','-f','lavfi','-i','sine=frequency=440:duration=3','-f','lavfi','-i','sine=frequency=880:duration=3','-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v];[2:a][3:a]concat=n=2:v=0:a=1[a]','-map','[v]','-map','[a]','-c:v','libx264','-c:a','aac',src)
 a=Analysis(summary=T,strongest_moment=T,audience=T,scores=[dict(category='clarity',value=50,reason=T)],scenes=[dict(start=0,end=6,title=T,observation=T,role='context')],transcript=[],recommendations=[],uncertainties=[])
 result=render(src,tmp_path,probe(src),a,[],'en','original',manual={'clips':[{'start':0,'end':3,'cutaway':{'start':1,'end':2,'source_start':4}}]})
 def pixel(t):return subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(tmp_path/'result.mp4'),'-vf','scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
 assert pixel(.5)[0]>180 and pixel(1.5)[2]>180 and pixel(2.5)[0]>180
 raw=subprocess.check_output(['ffmpeg','-v','error','-ss','1.3','-i',str(tmp_path/'result.mp4'),'-t','0.25','-vn','-ac','1','-ar','44100','-f','s16le','-'])
 samples=array.array('h',raw);crossings=sum(x<=0<y for x,y in zip(samples,samples[1:]))
 assert 100<crossings<120  # Original 440 Hz; inserted footage has 880 Hz.
 assert result['director_timeline']['tracks']['cutaways'][0]['source_start']==4

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg required')
def test_external_library_asset_renders_only_during_insert(tmp_path):
 import subprocess
 src=tmp_path/'base.mp4';asset=tmp_path/'library.mp4'
 ffmpeg('-f','lavfi','-i','color=red:s=320x568:d=3:r=30','-c:v','libx264',src)
 ffmpeg('-f','lavfi','-i','color=lime:s=640x360:d=2:r=30','-c:v','libx264',asset)
 a=Analysis(summary=T,strongest_moment=T,audience=T,scores=[dict(category='clarity',value=50,reason=T)],scenes=[dict(start=0,end=3,title=T,observation=T,role='context')],transcript=[],recommendations=[],uncertainties=[])
 ident='a'*32
 result=render(src,tmp_path,probe(src),a,[],'en','original',manual={'clips':[{'start':0,'end':3,'external_broll':{'asset_id':ident,'start':1,'end':2,'source_start':0}}]},asset_paths={ident:asset})
 def pixel(t):return subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(tmp_path/'result.mp4'),'-vf','scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
 assert pixel(.5)[0]>180 and pixel(1.5)[1]>180 and pixel(2.5)[0]>180
 assert result['director_timeline']['tracks']['cutaways'][0]['asset_id']==ident
