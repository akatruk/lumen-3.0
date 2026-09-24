"""Style match does not generate a picture for each element.

Diagrams stay owned words and tiles. A screenshot is an owned frame.
A measured photo, illustration, or extra cutaway may add a licensed Commons still.
"""
import json
import re
import shutil
import time
import uuid

STILL_CAP = 2
STILL_KINDS = {'photo', 'illustration', 'image', 'still', 'cutaway'}

def attach_art(pid, manual, enabled=False):
    """Drop a generated picture so it cannot enter the automatic cut."""
    del pid, enabled
    if not manual:
        return manual
    for clip in manual.get('clips') or []:
        if isinstance(clip, dict):
            clip['art'] = ''
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
