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
def test_a_horn_and_street_noise_drop_and_the_command_uses_rnnoise(tmp_path, monkeypatch):
    commands = []
    real = media.ffmpeg

    def wrapped(*args, timeout=600):
        commands.append([str(arg) for arg in args])
        return real(*args, timeout=timeout)

    monkeypatch.setattr(media, 'ffmpeg', wrapped)
    noisy = tmp_path / 'noisy.wav'
    media.ffmpeg(
        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=2',
        '-f', 'lavfi', '-i', 'sine=frequency=40:sample_rate=48000:duration=2',
        '-f', 'lavfi', '-i', 'anoisesrc=color=white:sample_rate=48000:duration=2:amplitude=0.15',
        '-filter_complex', '[0:a]volume=0.8,apulsator=hz=2:amount=1[horn];[horn][1:a][2:a]amix=inputs=3:duration=first:normalize=0,volume=0.6',
        '-c:a', 'pcm_s16le', noisy,
    )
    cleaned = apply(noisy, tmp_path / 'out')
    low_in, low_out = _rms(noisy, 'lowpass=f=70'), _rms(cleaned, 'lowpass=f=70')
    horn_in, horn_out = _rms(noisy, 'bandpass=f=440:width_type=h:w=40'), _rms(cleaned, 'bandpass=f=440:width_type=h:w=40')
    hiss_in, hiss_out = _rms(noisy, 'highpass=f=6000'), _rms(cleaned, 'highpass=f=6000')
    assert low_out < low_in * 0.5
    assert horn_out < horn_in * 0.25
    assert hiss_out < hiss_in * 0.35
    joined = ' '.join(' '.join(command) for command in commands)
    assert FILTER in joined
    assert 'arnndn' in joined and 'rnnoise-lq.rnnn' in joined
    assert 'afftdn' not in joined and 'sidechaincompress' not in joined


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('say'), reason='FFmpeg and say required')
def test_spoken_voice_stays_while_hiss_drops(tmp_path):
    speech = tmp_path / 'speech.aiff'
    subprocess.run(['say', '-o', str(speech), 'Three shareholders meet to review the company registration.'], check=True)
    mixed = tmp_path / 'mixed.wav'
    media.ffmpeg(
        '-i', speech,
        '-f', 'lavfi', '-i', 'anoisesrc=color=white:sample_rate=48000:duration=6:amplitude=0.2',
        '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=first:normalize=0,volume=0.8',
        '-c:a', 'pcm_s16le', '-ar', '48000', mixed,
    )
    cleaned = apply(mixed, tmp_path / 'out')
    voice = 'highpass=f=200,lowpass=f=3000'
    voice_in, voice_out = _rms(speech, voice), _rms(cleaned, voice)
    hiss_in, hiss_out = _rms(mixed, 'highpass=f=6000'), _rms(cleaned, 'highpass=f=6000')
    assert voice_out > voice_in * 0.45
    assert hiss_out < hiss_in * 0.35
