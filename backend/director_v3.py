"""Project «e» is assembled by the Director V3 Remotion composition.

A create-video press renders DirectorV3Preview from the speaker, the
consultation clip, and the document still. It does not copy a finished
mp4 and it does not call Hypit.
"""
import hashlib
import json
import logging
import os
import signal
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


def frame_seconds(seconds, source_duration, fps: int = 30) -> float:
    """Whole frames, never past the source container and never a padded tail."""
    source = float(source_duration)
    frames = int(float(seconds) * fps + 1e-6)
    source_frames = int(source * fps + 1e-6)
    frames = max(1, min(frames, source_frames))
    return frames / fps


def output_seconds(requested, source_duration):
    """Steps of five, plus the real source length so the last spoken seconds stay.

    The grid cap is the largest 5s step that does not pass the source. Asking
    for the source itself is also valid. Nothing is rounded up past the file.
    """
    source = float(source_duration)
    grid = max(5, (int(source) // 5) * 5)
    if requested is None:
        # FULL_SOURCE. A missing request is the probed file, not a 20s preview.
        return frame_seconds(source, source)
    value = float(requested)
    if value > source + 1e-3:
        raise ValueError('duration_step')
    if abs(value - source) <= 0.05:
        return frame_seconds(source, source)
    seconds = int(round(value))
    if seconds % 5 or not 10 <= seconds <= min(grid, source):
        raise ValueError('duration_step')
    return frame_seconds(seconds, source)


def duration_contract(requested, source_duration, fps: int = 30) -> dict:
    """FULL_SOURCE keeps the probed file. TARGET_DURATION is an explicit request.

    Both come back as a frame count at ``fps``. ``int(seconds)`` is not used,
    so 85.5s and 151.1s are not shortened to 85 and 151.
    """
    source = float(source_duration)
    if requested is None:
        mode = 'full_source'
        target = frame_seconds(source, source, fps)
    else:
        mode = 'target'
        target = output_seconds(requested, source)
    frames = int(round(float(target) * fps))
    return {
        'mode': mode,
        'sourceSeconds': source,
        'targetSeconds': frames / fps,
        'durationInFrames': frames,
        'fps': fps,
    }


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


# Remotion 4.0.524 defaults both caches to half of host RAM (os.freemem),
# which ignores the worker cgroup. 256 MiB + 128 MiB stay inside MemoryMax
# 2800 MiB together with one Chrome renderer. Threads default to 2.
REMOTION_CONCURRENCY = '1'
OFFTHREAD_VIDEO_THREADS = '1'
OFFTHREAD_CACHE_BYTES = '268435456'
MEDIA_CACHE_BYTES = '134217728'


def remotion_render_command(binary: str, dest: Path, seconds, speaker: str, visual_plan, public_dir: Path) -> list[str]:
    return [
        binary,
        'render', 'src/index.ts', COMPOSITION, str(dest),
        '--props', json.dumps({
            'durationSeconds': seconds,
            'speakerFile': speaker,
            'visualPlan': visual_plan,
        }),
        f'--public-dir={public_dir}',
        f'--concurrency={REMOTION_CONCURRENCY}',
        f'--offthreadvideo-video-threads={OFFTHREAD_VIDEO_THREADS}',
        f'--offthreadvideo-cache-size-in-bytes={OFFTHREAD_CACHE_BYTES}',
        f'--media-cache-size-in-bytes={MEDIA_CACHE_BYTES}',
        '--disallow-parallel-encoding',
    ]


def _render_timeout(seconds) -> int:
    return max(900, int(float(seconds)) * 45)


def _remove_tree(path: Path) -> None:
    if not path.is_dir():
        return
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            os.unlink(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(path)


def _kill_render_group(proc: subprocess.Popen) -> None:
    """Stop Remotion and the Chrome, compositor, and FFmpeg children it spawned."""
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


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
    command = remotion_render_command(
        str(root / 'node_modules' / '.bin' / 'remotion'),
        dest, seconds, speaker, visual_plan, public_dir,
    )
    env = _remotion_env(root)
    scratch = dest.parent / '.remotion-tmp'
    if scratch.exists():
        _remove_tree(scratch)
    scratch.mkdir()
    env['TMPDIR'] = str(scratch)
    proc = subprocess.Popen(
        command,
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=_render_timeout(seconds))
    except subprocess.TimeoutExpired:
        _kill_render_group(proc)
        stdout, stderr = '', 'remotion timeout'
        proc.returncode = proc.returncode if proc.returncode is not None else -9
    finally:
        if proc.poll() is None:
            _kill_render_group(proc)
        _remove_tree(scratch)
    if proc.returncode != 0 or not dest.is_file() or dest.stat().st_size < 100_000:
        if dest.exists():
            dest.unlink()
        tail = (stderr or stdout or '')[-2000:]
        log.error('Director V3 render failed: %s', tail)
        raise ValueError('director_v3_render_failed')
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    if digest == FROZEN_COPY_SHA256:
        dest.unlink()
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
    if (payload or {}).get("await_transcript"):
        from .transcription import materialize_director_payload
        payload = materialize_director_payload(p, payload)
    from . import remotion_engine
    if not remotion_engine.should_use_remotion(p['id']):
        raise ValueError('director_v3_required')
    if (payload or {}).get('composition') not in (None, COMPOSITION):
        raise ValueError('director_v3_required')
    # Explicit Hypit request must not be silently remapped.
    if (payload or {}).get('picture_engine') == 'hypit':
        raise ValueError('remotion_required_for_supported_project')
    raw_source = (p.get('metadata') or {}).get('duration')
    if raw_source:
        contract = duration_contract((payload or {}).get('duration_seconds'), raw_source)
        seconds = contract['targetSeconds']
    else:
        contract = None
        seconds = output_seconds((payload or {}).get('duration_seconds'), 20)
    render_id = uuid.uuid4().hex
    folder = settings.data_dir / p['id'] / 'renders' / render_id
    folder.mkdir(parents=True)
    (folder / '.rendering').write_text(render_id, encoding='utf-8')
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
    from .language import resolve_locale
    from .source_analysis import is_placeholder_transcript
    from .source_transcript import TranscriptError, source_language_decision
    rows = (payload or {}).get('transcript') or ((payload or {}).get('plan') or {}).get('transcript') or []
    if is_placeholder_transcript(rows) and rows:
        raise ValueError('SOURCE_TRANSCRIPT_UNAVAILABLE')
    try:
        decision = source_language_decision(rows)
    except TranscriptError as exc:
        raise ValueError(exc.code) from None
    if rows and decision.get("status") not in (None, "resolved", "unset"):
        raise ValueError("SOURCE_LANGUAGE_UNVERIFIED")
    heard = decision.get("sourceLanguage") if decision.get("status") == "resolved" else None
    if heard:
        try:
            asked = resolve_locale(target_locale) if target_locale else None
        except Exception:
            asked = None
        stored = None
        try:
            stored = resolve_locale((payload or {}).get('source_language')) if (payload or {}).get('source_language') else None
        except Exception:
            stored = None
        if stored and stored != heard:
            raise ValueError('SOURCE_LANGUAGE_UNVERIFIED')
        if asked and asked == heard:
            dubbed = False
        elif not (payload or {}).get('source_language'):
            payload = {**(payload or {}), 'source_language': heard}
    if dubbed:
        import os
        if not (os.environ.get('RUNPOD_API_KEY') or '').strip():
            raise ValueError('VOICE_PROVIDER_NOT_CONFIGURED')
        # A different language uses the existing dub path. Same language never reaches here.
        # Never leave source speech under a different language label.
        locale_label = target_locale or (payload or {}).get('language') or 'target'
        progress(
            p['id'], 'preparing_voice', 18,
            note=f'Building {locale_label} voice on GPU (Qwen3-TTS). Source RU audio is not used.',
            plan=['preparing_voice', 'drawing_graphics', 'rendering', 'assembling', 'checking'],
        )
        from .worker import _dub_for_job
        try:
            record = _dub_for_job(p['id'], payload or {}, folder)
        except RuntimeError as exc:
            if str(exc) == 'hypit_unavailable':
                raise ValueError('VOICE_PROVIDER_NOT_CONFIGURED') from exc
            raise
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
    transcript_early = (
        (payload or {}).get('transcript')
        or ((payload or {}).get('plan') or {}).get('transcript')
        or (visual_plan or {}).get('transcript')
        or []
    )
    if visual_plan is not None and transcript_early:
        from .director_semantics import enrich_plan_from_transcript
        from . import director_v8
        locale = target_locale or visual_plan.get('language')
        cleaned = director_v8.filter_locale_transcript(transcript_early, locale)
        visual_plan = enrich_plan_from_transcript(visual_plan, cleaned, locale=locale)
        visual_plan = director_v8.expand_plan_for_duration(
            visual_plan, duration_seconds=seconds, transcript=cleaned, locale=locale,
        )
        from .passage_retrieval import apply_passage_media, apply_semantic_beats
        from .semantic_planner import PlannerError
        try:
            visual_plan = apply_semantic_beats(visual_plan, p['id'], cleaned)
            visual_plan = apply_passage_media(visual_plan, p['id'], cleaned)
        except PlannerError as exc:
            raise ValueError(exc.code) from exc
        visual_plan = director_v8.fill_media_for_scenes(visual_plan, seed=visual_plan.get('visualSeed'))
        from . import director_v9, director_v10, director_v11, director_v11_1, director_v11_2
        visual_plan = director_v9.apply_composition_intelligence(visual_plan)
        visual_plan = director_v11.apply_semantic_intelligence(
            visual_plan, cleaned, locale=locale,
        )
        visual_plan = director_v11_1.apply_factual_business_motion(
            visual_plan, cleaned, locale=locale,
        )
        visual_plan = director_v11_2.apply_composition_repair(
            visual_plan, cleaned, locale=locale,
        )
        visual_plan = director_v8.fill_media_for_scenes(
            visual_plan, seed=visual_plan.get('visualSeed'),
        )
        from .passage_retrieval import revalidate_assets
        try:
            visual_plan = revalidate_assets(visual_plan, p['id'], cleaned)
        except PlannerError as exc:
            raise ValueError(exc.code) from exc
        visual_plan = director_v9.apply_composition_intelligence(visual_plan)
        visual_plan = director_v10.apply_premium_3d(visual_plan, seed=visual_plan.get('visualSeed'))
        from .semantic_motion_profile import selected as _motion_profile
        motion_profile = (payload or {}).get('semantic_motion_profile')
        if not _motion_profile(motion_profile):
            from . import director_v14
            visual_plan = director_v14.apply_semantic_motion(
                visual_plan, transcript_early, locale=locale,
            )
        from . import director_v15
        visual_plan = director_v15.apply_semantic_motion_v15(
            visual_plan, transcript_early, locale=locale,
        )
        from . import scene_composer_v16
        visual_plan = scene_composer_v16.apply_scene_composer(
            visual_plan, transcript_early, locale=locale,
            source=settings.data_dir / p['id'] / 'source',
        )
        from . import motion_design_v18
        visual_plan = motion_design_v18.apply_motion_design(
            visual_plan, transcript_early, locale=locale,
            source=settings.data_dir / p['id'] / 'source',
        )
        if _motion_profile(motion_profile):
            from .semantic_motion_profile import apply_profile
            visual_plan = apply_profile(visual_plan, transcript_early, locale=locale)
        else:
            from . import semantic_numeric_range
            visual_plan = semantic_numeric_range.apply_numeric_range(
                visual_plan, transcript_early, locale=locale,
            )
            from .director_evidence import apply_evidence_gate
            visual_plan = apply_evidence_gate(visual_plan, transcript_early, locale=locale)
        from .visual_quality_optimizer import apply as apply_visual_optimizer
        visual_plan = apply_visual_optimizer(
            visual_plan,
            transcript_early,
            mode=(payload or {}).get('visual_optimizer_mode'),
        )
        from .visual_treatment_ranking import apply as apply_treatment_ranking
        visual_plan = apply_treatment_ranking(
            visual_plan,
            mode=(payload or {}).get('visual_treatment_mode'),
        )
        from .editorial_decision import apply_editorial_decision
        visual_plan = apply_editorial_decision(
            visual_plan,
            cleaned,
            locale=locale,
            target_seconds=seconds,
            source_seconds=float(raw_source or seconds),
            duration_mode=(contract or {}).get('mode') or 'target',
        )
        try:
            visual_plan = revalidate_assets(visual_plan, p['id'], cleaned)
        except PlannerError as exc:
            raise ValueError(exc.code) from exc
        if (payload or {}).get('plan_only'):
            visual_plan = {**visual_plan, 'planOnly': True, 'staging': 'skipped'}
        else:
            public = _public_director()
            from .visual_variation import stage_backgrounds
            from pathlib import Path as _Path
            library = _Path(__file__).resolve().parent.parent / 'media' / 'library' / 'out'
            visual_plan = stage_backgrounds(visual_plan, public, library)
            visual_plan = director_v8.stage_semantic_motion(visual_plan, public, library)
            visual_plan = director_v9.stage_float_objects(visual_plan, public, library)
            visual_plan = director_v10.stage_premium_3d(visual_plan, public, library)
        transcript_early = cleaned
        if visual_plan.get('form') == 'semantic':
            ends = [float(scene.get('end') or 0) for scene in visual_plan.get('scenes') or []]
            if ends and max(ends) > 0:
                seconds = frame_seconds(max(ends), max(ends))
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
    if (payload or {}).get('plan_only'):
        marker = folder / '.rendering'
        marker.unlink(missing_ok=True)
        return {
            'plan_only': True,
            'rendered': False,
            'render_id': render_id,
            'director': (visual_plan or {}).get('director'),
            'directorMode': render_plan.get('directorMode'),
            'form': (visual_plan or {}).get('form'),
            'beatWeights': (visual_plan or {}).get('beatWeights'),
            'scenes': (visual_plan or {}).get('scenes') or [],
            'render_scenes': render_plan.get('scenes') or [],
            'generationId': render_plan.get('generationId'),
        }
    from .director_quality_shadow import diagnose
    import json as _json
    shadow = diagnose(render_plan, transcript)
    shadow_path = settings.data_dir / p['id'] / 'remotion-plans' / f"{render_plan.get('generationId') or 'plan'}-quality-shadow.json"
    shadow_path.write_text(_json.dumps(shadow, ensure_ascii=False, indent=2), encoding='utf-8')
    progress(
        p['id'], 'rendering', 55,
        note=f'Remotion DirectorV3 · {seconds}s · speaker={speaker} · captions={render_plan.get("captionSource")}',
    )
    digest = remotion_engine.render_with_plan(dest, render_plan)
    try:
        from . import motion_quality_v17
        motion_quality_v17.record_completed(
            p['id'],
            str((visual_plan or {}).get('generationId') or render_id),
            visual_plan or {},
        )
    except Exception:
        log.exception('motion quality record failed for %s', p['id'])
    progress(p['id'], 'checking', 92, note='Probing finished MP4 (size, audio, duration)…')
    meta = _accept(dest, seconds)
    from .db import connect, event, update
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
        'timeline': [[0.0, seconds]],
        'applied': ['director_v3', 'remotion_engine_v1', 'director_execution_v4'],
        'picture_engine': 'remotion',
        'renderer': 'remotion',
        'directorMode': director_mode,
        'executionValidation': render_plan.get('executionValidation') or 'passed',
        'captionSource': render_plan.get('captionSource') or 'unavailable',
        'semanticMotionProfile': (visual_plan or {}).get('semanticMotionProfile'),
        'composition': COMPOSITION,
        'duration_seconds': seconds,
        'duration_contract': contract,
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
    from . import render_audio
    carried = False
    with connect() as db:
        db.lock()
        carried = render_audio.attach_selected(db, p, folder, result)
    if not carried:
        update(p['id'], result=result, status='complete', stage='complete', progress=100, error=None)
    try:
        marker = folder / '.rendering'
        if marker.is_file():
            marker.unlink()
        from .render_retention import prune_pictures
        prune_pictures(p['id'], render_id)
    except Exception:
        log.exception('render retention failed for %s', p['id'])
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
