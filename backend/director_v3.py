"""Project «e» is assembled by the Director V3 Remotion composition.

A create-video press renders DirectorV3Preview from the speaker, the
consultation clip, and the document still. It does not copy a finished
mp4 and it does not call Hypit.
"""
import hashlib
import json
import logging
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
    volume = Path('/mnt/volume_nyc1_1791446889637')
    root = volume / 'lumen-motion' / 'public' / 'director-v3' if volume.is_dir() else motion_root() / 'public' / 'director-v3'
    root.mkdir(parents=True, exist_ok=True)
    return root


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


def render_assembly(dest: Path, seconds: int = 20, speaker: str = 'speaker.mp4', visual_plan=None):
    """Render the composition. The destination bytes come from Remotion."""
    root = motion_root()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    if visual_plan:
        from .visual_variation import stage_backgrounds
        visual_plan = stage_backgrounds(visual_plan, _public_director())
    command = [
        str(root / 'node_modules' / '.bin' / 'remotion'),
        'render', 'src/index.ts', COMPOSITION, str(dest),
        '--props', json.dumps({
            'durationSeconds': seconds,
            'speakerFile': speaker,
            'visualPlan': visual_plan,
        }),
        '--concurrency=1',
    ]
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=max(900, int(seconds) * 45))
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
    """Assemble a new picture for project «e». Never calls Hypit."""
    if p['id'] != PROJECT_ID:
        raise ValueError('director_v3_required')
    if (payload or {}).get('composition') not in (None, COMPOSITION):
        raise ValueError('director_v3_required')
    seconds = output_seconds((payload or {}).get('duration_seconds'), (p.get('metadata') or {}).get('duration') or 20)
    render_id = uuid.uuid4().hex
    folder = settings.data_dir / p['id'] / 'renders' / render_id
    folder.mkdir(parents=True)
    dest = folder / 'result.mp4'
    visual_plan = (payload or {}).get('visual_plan')
    speaker = speaker_for(seconds, settings.data_dir / p['id'] / 'source')
    from . import remotion_engine
    render_plan = remotion_engine.resolve_scene_plan(
        visual_plan=visual_plan,
        locale=(visual_plan or {}).get('language'),
        duration_seconds=seconds,
        speaker_file=speaker,
        source_ref=str(settings.data_dir / p['id'] / 'source'),
        generation_id=(visual_plan or {}).get('generationId'),
    )
    remotion_engine.store_render_plan(settings.data_dir, p['id'], render_plan)
    digest = remotion_engine.render_with_plan(dest, render_plan)
    meta = _accept(dest, seconds)
    from .db import event, update
    from .studio import state
    current = state(p['id']) or {}
    result = {
        'render_id': render_id,
        'metadata': meta,
        'timeline': [[0.0, meta['duration']]],
        'applied': ['director_v3', 'remotion_engine_v1'],
        'picture_engine': 'remotion',
        'composition': COMPOSITION,
        'duration_seconds': seconds,
        'visual_seed': render_plan.get('visualSeed'),
        'art_direction': render_plan.get('artDirection'),
        'render_plan_id': render_plan.get('generationId'),
        'delivery_sha256': digest,
        'assembled': True,
        'qa': None,
        'qa_status': 'unavailable',
        'generated_clips': 0,
        'music': None,
        'captions_enabled': False,
        'caption_master': False,
        'plan_revision': current.get('revision'),
        'manual_transcript': [],
    }
    update(p['id'], result=result, status='complete', stage='complete', progress=100, error=None)
    event(p['id'], 'render_complete', json.dumps({
        'applied': ['director_v3'],
        'quality': 'unavailable',
        'engine': 'remotion',
        'composition': COMPOSITION,
        'assembled': True,
    }))
    return result
