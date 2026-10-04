"""Short licensed inserts inside the graphic. The source stays one file.

The inserts slider decides how many spoken subjects get a window. A Commons
video is used when it names the subject. Otherwise a licensed photo of that
subject is turned into a short moving clip. A failed search adds nothing.
"""
import html
import os
import re
from pathlib import Path

import httpx

from .media import ffmpeg

_API = 'https://commons.wikimedia.org/w/api.php'
_HEADERS = {'User-Agent': 'Lumen/2.0 (https://lumen-fix.universalgravity.org; video asset discovery)'}
_BY = re.compile(r'CC BY (?:1\.0|2\.0|2\.5|3\.0|4\.0)$')
_PD = {'Public domain', 'CC0', 'CC0 1.0'}

# A place the host named, then the thing the video is about. A lone word is not a search.
_PLACES = (
    (('泰国', 'thailand', 'thai', 'bangkok', '中泰'), 'Bangkok'),
    (('中国', 'china', 'chinese', '上海', '北京'), 'China'),
)
_SUBJECTS = (
    (('注册', 'regist', '公司', 'company'), 'company office'),
    (('股东', 'shareholder'), 'business meeting'),
    (('董事', 'director', '法人', 'representative'), 'company directors'),
    (('资本', 'capital', '出资'), 'company capital'),
)
_PLACE_WORDS = {
    'bangkok': ('bangkok', 'thailand'),
    'china': ('china', 'chinese', 'shanghai', 'beijing'),
}
# A picture of another institution is not this video, even when one word matches.
_OFF = (
    'army', 'military', 'navy', 'soldier', 'devcom', 'rdecom', 'pentagon',
    'telegraph', 'railroad', 'locomotive', 'hong kong', 'temple', 'shrine',
    'pillar', 'dollar', 'banknote', 'advertisement', 'certificate',
)


def _blob(manual):
    parts = []
    for caption in (manual or {}).get('captions') or []:
        if not isinstance(caption, dict):
            continue
        for key in ('zh', 'original', 'en', 'ru'):
            text = str(caption.get(key) or '').strip()
            if text:
                parts.append(text)
    return ' '.join(parts).lower()


def quota(percent):
    """How many inner clips. 0 is none, 100 is six, and 20 is already one."""
    try:
        percent = max(0, min(100, int(percent)))
    except (TypeError, ValueError):
        percent = 0
    if percent <= 0:
        return 0
    return max(1, min(6, round(6 * percent / 100)))


def hold(percent):
    """How long each clip stays, from 1.5 seconds up to 3."""
    try:
        percent = max(0, min(100, int(percent)))
    except (TypeError, ValueError):
        percent = 0
    return round(1.5 + 1.5 * percent / 100, 1)


def _span(manual, needles, length, taken=()):
    """A window inside a phrase that named the subject and is still free."""
    length = max(1.2, float(length))
    for caption in (manual or {}).get('captions') or []:
        if not isinstance(caption, dict):
            continue
        text = ' '.join(str(caption.get(key) or '') for key in ('zh', 'original', 'en', 'ru')).lower()
        if not any(needle in text for needle in needles):
            continue
        try:
            start, end = float(caption.get('start') or 0), float(caption.get('end') or 0)
        except (TypeError, ValueError):
            continue
        if end - start < 1.2:
            continue
        open_at = min(start + 0.6, max(start, end - length))
        for _ in range(4):
            span_end = min(end, open_at + length)
            if span_end - open_at < 1.2:
                break
            blocker = next((stop for begin, stop in taken if open_at < stop and span_end > begin), None)
            if blocker is None:
                return open_at, span_end
            open_at = blocker + 0.2
    return None


def theme_phrase(manual):
    """The video's subject, in the prompt. Empty when the speech names none of it."""
    blob = _blob(manual)
    places = []
    if any(needle in blob for needle in _PLACES[0][0]):
        places.append('Таиланд')
    if any(needle in blob for needle in _PLACES[1][0]):
        places.append('Китай')
    topics = []
    if any(needle in blob for needle in _SUBJECTS[0][0]):
        topics.append('регистрация компании')
    if any(needle in blob for needle in _SUBJECTS[1][0]):
        topics.append('акционеры')
    if any(needle in blob for needle in _SUBJECTS[2][0]):
        topics.append('директора')
    if any(needle in blob for needle in _SUBJECTS[3][0]):
        topics.append('капитал')
    parts = []
    if places:
        parts.append(' и '.join(places))
    if topics:
        parts.append(', '.join(topics))
    return ', '.join(parts)


