import shutil
import subprocess
import wave
import pytest
from backend import dubbing_audio as audio, media

pytestmark = pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg required')


def test_dub_preserves_picture_duration_and_silence(tmp_path):
    source = tmp_path / 'master.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=c=blue:s=160x240:r=25:d=4', '-f', 'lavfi', '-i', 'sine=frequency=200:duration=4', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', source)
    raw = tmp_path / '0.mp3'
    media.ffmpeg('-f', 'lavfi', '-i', 'sine=frequency=700:duration=1.2', raw)
    audio.fit_phrase(raw, tmp_path / '0.wav', 1)
    phrases = [{'start': 1, 'end': 2, 'text': 'Test'}]
    meta = audio.assemble(source, tmp_path, phrases, 4)
    assert abs(meta['duration'] - 4) < .1 and meta['has_audio']
    with wave.open(str(tmp_path / 'voice.wav')) as w:
        pcm = w.readframes(w.getnframes())
    assert not any(pcm[:48000*2]) and any(pcm[48000*2:48000*4]) and not any(pcm[48000*4:])
    def picture(path):
        return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v:0', '-c', 'copy', '-f', 'hash', '-hash', 'sha256', '-'])
    assert picture(source) == picture(tmp_path / 'video.mp4')


def test_overlong_phrase_is_never_silently_truncated(tmp_path):
    raw = tmp_path / 'long.mp3'
    media.ffmpeg('-f', 'lavfi', '-i', 'sine=frequency=700:duration=3', raw)
    with pytest.raises(ValueError, match='dubbing_speech_too_long'):
        audio.fit_phrase(raw, tmp_path / 'out.wav', 1)
    assert not (tmp_path / 'out.wav').exists()
