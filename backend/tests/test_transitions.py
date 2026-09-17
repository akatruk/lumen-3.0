import subprocess
import pytest
from backend import media
from backend.transitions import apply,KINDS

@pytest.mark.parametrize('kind',list(KINDS))
def test_transition_keeps_incoming_duration_audio_and_eventual_image(tmp_path,kind):
    before=tmp_path/'before.mp4';after=tmp_path/'after.mp4'
    for path,color in [(before,'red'),(after,'blue')]:
        media.ffmpeg('-f','lavfi','-i',f'color={color}:s=160x240:d=1:r=30','-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','libx264','-c:a','aac',path)
    original_audio=subprocess.check_output(['ffmpeg','-v','error','-i',str(after),'-map','0:a','-f','s16le','-'])
    apply(before,after,kind,1)
    result=media.probe(after)
    assert abs(result['duration']-1)<.08 and result['has_audio']
    audio=subprocess.check_output(['ffmpeg','-v','error','-i',str(after),'-map','0:a','-f','s16le','-'])
    assert audio==original_audio
    pixel=subprocess.check_output(['ffmpeg','-v','error','-ss','0.7','-i',str(after),'-vf','scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
    assert pixel[2]>180 and pixel[0]<60
