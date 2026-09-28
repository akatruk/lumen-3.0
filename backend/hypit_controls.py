"""Editor controls that drive Hypit.

``voice_cleanup`` removes rumble, hiss, and other extra sound from the host
stem. Music is mixed afterwards and is not an input here.

``picture_quality`` runs Hypit's image program on each captured piece:
YCrCb non-local-means denoise at the published GPT Image profile, then a
sharpen. Frame count and clip length stay put, so the mouth does not drift.

``generate`` is the next control on this same dispatcher. It stays closed
until a generation provider is selected.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from .media import ffmpeg, run

# Published by @hypit/image-transform as gptImageDenoiseV1, then a sharpen.
PICTURE_OPERATIONS = (
    {
        'kind': 'denoise', 'method': 'nlm-ycrcb',
        'lumaStrength': 2, 'chromaStrength': 10,
        'templateWindow': 7, 'searchWindow': 21, 'saturationRecovery': 1.02,
    },
    {'kind': 'sharpen', 'amount': 0.35, 'radius': 1.2, 'threshold': 2},
    {'kind': 'encode', 'format': 'png'},
)
LATER = ('generate',)


def picture_program():
    return [dict(item) for item in PICTURE_OPERATIONS]


def controls_for(manual):
    """Controls the saved edit asked Hypit to run. Generation is not implied."""
    asked = []
    if (manual or {}).get('voice_cleanup'):
        asked.append('voice_cleanup')
    if (manual or {}).get('picture_quality'):
        asked.append('picture_quality')
    return asked


def run_generate():
    """Video generation uses this dispatcher later. Nothing is rendered now."""
    raise RuntimeError('hypit_generation_unavailable')


def _duration(path):
    out, _ = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(path)], 30)
    try:
        return float((json.loads(out or '{}').get('format') or {}).get('duration') or 0)
    except (TypeError, ValueError):
        return 0.0


def _has_audio(path):
    out, _ = run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'json', str(path)], 30)
    try:
        streams = json.loads(out or '{}').get('streams') or []
    except (TypeError, ValueError):
        return False
    return any(item.get('codec_type') == 'audio' for item in streams)


def clean_host(source, folder):
    """Return the host stem with extra sound removed. Length stays the same."""
    from .voice_cleanup import FILTER

    folder = Path(folder)
    before = _duration(source)
    program = {
        'control': 'voice_cleanup',
        'stem': 'host',
        'sample_rate': 48000,
        'channels': 2,
        'filter': FILTER,
    }
    (folder / 'voice-cleanup.json').write_text(json.dumps(program))
    cleaned = folder / 'host-cleaned.wav'
    ffmpeg(
        '-i', str(source), '-map', '0:a:0', '-vn', '-af', FILTER,
        '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', str(cleaned), timeout=600,
    )
    after = _duration(cleaned)
    if after <= 0 or abs(after - before) > 0.25:
        raise ValueError('output_audio_missing' if after <= 0 else 'output_duration_mismatch')
    return cleaned


def raster_script():
    root = Path(os.environ.get('HYPIT_ROOT') or '/opt/hypit')
    return root / 'packages' / 'provider-image-opencv-local' / 'runtime' / 'raster_execute.py'


def invoke_raster(source, dest, operations):
    """One Hypit raster request. The interpreter lives in HYPIT_ROOT."""
    script = raster_script()
    if not script.is_file():
        raise RuntimeError('hypit_unavailable')
    request = Path(dest).with_suffix('.request.json')
    request.write_text(json.dumps({
        'kind': 'transform', 'source': str(source), 'operations': operations,
    }))
    try:
        subprocess.run(
            [sys.executable, str(script), str(request), str(dest)],
            check=True, timeout=120,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError('hypit_unavailable') from exc
    if not Path(dest).is_file() or Path(dest).stat().st_size < 8:
        raise RuntimeError('hypit_unavailable')


def apply_picture(piece, folder, index):
    """Run the picture-quality program on every frame. The piece length is unchanged."""
    piece = Path(piece)
    folder = Path(folder)
    before = _duration(piece)
    spoken = folder / f'quality-audio-{index:03d}.m4a'
    if _has_audio(piece):
        ffmpeg('-i', str(piece), '-vn', '-c:a', 'copy', str(spoken), timeout=180)
    frames = folder / f'quality-{index:03d}'
    frames.mkdir(parents=True)
    program = picture_program()
    (folder / f'quality-{index:03d}.json').write_text(json.dumps({
        'control': 'picture_quality', 'operations': program,
    }))
    ffmpeg('-i', str(piece), str(frames / 'in-%05d.png'), timeout=180)
    names = sorted(frames.glob('in-*.png'))
    if not names or before <= 0:
        raise RuntimeError('hypit_unavailable')
    for number, name in enumerate(names, start=1):
        invoke_raster(name, frames / f'out-{number:05d}.png', program)
    out = folder / f'quality-{index:03d}.mp4'
    ffmpeg(
        '-framerate', '30', '-i', str(frames / 'out-%05d.png'),
        '-t', f'{before:.3f}', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-pix_fmt', 'yuv420p', str(out), timeout=180,
    )
    if abs(_duration(out) - before) > 0.2:
        raise RuntimeError('hypit_unavailable')
    if spoken.is_file() and spoken.stat().st_size > 32:
        mixed = folder / f'quality-av-{index:03d}.mp4'
        ffmpeg(
            '-i', str(out), '-i', str(spoken), '-map', '0:v:0', '-map', '1:a:0',
            '-c', 'copy', '-shortest', str(mixed), timeout=180,
        )
        out = mixed
    out.replace(piece)
    return piece
