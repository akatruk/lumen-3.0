"""One generated picture for each measured graphic, from that graphic's own words.

A card, chart, icon, or illustration tiles ask for the picture.
A photo, an illustration still, or a second cover stays on Commons.
Words with no measured graphic do not call the image API.
"""
import base64
import json
import re
import shutil
import time
import uuid

import httpx

from .config import settings
from .db import connect, reserve, settle

STILL_CAP = 2
STILL_KINDS = {'photo', 'illustration', 'image', 'still', 'cutaway'}
_ART_PROMPT = 'Abstract editorial illustration, flat shapes, no text, no letters, no logos, no watermark, no people. Subject: '

def subject(text):
    """Owned words only. Letters outside the owned title or keyword are dropped."""
    cleaned = re.sub(r'[^0-9A-Za-z\u0400-\u04FF\u4e00-\u9fff ]+', ' ', text or '')
    return ' '.join(cleaned.split())[:80]

def graphic_words(clip):
    """The card title, or the owned keyword. Reference dialogue is not read."""
    card = clip.get('card') if isinstance(clip, dict) else None
    if isinstance(card, dict):
        title = card.get('title')
        if isinstance(title, dict):
            words = str(title.get('en') or title.get('zh') or '')
        else:
            words = str(title or '')
        cleaned = subject(words)
        if cleaned:
            return cleaned
    text = str((clip or {}).get('text') or '')
    for mark in ('● ', '▮ '):
        if text.startswith(mark):
            text = text[len(mark):]
    return subject(text)

def measured_graphic(clip):
    """A card, chart, icon, or illustration tiles. A Commons still is not one."""
    if not isinstance(clip, dict):
        return False
    if str(clip.get('stock_still') or '').strip():
        return False
    if clip.get('screen') is not None:
        return False
    if isinstance(clip.get('card'), dict):
        return True
    if clip.get('graphic'):
        return True
    if clip.get('icon'):
        return True
    try:
        tiles = int(clip.get('diagram') or 0)
    except (TypeError, ValueError):
        tiles = 0
    return tiles > 0

def image_bytes(payload):
    message = ((payload.get('choices') or [{}])[0].get('message') or {})
    found = []
    for image in message.get('images') or []:
        found.append((image.get('image_url') or {}).get('url') or '')
    content = message.get('content')
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                found.append((part.get('image_url') or {}).get('url') or '')
    for url in found:
        if url.startswith('data:image') and ',' in url:
            raw = base64.b64decode(url.split(',', 1)[1])
            if raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff'):
                return raw
    return None

def fetch(prompt):
    """Existing OpenRouter image call. One picture, no new client."""
    body = {'model': settings.image_model, 'modalities': ['image', 'text'], 'messages': [{'role': 'user', 'content': prompt}]}
    headers = {'Authorization': 'Bearer ' + settings.openrouter_api_key, 'Content-Type': 'application/json', 'X-Title': 'Lumen Studio'}
    with httpx.Client(timeout=60) as client:
        response = client.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=body)
    if response.status_code != 200:
        raise ValueError('style_image_failed')
    raw = image_bytes(response.json())
    if not raw or len(raw) > 8 * 1024 * 1024:
        raise ValueError('style_image_failed')
    return raw

def _reference_shots(pid):
    try:
        from .studio import state
        from .style_match import shots_of
        current = state(pid)
        if not current:
            return []
        return shots_of(current.get('dna'))
    except Exception:
        return []

def _remember(pid, manual):
    """Keep the saved edit on the picture that was just written. A database miss leaves the render payload."""
    try:
        names = {clip.get('id'): clip.get('art') or '' for clip in manual.get('clips') or [] if isinstance(clip, dict) and clip.get('id')}
        with connect() as db:
            row = db.execute('SELECT config FROM studio_manual WHERE project_id=?', (pid,)).fetchone()
            if row:
                config = json.loads(row['config'])
                for clip in config.get('clips') or []:
                    if clip.get('id') in names:
                        clip['art'] = names[clip['id']]
                db.execute('UPDATE studio_manual SET config=? WHERE project_id=?', (json.dumps(config), pid))
            if not any(names.values()):
                return
            project = db.execute('SELECT context FROM studio_projects WHERE project_id=?', (pid,)).fetchone()
            if not project:
                return
            context = json.loads(project['context'] or '{}')
            report = context.get('style_report') or {}
            applied = list(report.get('applied') or [])
            if 'art' not in applied:
                applied.append('art')
            report['applied'] = applied
            context['style_report'] = report
            db.execute('UPDATE studio_projects SET context=? WHERE project_id=?', (json.dumps(context, ensure_ascii=False), pid))
    except Exception:
        return

