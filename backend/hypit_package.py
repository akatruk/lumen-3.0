"""Versioned handoff from a Lumen project to Hypit's local HyperFrames capture.

Hypit stays in ``HYPIT_ROOT``. This module does not vendor it, does not start
its CLI UI, and does not put secrets or reference media in the package.
License: Apache 2.0 with Hypit's additional conditions. The capture subprocess
does not surface the Hypit CLI, so the logo clause does not apply.
"""
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from .config import settings
from .media import ffmpeg, probe

SCHEMA = 'lumen.hypit.package.v1'
FPS = 30
_SECRET = re.compile(r'(api[_-]?key|secret|BEGIN [A-Z ]*PRIVATE KEY|sk-[A-Za-z0-9]{8,})', re.I)


def _owned(pid, relative):
    root = (settings.data_dir / pid).resolve()
    path = (root / relative).resolve()
    if path != root and root not in path.parents:
        raise ValueError('invalid_media_path')
    if 'references' in path.parts or path.name == 'reference_source':
        raise ValueError('reference_media_blocked')
    if not path.is_file() or path.stat().st_size < 32:
        raise ValueError('invalid_media_path')
    if path.stat().st_size > settings.max_upload_mb * 1024 * 1024:
        raise ValueError('upload_too_large')
    return path


def _sniff(path: Path):
    head = path.read_bytes()[:16]
    if head[4:8] == b'ftyp' or head[:4] == b'\x1a\x45\xdf\xa3':
        return 'video/mp4'
    if head[:4] == b'RIFF':
        return 'audio/wav'
    if head.startswith(b'ID3') or head[:2] == b'\xff\xfb':
        return 'audio/mpeg'
    raise ValueError('invalid_media_path')


def _describe(pid, relative, role):
    path = _owned(pid, relative)
    media_type = _sniff(path)
    if role == 'music' and not media_type.startswith('audio/') and media_type != 'video/mp4':
        raise ValueError('invalid_media_path')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        'role': role,
        'path': relative,
        'bytes': path.stat().st_size,
        'media_type': media_type,
        'sha256': digest,
    }


def _revision(root: Path):
    package = root / 'package.json'
    if not package.is_file():
        return ''
    try:
        return str(json.loads(package.read_text()).get('version') or '')
    except (OSError, json.JSONDecodeError):
        return ''


