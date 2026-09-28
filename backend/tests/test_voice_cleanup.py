import array
import math
import shutil
import subprocess

import pytest

from backend import media
from backend.manual import Clip, Edit
from backend.voice_cleanup import FILTER, apply, default_enabled, prepare_track


def _rms(path, audio_filter):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-af', audio_filter, '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'])
    samples = array.array('f')
    samples.frombytes(raw)
    assert samples
    return math.sqrt(sum(x * x for x in samples) / len(samples))


def test_missing_choice_stays_off_and_an_explicit_choice_round_trips():
    assert Edit(clips=[Clip(start=0, end=1)]).voice_cleanup is False
    saved = Edit(clips=[Clip(start=0, end=1)], voice_cleanup=True).model_dump()
    assert Edit.model_validate(saved).voice_cleanup is True
    assert Edit.model_validate({'clips': [{'start': 0, 'end': 1}]}).voice_cleanup is False


def test_new_style_match_and_voiceover_edits_start_cleaned():
    from backend.style_match import build
    edit, _report = build([], 8, [], True)
    assert edit['voice_cleanup'] is True
    assert default_enabled(style_match=True) is True
    assert default_enabled(has_voiceover=True) is True
    assert default_enabled() is False


def test_cleanup_is_skipped_when_the_edit_leaves_it_off(tmp_path):
    source = tmp_path / 'voice.wav'
    source.write_bytes(b'unchanged')
    assert prepare_track(source, tmp_path, {'voice_cleanup': False}, True) is source
    assert prepare_track(source, tmp_path, None, True) is source
    assert prepare_track(source, tmp_path, {'voice_cleanup': True}, False) is source


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg required')
def test_noisy_tone_loses_energy_outside_speech_and_the_command_uses_afftdn(tmp_path, monkeypatch):
    commands = []
    real = media.ffmpeg

    def wrapped(*args, timeout=600):
        commands.append([str(arg) for arg in args])
        return real(*args, timeout=timeout)

    monkeypatch.setattr(media, 'ffmpeg', wrapped)
    noisy = tmp_path / 'noisy.wav'
    media.ffmpeg(
        '-f', 'lavfi', '-i', 'sine=frequency=200:sample_rate=48000:duration=2',
        '-f', 'lavfi', '-i', 'sine=frequency=40:sample_rate=48000:duration=2',
        '-f', 'lavfi', '-i', 'anoisesrc=color=white:sample_rate=48000:duration=2:amplitude=0.15',
        '-filter_complex', '[0:a][1:a][2:a]amix=inputs=3:duration=first:normalize=0,volume=0.5',
        '-c:a', 'pcm_s16le', noisy,
    )
    cleaned = apply(noisy, tmp_path / 'out')
    low_in, low_out = _rms(noisy, 'lowpass=f=70'), _rms(cleaned, 'lowpass=f=70')
    speech_in, speech_out = _rms(noisy, 'highpass=f=150,lowpass=f=400'), _rms(cleaned, 'highpass=f=150,lowpass=f=400')
    assert low_out < low_in * 0.5
    assert speech_out > speech_in * 0.5
    joined = ' '.join(' '.join(command) for command in commands)
    assert FILTER in joined
    assert 'arnndn' not in joined
    assert 'sidechaincompress' not in joined