def _scenes(blob):
    """Pictures of the places this video is about, not a photo that merely shares one word."""
    thai = any(needle in blob for needle in _PLACES[0][0])
    china = any(needle in blob for needle in _PLACES[1][0])
    business = any(needle in blob for needles, _query in _SUBJECTS for needle in needles)
    scenes = []
    if thai:
        scenes.append((('泰国', 'thailand', 'thai', 'bangkok', '中泰'), 'Bangkok city hall'))
    if china:
        scenes.append((('中国', 'china', 'chinese', '上海', '北京'), 'Shanghai skyline'))
    if china and business:
        scenes.append((('资本', 'capital', '出资', '股东', 'shareholder', '董事', 'director'), 'Beijing financial street'))
    elif thai and business:
        scenes.append((('注册', 'regist', '资本', 'capital', '公司', 'company'), 'Bangkok city'))
    return scenes


def windows(manual, limit=2, length=2.0):
    """Inserts of the video's own subject, up to the slider. A lone noun is not a search."""
    limit = max(0, int(limit))
    blob = _blob(manual)
    chosen = []
    for needles, query in _scenes(blob):
        if limit and len(chosen) >= limit:
            break
        span = _span(manual, needles, length, [(item['start'], item['end']) for item in chosen])
        if not span:
            continue
        if any(span[0] < item['end'] and span[1] > item['start'] for item in chosen):
            continue
        chosen.append({'query': query, 'start': round(span[0], 3), 'end': round(span[1], 3)})
    return chosen


def _on_theme(query, title, speech):
    """The picture has to name a place the host named, and not another institution."""
    title = str(title or '').lower()
    spoken = str(speech or '').lower()
    folded = str(query or '').lower()
    for place, words in _PLACE_WORDS.items():
        if place in folded.split():
            if not any(word in title for word in words):
                return False
    if any(token in title and token not in spoken for token in _OFF):
        return False
    skip = {word for words in _PLACE_WORDS.values() for word in words}
    subject = [word for word in folded.split() if len(word) > 3 and word not in skip]
    if subject and not all(word in title for word in subject):
        return False
    return True


# A place the host did not name is not a picture of this speech.
_ELSEWHERE = (
    'philippine', 'malaca', 'india', 'japan', 'korea', 'vietnam', 'indonesia',
    'malaysia', 'singapore', 'america', 'australia', 'africa', 'europe',
    'france', 'germany', 'brazil', 'russia', 'mexico', 'nigeria',
    'harris', 'biden', 'white house',
)


def relevant(found, query, speech=''):
    """Every search word must be in the clip, and the clip must not name another country."""
    if not isinstance(found, dict):
        return False
    title = str(found.get('title') or '').lower()
    blob = f"{title} {found.get('description') or ''} {found.get('artist') or ''}".lower()
    words = [word for word in str(query or '').lower().split() if len(word) > 4]
    if not words or not all(word in title for word in words):
        return False
    if not _on_theme(query, title, speech):
        return False
    spoken = str(speech or '').lower()
    return not any(place in blob and place not in spoken for place in _ELSEWHERE)


def _plain(value):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', str(value or ''))).split())


def _meta(info, key):
    raw = (info.get('extmetadata') or {}).get(key) or {}
    return _plain(raw.get('value', '') if isinstance(raw, dict) else '')


def _safe_image(url):
    try:
        from urllib.parse import urlsplit
        parts = urlsplit(url)
    except ValueError:
        return False
    return (
        parts.scheme == 'https' and parts.hostname in ('upload.wikimedia.org', 'thumb.wikimedia.org')
        and parts.port in (None, 443) and not parts.username and parts.path.startswith('/wikipedia/commons/')
    )


def image_hit(page, query, speech):
    """A licensed still of the searched subject. Share-alike stays out."""
    if not isinstance(page, dict):
        return None
    info = (page.get('imageinfo') or [{}])[0]
    if not isinstance(info, dict):
        return None
    license_name = _meta(info, 'LicenseShortName')
    artist = _meta(info, 'Artist')
    by = bool(_BY.fullmatch(license_name))
    public = license_name in _PD
    if by and not artist:
        return None
    if not (by or public):
        return None
    url = next((item for item in (info.get('thumburl'), info.get('url')) if _safe_image(item or '')), '')
    if not url:
        return None
    title = _plain(str(page.get('title') or '').removeprefix('File:'))
    found = {'title': title, 'description': _meta(info, 'ImageDescription'), 'artist': artist, 'media_url': url}
    words = [word for word in str(query or '').lower().split() if len(word) > 4]
    blob = f"{title} {found['description']} {artist}".lower()
    if any(token in title.lower() for token in ('typeface', 'font', 'logo', 'icon', 'coat of arms', 'flag of')):
        return None
    if any(token in blob for token in ('bakery', 'restaurant', 'shrine')):
        return None
    if words and max(words, key=len) not in blob:
        return None
    if not _on_theme(query, title, speech):
        return None
    spoken = str(speech or '').lower()
    if any(place in blob and place not in spoken for place in _ELSEWHERE):
        return None
    return found