def programme(work, width, height, frames, scenes, brand, show_location):
    """HyperFrames HTML. Only supplied captions are drawn on the owned picture."""
    seconds = f'{frames / FPS:.3f}'
    layers = []
    if brand:
        layers.append(
            f'<aside class="hf-brand" data-hypit-start-frame="0" data-hypit-end-frame="{frames}">{html.escape(brand)}</aside>'
        )
    for scene in scenes:
        start = max(0, int(round(float(scene['start']) * FPS)))
        end = max(start + 1, min(frames, int(round(float(scene['end']) * FPS))))
        kind = scene['role']
        layers.append(
            f'<aside class="hf-caption hf-{kind}" data-hypit-kind="{kind}" data-hypit-start-frame="{start}" '
            f'data-hypit-end-frame="{end}">{html.escape(scene["caption"])}</aside>'
        )
        if kind == 'hook' and show_location and scene.get('location'):
            layers.append(
                f'<aside class="hf-location" data-hypit-kind="location" data-hypit-start-frame="{start}" '
                f'data-hypit-end-frame="{end}">{html.escape(scene["location"])}</aside>'
            )
    body = '\n    '.join(layers)
    page = f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <style>
    html,body{{margin:0;background:#111}}
    [data-composition-id]{{position:relative;width:{width}px;height:{height}px;overflow:hidden;background:#111}}
    video{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
    .hf-brand{{position:absolute;z-index:5;top:4%;left:5%;color:#fff;font:700 {max(18, height // 28)}px/1.1 sans-serif;letter-spacing:.04em;text-shadow:0 2px 10px #000}}
    .hf-caption{{position:absolute;z-index:4;left:6%;right:6%;bottom:8%;padding:14px 16px;border-radius:16px;background:rgba(8,12,16,.78);color:#fff;font:700 {max(22, height // 22)}px/1.25 sans-serif;opacity:0}}
    .hf-location{{position:absolute;z-index:4;left:6%;top:12%;color:#fff;font:600 {max(16, height // 32)}px/1.2 sans-serif;text-shadow:0 2px 8px #000;opacity:0}}
  </style>
</head>
<body>
  <div data-composition-id="lumen" data-start="0" data-no-timeline data-width="{width}" data-height="{height}" data-duration="{seconds}" data-fps="{FPS}/1" data-hypit-frame-count="{frames}">
    <video id="picture" src="cut.mp4" muted playsinline preload="none" data-has-audio="false" data-start="0.000" data-end="{seconds}" data-media-start="0.000" data-hypit-start-frame="0" data-hypit-end-frame="{frames}" data-hypit-source-frame="0/1" data-hypit-source-rate="1/1" data-hypit-source-fps="{FPS}/1"></video>
    {body}
  </div>
  <script>
    const fps = {FPS};
    const layers = [...document.querySelectorAll('[data-hypit-start-frame]')];
    const apply = (time) => {{
      const frame = Math.max(0, Math.round(Number(time || 0) * fps));
      for (const el of layers) {{
        if (el.classList.contains('hf-brand')) continue;
        const start = Number(el.getAttribute('data-hypit-start-frame'));
        const end = Number(el.getAttribute('data-hypit-end-frame'));
        el.style.opacity = frame >= start && frame < end ? '1' : '0';
      }}
    }};
    apply(0);
    window.addEventListener('hf-seek', (event) => apply(event.detail && event.detail.time));
  </script>
</body>
</html>
'''
    (work / 'index.html').write_text(page)
    return page


def invoke(work: Path, job: dict):
    """Run the existing capture script. Raises hypit_unavailable when it cannot."""
    job_path = work / 'job.json'
    job_path.write_text(json.dumps(job))
    from .hypit_picture import SCRIPT, command, spawn
    argv, root, tsx = command(job_path)
    if not tsx.is_file() or not SCRIPT.is_file():
        raise RuntimeError('hypit_unavailable')
    env = os.environ.copy()
    env['HYPIT_ROOT'] = str(root)
    try:
        spawn(argv, env)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError('hypit_unavailable') from exc
    visual = work / 'visual.mp4'
    if not visual.is_file() or visual.stat().st_size < 32:
        raise RuntimeError('hypit_unavailable') from RuntimeError('capture_output_missing')
    return visual


def _music(pid, asset_id, db):
    if not asset_id:
        return None
    row = db.execute('SELECT metadata FROM studio_assets WHERE id=? AND project_id=?', (asset_id, pid)).fetchone()
    if not row:
        raise ValueError('asset_not_found')
    meta = json.loads(row['metadata'])
    if meta.get('kind') != 'music':
        raise ValueError('invalid_media_path')
    return _describe(pid, f'assets/{asset_id}', 'music')


def _held_illustrations(pid, idents, db):
    held = []
    for ident in idents:
        row = db.execute('SELECT title FROM studio_assets WHERE id=? AND project_id=?', (ident, pid)).fetchone()
        if not row:
            raise ValueError('asset_not_found')
        held.append({'asset_id': ident, 'title': row['title'], 'in_picture': False, 'label': 'illustration_not_the_property'})
    return held


def render_package(p, prop, folder: Path):
    pid = p['id']
    plan = prop['plan']
    source = _owned(pid, 'source')
    meta = probe(source)
    if abs(float(meta['duration']) - float(plan['duration'])) > 0.45:
        raise ValueError('output_duration_mismatch')
    width = int(meta['width']) - int(meta['width']) % 2
    height = int(meta['height']) - int(meta['height']) % 2
    frames = max(1, int(round(float(plan['duration']) * FPS)))
    work = folder / 'hypit'
    # A second capture in this folder must not die on Hypit's worker-0 mkdir.
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    ffmpeg('-i', source, '-an', '-vf', f'scale={width}:{height}', '-r', str(FPS), '-frames:v', str(frames),
           '-c:v', 'libx264', '-pix_fmt', 'yuv420p', work / 'cut.mp4', timeout=600)
    page = programme(work, width, height, frames, plan['scenes'], plan.get('brand') or '', plan.get('show_location'))
    from .db import connect
    with connect() as db:
        music = _music(pid, plan.get('music_asset_id') or '', db)
        held = _held_illustrations(pid, plan.get('illustrative_asset_ids') or [], db)
    inputs = [_describe(pid, 'source', 'owned_footage')]
    if music:
        inputs.append(music)
    if any(item['path'].endswith('reference_source') or '/references/' in item['path'] for item in inputs):
        raise ValueError('reference_media_blocked')
    from .hypit_picture import _root
    root = _root()
    package_id = hashlib.sha256(json.dumps({
        'project': pid, 'revision': prop['plan_revision'], 'inputs': inputs, 'frames': frames,
    }, sort_keys=True).encode()).hexdigest()[:32]
    package = {
        'schema': SCHEMA,
        'package_id': package_id,
        'project_id': pid,
        'plan_revision': prop['plan_revision'],
        'engine': 'provider-hyperframes-local',
        'hypit_version': _revision(root),
        'notices': [
            'Hypit is Apache License 2.0 with additional conditions: https://github.com/hypit-ai/hypit',
            'Lumen does not surface the Hypit CLI, so the logo clause does not apply.',
            'Lumen owns the project, the media, and this delivery.',
        ],
        'canvas': {'width': width, 'height': height, 'fps': FPS, 'frame_count': frames},
        'inputs': inputs,
        'illustrative': held,
        'reference_media_included': False,
        'cost': {
            'hypit_license_fee_usd': 0,
            'external_model_usd': 0,
            'metered': False,
            'note': 'Local HyperFrames capture. This package calls no generation provider.',
        },
    }
    encoded = json.dumps(package, ensure_ascii=False)
    if _SECRET.search(encoded):
        raise ValueError('invalid_media_path')
    (folder / 'package.json').write_text(encoded)
    job = {'directory': str(work), 'width': width, 'height': height, 'fpsNum': FPS, 'fpsDen': 1, 'frameCount': frames}
    invoke(work, job)
    visual = work / 'visual.mp4'
    dest = folder / 'result.mp4'
    audio_args = ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart']
    if music and meta['has_audio']:
        music_path = _owned(pid, music['path'])
        ffmpeg('-i', visual, '-i', source, '-i', music_path, '-filter_complex',
               '[1:a]volume=1[a1];[2:a]volume=0.18[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=0[a]',
               '-map', '0:v:0', '-map', '[a]', *audio_args, dest, timeout=600)
    elif music:
        ffmpeg('-i', visual, '-i', _owned(pid, music['path']), '-map', '0:v:0', '-map', '1:a:0', *audio_args, dest, timeout=600)
    elif meta['has_audio']:
        ffmpeg('-i', visual, '-i', source, '-map', '0:v:0', '-map', '1:a:0', *audio_args, dest, timeout=600)
    else:
        ffmpeg('-i', visual, '-c', 'copy', '-movflags', '+faststart', dest, timeout=600)
    checked = probe(dest)
    if abs(checked['duration'] - frames / FPS) > 0.45:
        raise ValueError('output_duration_mismatch')
    if (meta['has_audio'] or music) and not checked['has_audio']:
        raise ValueError('output_audio_missing')
    manifest = {
        'schema': SCHEMA,
        'package_id': package_id,
        'render_html_sha256': hashlib.sha256(page.encode()).hexdigest(),
        'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
        'duration': checked['duration'],
        'width': checked['width'],
        'height': checked['height'],
        'has_audio': checked['has_audio'],
        'frame_count': frames,
        'cost': package['cost'],
        'reference_media_included': False,
    }
    (folder / 'manifest.json').write_text(json.dumps(manifest))
    return manifest
