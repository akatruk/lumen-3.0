"""Short licensed inserts for a high motion setting.

The source stays one file. A window shows a Commons clip whose subject is
already in the speech. A failed search adds nothing.
"""
import os
from pathlib import Path

from .media import ffmpeg

# English search only. The needle must occur in the words that were spoken.
THEMES = (
    (('泰国', 'thailand', 'thai'), 'Bangkok city street'),
    (('股东', 'shareholder'), 'business meeting'),
    (('董事', 'director'), 'board of directors'),
    (('注册', 'regist'), 'company office'),
    (('资本', 'capital'), 'business contract'),
    (('法人', 'representative'), 'office handshake'),
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


def _span(manual, needles):
    """A two-second window inside the phrase that named the subject."""
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
        open_at = min(start + 0.8, end - 1.2)
        return open_at, min(end, open_at + 2.0)
    return None


def windows(manual):
    """At most two inserts. Each one is a subject the host actually named."""
    blob = _blob(manual)
    chosen = []
    for needles, query in THEMES:
        if not any(needle in blob for needle in needles):
            continue
        span = _span(manual, needles)
        if not span:
            continue
        chosen.append({'query': query, 'start': round(span[0], 3), 'end': round(span[1], 3)})
        if len(chosen) == 2:
            break
    return chosen


# A place the host did not name is not a picture of this speech.
_ELSEWHERE = (
    'philippine', 'malaca', 'india', 'japan', 'korea', 'vietnam', 'indonesia',
    'malaysia', 'singapore', 'america', 'australia', 'africa', 'europe',
    'france', 'germany', 'brazil', 'russia', 'mexico', 'nigeria',
)


def relevant(found, query, speech=''):
    """Every search word must be in the clip, and the clip must not name another country."""
    if not isinstance(found, dict):
        return False
    blob = f"{found.get('title') or ''} {found.get('description') or ''} {found.get('artist') or ''}".lower()
    words = [word for word in str(query or '').lower().split() if len(word) > 4]
    if not words or not all(word in blob for word in words):
        return False
    spoken = str(speech or '').lower()
    return not any(place in blob and place not in spoken for place in _ELSEWHERE)


def attach(manual, work):
    """Download the windows. Tests and a failed search leave the picture without them."""
    ready = manual.get('_thematic_broll')
    if isinstance(ready, list):
        return ready
    if os.environ.get('PYTEST_CURRENT_TEST'):
        return []
    saved = []
    work = Path(work)
    speech = _blob(manual)
    try:
        from . import stock
    except Exception:
        return []
    for index, item in enumerate(windows(manual)):
        try:
            pages = stock.query(generator='search', gsrsearch=item['query'] + ' filetype:video', gsrnamespace=6, gsrlimit=8)
            found = None
            for page in pages or []:
                hit = stock.candidate(page)
                if hit and relevant(hit, item['query'], speech):
                    found = hit
                    break
            if not found:
                continue
            raw = work / f'broll-{index}.webm'
            clip = work / f'broll-{index}.mp4'
            stock.download(found['media_url'], raw)
            ffmpeg(
                '-ss', '0.4', '-i', str(raw), '-t', '2.0', '-an',
                '-vf', 'scale=480:854:force_original_aspect_ratio=increase,crop=480:854',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
                str(clip),
                timeout=120,
            )
            raw.unlink(missing_ok=True)
            if not clip.is_file() or clip.stat().st_size < 32:
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