def _image_pages(query):
    response = httpx.get(
        _API,
        params={
            'action': 'query', 'format': 'json', 'generator': 'search',
            'gsrsearch': query + ' filetype:bitmap', 'gsrnamespace': 6, 'gsrlimit': 12,
            'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiurlwidth': 1280,
        },
        headers=_HEADERS,
        timeout=25,
    )
    response.raise_for_status()
    pages = (response.json().get('query') or {}).get('pages') or {}
    if isinstance(pages, dict):
        return list(pages.values())
    return list(pages) if isinstance(pages, list) else []


def _zoom(raw, clip, length):
    frames = max(30, int(round(float(length) * 30)))
    ffmpeg(
        '-loop', '1', '-i', str(raw), '-frames:v', str(frames), '-an',
        '-vf', (
            'scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,'
            f"zoompan=z='min(1.08,1.0+0.0004*on)':d={frames}:s=640x360:fps=30"
        ),
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
        str(clip),
        timeout=120,
    )


def _save_clip(work, index, url, length, still):
    raw = work / f'broll-{index}.src'
    clip = work / f'broll-{index}.mp4'
    from urllib.parse import urlsplit
    if urlsplit(url).hostname == 'upload.wikimedia.org':
        from . import stock
        stock.download(url, raw)
    else:
        with httpx.stream('GET', url, headers=_HEADERS, timeout=30, follow_redirects=False) as response:
            if response.status_code != 200:
                raise ValueError('stock_unavailable')
            size = 0
            with raw.open('wb') as handle:
                for chunk in response.iter_bytes(256 * 1024):
                    size += len(chunk)
                    if size > 12 * 1024 * 1024:
                        raise ValueError('stock_media_too_large')
                    handle.write(chunk)
    if still:
        _zoom(raw, clip, length)
    else:
        ffmpeg(
            '-ss', '0.3', '-i', str(raw), '-t', f'{length:.2f}', '-an',
            '-vf', 'scale=640:360:force_original_aspect_ratio=increase,crop=640:360',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
            str(clip),
            timeout=120,
        )
    raw.unlink(missing_ok=True)
    if not clip.is_file() or clip.stat().st_size < 32:
        return None
    return clip


def attach(manual, work):
    """Download the windows. Tests and a failed search leave the picture without them."""
    ready = manual.get('_thematic_broll')
    if isinstance(ready, list):
        return ready
    if os.environ.get('PYTEST_CURRENT_TEST'):
        return []
    from .presentation_graphics import animation_levels
    share = animation_levels(manual)['inserts']
    if quota(share) <= 0:
        return []
    saved = []
    work = Path(work)
    speech = _blob(manual)
    length = hold(share)
    try:
        from . import stock
    except Exception:
        stock = None
    for index, item in enumerate(windows(manual, quota(share), length)):
        found = None
        still = False
        try:
            words = [word for word in item['query'].lower().split() if len(word) > 4]
            best_score = -1
            for page in _image_pages(item['query']):
                hit = image_hit(page, item['query'], speech)
                if not hit:
                    continue
                title = hit['title'].lower()
                score = sum(word in title for word in words)
                if score > best_score:
                    found = hit
                    still = True
                    best_score = score
            if found is None and stock is not None:
                pages = stock.query(generator='search', gsrsearch=item['query'] + ' filetype:video', gsrnamespace=6, gsrlimit=6)
                for page in pages or []:
                    hit = stock.candidate(page)
                    if hit and relevant(hit, item['query'], speech):
                        found = hit
                        break
            if not found:
                continue
            clip = _save_clip(work, index, found['media_url'], max(1.2, item['end'] - item['start']), still)
            if clip is None:
                continue
            saved.append({
                'src': clip.name,
                'start': item['start'],
                'end': item['end'],
                'credit': str(found.get('artist') or '')[:48],
            })
        except Exception:
            continue
    return saved
