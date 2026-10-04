"""Clean host speech before a licensed music bed is mixed under it.

Traffic horns sit in the same band as speech, so a mild FFT denoise leaves them
in the track. The chain is a high-pass plus RNNoise (leavened-quisling), which
keeps the voice and drops street noise, horns, and hiss. Music is mixed later.
"""
import json
from pathlib import Path

# Public RNNoise weights for a voice against general noise (traffic, horns, hiss).
# https://github.com/GregorR/rnnoise-models leavened-quisling-2018-08-31
MODEL = Path(__file__).resolve().parent / 'assets' / 'rnnoise-lq.rnnn'


def audio_filter():
    """High-pass, then RNNoise at 48 kHz. The model path is required."""
    if not MODEL.is_file():
        raise RuntimeError('rnnoise_model_missing')
    return f'highpass=f=100,aresample=48000,arnndn=m={MODEL}:mix=1'


FILTER = audio_filter()


def default_enabled(style_match=False, has_voiceover=False):
    """New style-match edits and projects that already have a voiceover start cleaned."""
    return bool(style_match or has_voiceover)


def has_voiceover(db, project):
    try:
        from .render_audio import snapshot
        delivery = snapshot(db, project)
    except ValueError:
        return False
    return bool(delivery and delivery.get('voice'))


def _describe(path):
    """Duration and stream kinds. The shared video probe rejects a bare voice file."""
    from .media import run
    out, _ = run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], 30)
    data = json.loads(out or '{}')
    streams = data.get('streams') or []
    duration = float((data.get('format') or {}).get('duration') or 0)
    return {
        'has_audio': any(s.get('codec_type') == 'audio' for s in streams),
        'has_video': any(s.get('codec_type') == 'video' for s in streams),
        'duration': duration,
    }


def apply(source, folder):
    """Return host speech with rumble, hiss, and traffic horns reduced.

    Video is copied. A file with no audio is returned unchanged. The music bed
    is not an input here; callers mix it afterwards.
    """
    from .media import ffmpeg
    meta = _describe(source)
    if not meta['has_audio']:
        return source
    folder.mkdir(parents=True, exist_ok=True)
    cleaned = folder / 'host-voice.wav'
    ffmpeg('-i', source, '-map', '0:a:0', '-vn', '-af', FILTER, '-c:a', 'pcm_s16le', '-ar', '48000', cleaned, timeout=600)
    out_meta = _describe(cleaned)
    if not out_meta['has_audio'] or abs(out_meta['duration'] - meta['duration']) > 0.25:
        raise ValueError('output_audio_missing' if not out_meta['has_audio'] else 'output_duration_mismatch')
    if not meta['has_video']:
        return cleaned
    muxed = folder / 'host-voice.mp4'
    ffmpeg('-i', source, '-i', cleaned, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', muxed, timeout=600)
    cleaned.unlink(missing_ok=True)
    mux_meta = _describe(muxed)
    if not mux_meta['has_audio'] or abs(mux_meta['duration'] - meta['duration']) > 0.35:
        raise ValueError('output_audio_missing' if not mux_meta['has_audio'] else 'output_duration_mismatch')
    return muxed


def prepare_track(source, folder, manual, has_audio):
    """Clean the host track when the edit asks for it. Off leaves the file untouched."""
    if not (manual and manual.get('voice_cleanup') and has_audio):
        return source
    return apply(source, folder)