def attach_art(pid, manual, enabled=False):
    """One generated picture on each measured graphic. A missing key or a failed call keeps the layout."""
    del enabled
    if not manual:
        return manual
    clips = manual.get('clips') or []
    if not settings.openrouter_api_key:
        for clip in clips:
            if isinstance(clip, dict):
                clip['art'] = ''
        return manual
    shots = _reference_shots(pid)
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            continue
        still = bool(shots) and measured_still(shots[index % len(shots)])
        words = graphic_words(clip)
        if still or not measured_graphic(clip) or not words or index > 99:
            clip['art'] = ''
            continue
        name = f'style-art-{index}.png'
        try:
            token = reserve(pid, 0.08, 'style_illustration')
        except Exception:
            clip['art'] = ''
            continue
        try:
            raw = fetch(_ART_PROMPT + words)
            dest = settings.data_dir / pid / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            settle(token, 0.08)
            clip['art'] = name
        except Exception:
            try:
                settle(token, 0)
            except Exception:
                pass
            clip['art'] = ''
    _remember(pid, manual)
    return manual

def measured_still(shot):
    """A picture measurement asks for a still. The words photo and illustration do not."""
    if not isinstance(shot, dict):
        return False
    picture = shot.get('picture')
    if not isinstance(picture, dict) or picture.get('screen'):
        return False
    if picture.get('photo') is True or picture.get('illustration') is True:
        return True
    kind = str(picture.get('support') or '').strip().lower()
    if kind in STILL_KINDS:
        return True
    extra = picture.get('cutaways')
    return isinstance(extra, (list, tuple)) and len(extra) >= 2

def _owned_line(clip, edit, script):
    """Owned speech and the owned script. Reference text is not included."""
    from .style_stock import subject
    parts = [str(clip.get('text') or ''), str(script or '')]
    try:
        start, end = float(clip.get('start') or 0), float(clip.get('end') or 0)
    except (TypeError, ValueError):
        start, end = 0.0, 0.0
    for row in (edit or {}).get('captions') or []:
        if not isinstance(row, dict):
            continue
        try:
            if float(row.get('end') or 0) > start and float(row.get('start') or 0) < end:
                parts.append(str(row.get('original') or row.get('en') or ''))
        except (TypeError, ValueError):
            continue
    return subject(' '.join(parts), '')

def still_candidate(page):
    """One Commons image with the same CC BY / CC0 / public-domain rule as a video."""
    from . import stock
    info = (page.get('imageinfo') or [{}])[0]
    meta = info.get('extmetadata') or {}
    get = lambda key: stock.plain((meta.get(key) or {}).get('value', ''))
    license_name = get('LicenseShortName')
    license_url = get('LicenseUrl')
    by = bool(re.fullmatch(r'CC BY (?:1\.0|2\.0|2\.5|3\.0|4\.0)', license_name))
    public = license_name in ('Public domain', 'CC0', 'CC0 1.0')
    if not (by or public):
        return None
    if by and (not license_url.startswith('https://creativecommons.org/licenses/by/') or not get('Artist')):
        return None
    if public and license_url and not license_url.startswith('https://creativecommons.org/publicdomain/'):
        return None
    if get('Restrictions') or 'license review needed' in get('Categories').lower():
        return None
    url = str(info.get('url') or '')
    mime = str(info.get('mime') or '')
    if mime not in ('image/jpeg', 'image/png') or not stock.safe_media(url):
        return None
    try:
        width, height = int(info.get('width') or 0), int(info.get('height') or 0)
    except (TypeError, ValueError):
        return None
    if width < 64 or height < 64:
        return None
    page_id = page.get('pageid')
    if page_id is None:
        return None
    return {
        'page_id': page_id,
        'title': stock.plain(str(page.get('title') or '').removeprefix('File:'), 120),
        'description': get('ImageDescription'),
        'artist': get('Artist'),
        'license': license_name,
        'license_url': license_url,
        'source_url': f'https://commons.wikimedia.org/?curid={page_id}',
        'media_url': url,
        'width': width,
        'height': height,
        'mime': mime,
    }

