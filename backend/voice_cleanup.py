"""Clean host speech before a licensed music bed is mixed under it.

ffmpeg here has arnndn, but that filter needs an RNNoise model file and none is
shipped. The running chain is a high-pass plus FFT denoise. It is not a neural model.
"""
import json

# 80 Hz drops room rumble. afftdn at its moderate default keeps the speech tone.
FILTER = 'highpass=f=80,afftdn=nr=12:nf=-50:tn=1'


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
    """Return host speech with rumble, hiss, and broadband noise reduced.

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
