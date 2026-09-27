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
    assert abs(media.probe(before)['duration']-1)<.08
    previous_audio=subprocess.check_output(['ffmpeg','-v','error','-i',str(before),'-map','0:a','-f','s16le','-'])
    assert previous_audio==original_audio
    result=media.probe(after)
    assert abs(result['duration']-1)<.08 and result['has_audio']
    audio=subprocess.check_output(['ffmpeg','-v','error','-i',str(after),'-map','0:a','-f','s16le','-'])
    assert audio==original_audio
    pixel=subprocess.check_output(['ffmpeg','-v','error','-ss','0.7','-i',str(after),'-vf','scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
    assert pixel[2]>180 and pixel[0]<60


def test_transition_blends_before_boundary_without_extending_source(tmp_path):
    before=tmp_path/'before.mp4';after=tmp_path/'after.mp4'
    media.ffmpeg('-f','lavfi','-i','testsrc2=s=160x240:r=30:d=1','-c:v','libx264',before)
    media.ffmpeg('-f','lavfi','-i','color=blue:s=160x240:r=30:d=1','-c:v','libx264',after)
    def frame(path,t):
        return subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(path),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
    old_tail=frame(before,.96)
    apply(before,after,'crossfade',1)
    new_tail=frame(before,.96)
    assert sum(abs(a-b) for a,b in zip(old_tail,new_tail))/len(old_tail)>10
    assert not media.probe(before)['has_audio'] and not media.probe(after)['has_audio']
    assert abs(media.probe(before)['duration']+media.probe(after)['duration']-2)<.08
    assert not list(tmp_path.glob('*.transition*.mp4'))

def test_measured_blend_runs_past_the_default_side(tmp_path):
    def pair(name):
        before = tmp_path / f'{name}-before.mp4'
        after = tmp_path / f'{name}-after.mp4'
        for path, color in ((before, 'black'), (after, '0xE8E4DC')):
            media.ffmpeg('-f', 'lavfi', '-i', f'color={color}:s=160x240:d=4:r=30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', path)
        return before, after

    def level(path):
        raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', '3.5', '-i', str(path), '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
        return sum(raw) / len(raw)

    short_before, short_after = pair('short')
    long_before, long_after = pair('long')
    apply(short_before, short_after, 'crossfade', 4)
    apply(long_before, long_after, 'crossfade', 4, 1.2)
    assert level(long_before) > level(short_before) + 10