def first_licensed_still(pages, skip=()):
    skipped = set(skip)
    for page in pages or []:
        item = still_candidate(page)
        if item and item['page_id'] not in skipped:
            return item
    return None

def import_still(pid, item):
    """Save one image that already passed the license filter. No generated picture."""
    from . import stock
    from .assets import path
    from .config import settings
    from .db import connect
    pages = stock.query(pageids=item['page_id'], prop='imageinfo', iiprop='url|size|mime|extmetadata')
    fresh = still_candidate(pages[0]) if pages else None
    if not fresh or (fresh['license'], fresh['license_url'], fresh['artist']) != (item['license'], item['license_url'], item['artist']):
        raise ValueError('stock_license_changed')
    if shutil.disk_usage(settings.data_dir).free < 1024**3:
        raise ValueError('storage_full')
    ident = uuid.uuid4().hex
    folder = settings.data_dir / pid / 'stock' / ident
    folder.mkdir(parents=True, exist_ok=True)
    try:
        suffix = '.png' if fresh['mime'] == 'image/png' else '.jpg'
        source = folder / f'source{suffix}'
        stock.download(fresh['media_url'], source)
        if source.stat().st_size < 32:
            raise ValueError('stock_media_invalid')
        fresh = dict(fresh)
        fresh['approval'] = 'written'
        metadata = {
            'kind': 'image',
            'mime': fresh['mime'],
            'width': fresh['width'],
            'height': fresh['height'],
            'provenance': {key: value for key, value in fresh.items() if key != 'media_url'},
        }
        attribution = f'{fresh["title"]} — {fresh["artist"]}; {fresh["license"]}; {fresh["license_url"]}; {fresh["source_url"]}'
        with connect() as db:
            db.lock()
            if db.execute('SELECT count(*) FROM studio_assets WHERE project_id=?', (pid,)).fetchone()[0] >= 20:
                raise ValueError('asset_limit')
            aid = uuid.uuid4().hex
            target = path(pid, aid)
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, target)
            db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)', (aid, pid, ident, fresh['title'], attribution, json.dumps(metadata), time.time()))
        return aid
    finally:
        shutil.rmtree(folder, ignore_errors=True)

def attach_stills(pid, edit, shots, script, report, duration, only=None):
    """Up to two extra licensed stills. An empty search leaves the slot and the existing gap."""
    del duration
    from . import stock
    clips = edit.get('clips') or []
    used = sum(1 for clip in clips if clip.get('stock_still'))
    if used >= STILL_CAP:
        return edit, report
    indexes = [only] if only is not None else range(len(clips))
    seen = []
    for index in indexes:
        if used >= STILL_CAP:
            break
        if index < 0 or index >= len(clips):
            continue
        clip = clips[index]
        shot = shots[index % len(shots)] if shots else {}
        if clip.get('stock_still') or clip.get('external_broll') or clip.get('screen') is not None:
            continue
        if not measured_still(shot):
            continue
        query = _owned_line(clip, edit, script)
        if len(query) < 2:
            continue
        try:
            pages = stock.query(generator='search', gsrsearch=query + ' filetype:bitmap', gsrnamespace=6, gsrlimit=4, prop='imageinfo', iiprop='url|size|mime|extmetadata')
            item = first_licensed_still(pages, seen)
            if not item:
                continue
            asset_id = import_still(pid, item)
        except Exception:
            continue
        if not asset_id:
            continue
        clip['stock_still'] = asset_id
        clip['art'] = ''
        seen.append(item['page_id'])
        used += 1
    return edit, report
