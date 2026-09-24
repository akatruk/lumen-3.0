"""One Commons insert for a style cut. Only CC BY, CC0, and public domain pass. Reference text is not a search query."""
import re
from . import stock

STOP = {'the', 'and', 'for', 'with', 'your', 'from', 'this', 'that', 'video', 'shot', 'clip'}

def subject(text, script):
    raw = f'{text or ""} {script or ""}'
    tokens = re.findall(r'[A-Za-z]{3,}|[\u0400-\u04FF]{3,}|[\u4e00-\u9fff]{2,}', raw)
    kept = [token for token in tokens if token.lower() not in STOP][:4]
    return ' '.join(kept)

def first_licensed(pages):
    for page in pages or []:
        item = stock.candidate(page)
        if item:
            return item
    return None

def _open_broll(edit, report):
    """No free clip. Leave the essential gap instead of substituting another video."""
    for clip in edit.get('clips') or []:
        if clip.get('external_broll'):
            continue
        clip['cutaway'] = None
    report = dict(report)
    gaps = [gap for gap in report.get('gaps') or [] if gap.get('id') != 'broll']
    gaps.append({'id': 'broll', 'essential': True})
    report['gaps'] = gaps
    if not any(clip.get('cutaway') or clip.get('external_broll') for clip in edit.get('clips') or []):
        report['applied'] = [name for name in (report.get('applied') or []) if name != 'cutaway']
    return edit, report

def attach(pid, edit, shots, script, report, duration, only=None):
    from .manual import Edit, check
    from .style_match import _blob, _has, _insert_fraction, _local_insert, _measured_insert, _ref_span
    clips = edit.get('clips') or []
    # One Commons clip for the whole cut. A second section does not add another.
    if any(i != only and clip.get('external_broll') for i, clip in enumerate(clips)):
        return edit, report
    indexes = [only] if only is not None else range(len(clips))
    ref = _ref_span(shots)
    fraction = None
    for shot in shots or []:
        found = _measured_insert(shot, ref)
        if found is not None:
            fraction = found
            break
    if fraction is None:
        for shot in shots or []:
            found = _insert_fraction(shot, ref)
            if found is not None:
                fraction = found
                break
    if fraction is None:
        return edit, report
    target = float(fraction) * float(duration)
    chosen = None
    fallback = None
    for index in indexes:
        if index < 0 or index >= len(clips):
            continue
        clip = clips[index]
        shot = shots[index % len(shots)] if shots else {}
        if clip.get('external_broll') or clip.get('graphic') or clip.get('split') or clip.get('cutout'):
            continue
        mentions = _has(_blob([shot]), ('b-roll', 'broll', 'stock footage', 'cutaway'))
        if _insert_fraction(shot, ref) is None and not mentions:
            continue
        if fallback is None:
            fallback = index
        if float(clip['start']) - 1e-6 <= target < float(clip['end']):
            chosen = index
            break
    if chosen is None:
        chosen = fallback
    if chosen is None:
        return edit, report
    query = subject(edit['clips'][chosen].get('text'), script)
    if len(query) < 2:
        return edit, report
    try:
        pages = stock.query(generator='search', gsrsearch=query + ' filetype:video', gsrnamespace=6, gsrlimit=8)
        item = first_licensed(pages)
        if not item:
            return _open_broll(edit, report)
        asset_id, asset_duration = stock.import_licensed(pid, item)
    except Exception:
        return _open_broll(edit, report)
    clip = edit['clips'][chosen]
    span = float(clip['end']) - float(clip['start'])
    length = min(1.2, span * 0.45, float(asset_duration))
    local = _local_insert(fraction, clip['start'], clip['end'], duration)
    if local is None or length < 0.5 or local + length > span + 1e-6:
        return _open_broll(edit, report)
    start_at = round(local, 3)
    end_at = round(local + length, 3)
    clip['cutaway'] = None
    clip['external_broll'] = {'asset_id': asset_id, 'start': start_at, 'end': end_at, 'source_start': 0}
    try:
        check(Edit.model_validate(edit), float(duration))
    except Exception:
        clip['external_broll'] = None
        return _open_broll(edit, report)
    report = dict(report)
    report['gaps'] = [gap for gap in report.get('gaps') or [] if gap.get('id') != 'broll']
    applied = list(report.get('applied') or [])
    if 'stock' not in applied:
        applied.append('stock')
    report['applied'] = applied
    return edit, report
