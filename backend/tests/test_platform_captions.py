import pytest
from backend import media
from backend.media import ass_available
from backend.platform_captions import caption_source,write
from backend.tests.test_platform_titles import variant
from backend.schemas import Caption


def test_caption_mapping_reorders_source_and_master_without_duplicate_layers(tmp_path):
    caption=Caption(start=5,end=7,original='Test',en='Test',zh='测试')
    master={'caption_master':True,'captions_enabled':True,'caption_transcript':[caption.model_dump()], 'timeline':[(4,8),(0,4)],'caption_style':{}}
    path=tmp_path/'captions.ass'
    assert write(path,master,variant(caption_mode='custom',caption_color='yellow',caption_size='large'),'zh',1080,1920,[(4,8),(0,4)])
    text=path.read_text()
    assert '0:00:05.00,0:00:07.00' in text and '测试' in text and '&H0000FFFF' in text
    assert not write(path,master,variant(caption_mode='off'),'en',1080,1920,[(0,8)])
    master['captions_enabled']=False
    assert not write(path,master,variant(),'en',1080,1920,[(0,8)])
    assert write(path,master,variant(caption_mode='custom'),'en',1080,1920,[(0,8)])


def test_legacy_and_missing_companion_fail_safely(tmp_path):
    source=tmp_path/'result.mp4';source.touch()
    assert caption_source(source,{},variant())==source
    with pytest.raises(ValueError):caption_source(source,{},variant(caption_mode='off'))
    with pytest.raises(ValueError):caption_source(source,{'caption_master':True,'captions_enabled':True},variant())
    assert caption_source(source,{'caption_master':True,'captions_enabled':False},variant())==source

@pytest.mark.skipif(not ass_available(),reason='FFmpeg ass filter required')
@pytest.mark.parametrize('language',['en','zh'])
def test_clean_companion_retains_final_audio_without_captions(tmp_path,language):
    import subprocess
    from backend.manual import Edit,Clip
    from backend.tests.test_studio import plan
    source=tmp_path/'source.mp4'
    media.ffmpeg('-f','lavfi','-i','color=black:s=320x240:d=2:r=30','-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','libx264','-c:a','aac',source)
    edit=Edit(clips=[Clip(start=0,end=2,approved=True)],subtitles=True,normalize=True,captions=[Caption(start=0,end=2,original='Caption',en='Caption',zh='测试字幕')])
    output=tmp_path/'render';output.mkdir()
    result=media.render(source,output,media.probe(source),plan(),[],language,'original',manual=edit.model_dump(),preserve_caption_master=True)
    assert result['caption_master'] and result['captions_enabled']
    clean=caption_source(output/'result.mp4',result,variant())
    assert abs(media.probe(clean)['duration']-2)<.1
    def audio(path):return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a','-f','hash','-hash','sha256','-'])
    assert audio(clean)==audio(output/'result.mp4')
    def pixels(path):return subprocess.check_output(['ffmpeg','-v','error','-ss','0.5','-i',str(path),'-frames:v','1','-pix_fmt','gray','-f','rawvideo','-'])
    assert sum(pixels(output/'result.mp4'))>sum(pixels(clean))+10000
