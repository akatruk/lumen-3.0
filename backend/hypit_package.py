"""Versioned handoff from a property plan to one Hypit author prompt.

Hypit stays in ``HYPIT_ROOT``. This module does not vendor it, does not start
its CLI UI, and does not put secrets or reference media in the package.
The picture is ``main.svml``. License: Apache 2.0 with Hypit's additional
conditions.
"""
import hashlib
import json
import re
import shutil
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
    if head.startswith(b'\x89PNG'):
        return 'image/png'
    if head.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if head[:4] == b'RIFF' and path.read_bytes()[8:12] == b'WEBP':
        return 'image/webp'
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
    logo_id = plan.get('logo_asset_id') or ''
    photo_ids = list(plan.get('photo_asset_ids') or [])
    if logo_id:
        shutil.copyfile(_owned(pid, f'assets/{logo_id}'), work / 'logo.png')
    if photo_ids:
        shutil.copyfile(_owned(pid, f'assets/{photo_ids[0]}'), work / 'photo.png')
    clips = []
    captions = []
    for scene in plan['scenes']:
        start = float(scene['start'])
        end = float(scene['end'])
        caption = str(scene.get('caption') or '').strip()
        note = caption
        if logo_id:
            note = f'{note} logo.png'.strip()
        if photo_ids and scene.get('role') == 'highlight':
            note = f'{note} photo.png'.strip()
        clips.append({'start': start, 'end': end, 'text': note[:160], 'approved': True})
        if caption:
            captions.append({'start': start, 'end': end, 'original': caption, 'en': caption, 'zh': caption})
    brand = str(plan.get('brand') or '').strip()
    if brand and clips:
        clips[0]['text'] = f'{brand} {clips[0]["text"]}'.strip()[:160]
    manual = {'clips': clips, 'captions': captions, 'subtitles': True, 'normalize': False}
    from .hypit_picture import render_picture
    assembled = render_picture(source, folder, manual, width, height, meta, language=p.get('language') or 'en')
    page = (work / 'main.svml').read_text()
    from .db import connect
    with connect() as db:
        music = _music(pid, plan.get('music_asset_id') or '', db)
        held = _held_illustrations(pid, plan.get('illustrative_asset_ids') or [], db)
    inputs = [_describe(pid, 'source', 'owned_footage')]
    if logo_id:
        inputs.append(_describe(pid, f'assets/{logo_id}', 'logo'))
    if photo_ids:
        inputs.append(_describe(pid, f'assets/{photo_ids[0]}', 'owned_photo'))
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
        'engine': 'hypit',
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
            'note': 'One Hypit author prompt. This package calls no generation provider.',
        },
    }
    encoded = json.dumps(package, ensure_ascii=False)
    if _SECRET.search(encoded):
        raise ValueError('invalid_media_path')
    (folder / 'package.json').write_text(encoded)
    dest = folder / 'result.mp4'
    audio_args = ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart']
    if music and meta['has_audio']:
        music_path = _owned(pid, music['path'])
        ffmpeg('-i', assembled, '-i', music_path, '-filter_complex',
               '[0:a]volume=1[a1];[1:a]volume=0.18[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=0[a]',
               '-map', '0:v:0', '-map', '[a]', *audio_args, dest, timeout=600)
    elif music:
        ffmpeg('-i', assembled, '-i', _owned(pid, music['path']), '-map', '0:v:0', '-map', '1:a:0', *audio_args, dest, timeout=600)
    else:
        ffmpeg('-i', assembled, '-c', 'copy', '-movflags', '+faststart', dest, timeout=600)
    checked = probe(dest)
    if abs(checked['duration'] - float(plan['duration'])) > 0.45:
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
