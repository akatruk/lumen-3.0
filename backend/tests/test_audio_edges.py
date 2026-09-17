import array,math,subprocess
from types import SimpleNamespace
import pytest
from backend import media
from backend.manual import Edit

@pytest.mark.parametrize('has_audio',[True,False])
def test_audio_edge_smoothing_preserves_timeline_and_reduces_edge_energy(tmp_path,has_audio):
    src=tmp_path/'source.mp4'
    inputs=['-f','lavfi','-i','color=blue:s=160x240:r=30:d=2']
    if has_audio:inputs+=['-f','lavfi','-i','sine=frequency=440:duration=2']
    media.ffmpeg(*inputs,'-c:v','libx264','-c:a','aac',src)
    meta=media.probe(src);results=[]
    for fade in [0,100]:
        folder=tmp_path/str(fade);folder.mkdir()
        edit=Edit(clips=[{'start':0,'end':1,'audio_fade_ms':fade},{'start':1,'end':2,'audio_fade_ms':fade}])
        result=media.render(src,folder,meta,SimpleNamespace(transcript=[]),[],'en','original',manual=edit.model_dump())
        assert result['metadata']['has_audio']==has_audio
        assert abs(result['metadata']['duration']-2)<.1
        assert result['timeline']==[(0,1),(1,2)]
        assert result['director_timeline']['tracks']['video'][0]['audio_fade_ms']==fade
        if has_audio:
            samples=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(folder/'result.mp4'),'-map','0:a','-ac','1','-ar','48000','-f','f32le','-']))
            def rms(a,b):
                part=samples[int(a*48000):int(b*48000)]
                return math.sqrt(sum(x*x for x in part)/len(part))
            results.append((rms(.005,.025),rms(.4,.6)))
    if has_audio:
        assert results[1][0]<results[0][0]*.5
        assert abs(results[1][1]/results[0][1]-1)<.1
