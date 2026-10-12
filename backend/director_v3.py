"""Project «e» is assembled by the Director V3 Remotion composition.

A create-video press renders DirectorV3Preview from the speaker, the
consultation clip, and the document still. It does not copy a finished
mp4 and it does not call Hypit.
"""
import hashlib
import json
import logging
import os
import subprocess
import uuid
from pathlib import Path

from .config import settings
from . import media

log = logging.getLogger(__name__)

PROJECT_ID = '9a9c116d8e0d4f7f927e7f60cb926562'
COMPOSITION = 'DirectorV3Preview'
# The file that used to be pasted into the player. A new assembly must not match it.
FROZEN_COPY_SHA256 = '8db86f8ea0f6ef3cad2a5ed26dcc9ba8b60e6ab42f693ac30014472320746566'


def motion_root():
    root = Path(__file__).resolve().parent.parent / 'motion'
    if not (root / 'src' / 'index.ts').is_file():
        raise ValueError('director_v3_renderer_missing')
    if not (root / 'node_modules' / '.bin' / 'remotion').is_file():
        raise ValueError('director_v3_renderer_missing')
    return root


def output_seconds(requested, source_duration):
    """Seconds the create-video control may ask for. Steps of five, never past the source."""
    cap = max(5, (int(float(source_duration)) // 5) * 5)
    if requested is None:
        return 20 if cap >= 20 else cap
    seconds = int(requested)
    if seconds % 5 or not 10 <= seconds <= cap:
        raise ValueError('duration_step')
    return seconds


def _public_director():
    """Writable director-v3 media folder (volume on lumen-test, else motion/public)."""
    volume = Path('/mnt/volume_nyc1_1791446889637')
    root = volume / 'lumen-motion' / 'public' / 'director-v3' if volume.is_dir() else motion_root() / 'public' / 'director-v3'
    root.mkdir(parents=True, exist_ok=True)
    return root


def remotion_public_dir() -> Path:
    """Remotion ``--public-dir``: parent of ``director-v3/`` (staticFile('director-v3/…')).

    Staging writes to the volume path under ProtectSystem=strict. Remotion must
    serve that same tree — not the read-only copy under ``motion/public``.
    """
    return _public_director().parent


def _copy_file(source: Path, dest: Path):
    with source.open('rb') as incoming, dest.open('wb') as outgoing:
        while True:
            chunk = incoming.read(1024 * 1024)
            if not chunk:
                break
            outgoing.write(chunk)


def speaker_for(seconds, source: Path):
    """The 20-second cut uses the tuned clip. A longer cut uses the project source."""
    if seconds <= 20:
        return 'speaker.mp4'
    if not source.is_file():
        raise ValueError('director_v3_render_failed')
    _copy_file(source, _public_director() / 'source-edit.mp4')
    return 'source-edit.mp4'


def speaker_with_dub(speaker_name: str, dub_path: Path) -> str:
    """Replace speaker audio with the finished dubbed track. Video stays the host picture."""
    public = _public_director()
    src = public / speaker_name
    if not src.is_file():
        raise ValueError('director_v3_render_failed')
    if not Path(dub_path).is_file():
        raise ValueError('target_voice_not_ready')
    out_name = 'speaker-dub.mp4'
    out = public / out_name
    if out.exists():
        out.unlink()
    media.ffmpeg(
        '-y', '-i', src, '-i', dub_path,
        '-map', '0:v:0', '-map', '1:a:0',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
        '-shortest', '-movflags', '+faststart', out,
        timeout=600,
    )
    if not out.is_file() or out.stat().st_size < 10_000:
        raise ValueError('target_voice_not_ready')
    return out_name


def _remotion_env(root: Path) -> dict:
    """Point caches at a writable volume when the repo tree is read-only (systemd)."""
    env = os.environ.copy()
    tmp = Path(env.get('TMPDIR') or '/tmp')
    cache = Path(env.get('XDG_CACHE_HOME') or (tmp / 'remotion-cache'))
    cache.mkdir(parents=True, exist_ok=True)
    env.setdefault('XDG_CACHE_HOME', str(cache))
    env.setdefault('npm_config_cache', str(cache / 'npm'))
    # Webpack still defaults under node_modules/.cache; prefer a pre-created
    # writable dir when the worker cannot mutate /opt/.../motion.
    webpack = root / 'node_modules' / '.cache' / 'webpack'
    try:
        webpack.mkdir(parents=True, exist_ok=True)
        probe = webpack / '.write-probe'
        probe.write_text('ok', encoding='utf-8')
        probe.unlink(missing_ok=True)
    except OSError:
        log.warning('Remotion webpack cache not writable at %s (ProtectSystem?); bundling may warn', webpack)
    return env


def render_assembly(dest: Path, seconds: int = 20, speaker: str = 'speaker.mp4', visual_plan=None):
    """Render the composition. The destination bytes come from Remotion."""
    root = motion_root()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    public = _public_director()
    if visual_plan:
        from .visual_variation import stage_backgrounds
        visual_plan = stage_backgrounds(visual_plan, public)
    public_dir = remotion_public_dir()
    command = [
        str(root / 'node_modules' / '.bin' / 'remotion'),
        'render', 'src/index.ts', COMPOSITION, str(dest),
        '--props', json.dumps({
            'durationSeconds': seconds,
            'speakerFile': speaker,
            'visualPlan': visual_plan,
        }),
        f'--public-dir={public_dir}',
        '--concurrency=1',
    ]
    completed = subprocess.run(
        command,
        cwd=root,
        env=_remotion_env(root),
        capture_output=True,
        text=True,
        timeout=max(900, int(seconds) * 45),
    )
    if completed.returncode != 0 or not dest.is_file() or dest.stat().st_size < 100_000:
        tail = (completed.stderr or completed.stdout or '')[-2000:]
        log.error('Director V3 render failed: %s', tail)
        raise ValueError('director_v3_render_failed')
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    if digest == FROZEN_COPY_SHA256:
        raise ValueError('director_v3_render_failed')
    return digest


def _accept(path, seconds):
    meta = media.probe(path)
    if (meta['width'], meta['height']) != (1080, 1920) or not meta['has_audio']:
        raise ValueError('director_v3_render_failed')
    if abs(float(meta['duration']) - float(seconds)) > 1.5:
        raise ValueError('director_v3_render_failed')
    return meta


def run_job(p, payload):
    """Assemble picture via Director V4 + Remotion. Never calls Hypit."""
    from . import remotion_engine
    if not remotion_engine.should_use_remotion(p['id']):
        raise ValueError('director_v3_required')
    if (payload or {}).get('composition') not in (None, COMPOSITION):
        raise ValueError('director_v3_required')
    # Explicit Hypit request must not be silently remapped.
    if (payload or {}).get('picture_engine') == 'hypit':
        raise ValueError('remotion_required_for_supported_project')
    seconds = output_seconds((payload or {}).get('duration_seconds'), (p.get('metadata') or {}).get('duration') or 20)
    render_id = uuid.uuid4().hex
    folder = settings.data_dir / p['id'] / 'renders' / render_id
    folder.mkdir(parents=True)
    dest = folder / 'result.mp4'
    visual_plan = (payload or {}).get('visual_plan')
    speaker = speaker_for(seconds, settings.data_dir / p['id'] / 'source')
    from .worker import progress
    target_locale = (
        (visual_plan or {}).get('language')
        or (payload or {}).get('target_language')
        or (payload or {}).get('language')
    )
    dubbed = bool((payload or {}).get('dubbed'))
    if not dubbed:
        mode = ((payload or {}).get('voice_resolution') or {}).get('mode')
        dubbed = mode == 'dubbed'
    if dubbed:
        # Same path as Hypit: build target speech, then put it on the speaker cut.
        # Never leave source RU audio under an EN/ZH label.
        locale_label = target_locale or (payload or {}).get('language') or 'target'
        progress(
            p['id'], 'preparing_voice', 18,
            note=f'Building {locale_label} voice on GPU (Qwen3-TTS). Source RU audio is not used.',
            plan=['preparing_voice', 'drawing_graphics', 'rendering', 'assembling', 'checking'],
        )
        from .worker import _dub_for_job
        record = _dub_for_job(p['id'], payload or {}, folder)
        dub_file = (record.get('audio') or {}).get('file')
        if not dub_file:
            raise ValueError('target_voice_not_ready')
        progress(
            p['id'], 'preparing_voice', 28,
            note=f'Muxing {locale_label} voice onto the speaker picture…',
        )
        speaker = speaker_with_dub(speaker, Path(dub_file))
        progress(
            p['id'], 'drawing_graphics', 35,
            note='Voice ready. Staging Remotion stills and scene plan…',
        )
    if visual_plan is not None and target_locale and not visual_plan.get('language'):
        visual_plan = {**visual_plan, 'language': target_locale}
    render_plan = remotion_engine.resolve_scene_plan(
        visual_plan=visual_plan,
        locale=target_locale,
        duration_seconds=seconds,
        speaker_file=speaker,
        source_ref=str(settings.data_dir / p['id'] / 'source'),
        generation_id=(visual_plan or {}).get('generationId'),
    )
    transcript = (
        (payload or {}).get('transcript')
        or ((payload or {}).get('plan') or {}).get('transcript')
        or (visual_plan or {}).get('transcript')
        or []
    )
    render_plan = remotion_engine.attach_transcript_captions(
        render_plan, transcript, locale=target_locale, dubbed=dubbed,
    )
    remotion_engine.store_render_plan(settings.data_dir, p['id'], render_plan)
    progress(
        p['id'], 'rendering', 55,
        note=f'Remotion DirectorV3 · {seconds}s · speaker={speaker} · captions={render_plan.get("captionSource")}',
    )
    digest = remotion_engine.render_with_plan(dest, render_plan)
    progress(p['id'], 'checking', 92, note='Probing finished MP4 (size, audio, duration)…')
    meta = _accept(dest, seconds)
    from .db import event, update
    from .studio import state
    current = state(p['id']) or {}
    director_mode = (
        (payload or {}).get('director_mode')
        or (current.get('context') or {}).get('director_mode')
        or (p.get('metadata') or {}).get('director_mode')
        or 'heuristic'
    )
    result = {
        'render_id': render_id,
        'metadata': meta,
        'timeline': [[0.0, meta['duration']]],
        'applied': ['director_v3', 'remotion_engine_v1', 'director_execution_v4'],
        'picture_engine': 'remotion',
        'renderer': 'remotion',
        'directorMode': director_mode,
        'executionValidation': render_plan.get('executionValidation') or 'passed',
        'captionSource': render_plan.get('captionSource') or 'unavailable',
        'composition': COMPOSITION,
        'duration_seconds': seconds,
        'visual_seed': render_plan.get('visualSeed'),
        'art_direction': render_plan.get('artDirection'),
        'render_plan_id': render_plan.get('generationId'),
        'language': render_plan.get('locale'),
        'target_language': render_plan.get('locale'),
        'delivery_sha256': digest,
        'assembled': True,
        'qa': None,
        'qa_status': 'unavailable',
        'generated_clips': 0,
        'music': None,
        'captions_enabled': bool(render_plan.get('captions')),
        'caption_master': False,
        'plan_revision': current.get('revision'),
        'manual_transcript': [],
    }
    update(p['id'], result=result, status='complete', stage='complete', progress=100, error=None)
    event(p['id'], 'render_complete', json.dumps({
        'applied': ['director_v3'],
        'quality': 'unavailable',
        'engine': 'remotion',
        'renderer': 'remotion',
        'directorMode': director_mode,
        'executionValidation': result['executionValidation'],
        'captionSource': result['captionSource'],
        'composition': COMPOSITION,
        'assembled': True,
    }))
    return result
