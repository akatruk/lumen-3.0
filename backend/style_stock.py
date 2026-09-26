"""Up to two Commons videos for a style cut, one per kept shot that measured an insert, cover, or b-roll.

A third shot adds none. Words alone do not. Only CC BY, CC0, and public domain pass.
Reference text is not a search query. Photo, illustration, and a second cover stay stills, at most two.
"""
import re
from . import stock

VIDEO_CAP = 2

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

def _video_fraction(shot, ref):
    """Insert, cover, or b-roll measured on the picture. A still and words alone are not a video."""
    from .style_match import _measured_insert
    from .style_pictures import measured_still
    if not isinstance(shot, dict) or measured_still(shot):
        return None
    return _measured_insert(shot, ref)

def _place_video(clip, fraction, asset_id, asset_duration, duration):
    from .style_match import _local_insert
    span = float(clip['end']) - float(clip['start'])
    length = min(1.2, span * 0.45, float(asset_duration))
    local = _local_insert(fraction, clip['start'], clip['end'], duration)
    if local is None or length < 0.5 or local + length > span + 1e-6:
        return False
    clip['cutaway'] = None
    clip['external_broll'] = {'asset_id': asset_id, 'start': round(local, 3), 'end': round(local + length, 3), 'source_start': 0}
    return True

def _attach_video(pid, edit, shots, script, report, duration, only=None):
    """One Commons video per kept shot that measured an insert, cover, or b-roll. At most two. Words add none."""
    from .manual import Edit, check
    from .style_match import _ref_span
    clips = edit.get('clips') or []
    if not shots:
        return edit, report
    served = {index % len(shots) for index, clip in enumerate(clips) if clip.get('external_broll')}
    used = sum(1 for clip in clips if clip.get('external_broll'))
    if used >= VIDEO_CAP:
        return edit, report
    indexes = [only] if only is not None else range(len(clips))
    ref = _ref_span(shots)
    attempted = set()
    missed = False
    attached = False
    for index in indexes:
        if used >= VIDEO_CAP:
            break
        if index < 0 or index >= len(clips):
            continue
        shot_index = index % len(shots)
        if shot_index in served or shot_index in attempted:
            continue
        clip = clips[index]
        if clip.get('external_broll'):
            served.add(shot_index)
            continue
        if clip.get('graphic') or clip.get('split') or clip.get('cutout'):
            continue
        fraction = _video_fraction(shots[shot_index], ref)
        if fraction is None:
            continue
        query = subject(clip.get('text'), script)
        if len(query) < 2:
            continue
        attempted.add(shot_index)
        try:
            pages = stock.query(generator='search', gsrsearch=query + ' filetype:video', gsrnamespace=6, gsrlimit=8)
            item = first_licensed(pages)
        except Exception:
            missed = True
            continue
        if not item:
            missed = True
            continue
        try:
            asset_id, asset_duration = stock.import_licensed(pid, item)
        except Exception:
            missed = True
            continue
        if not _place_video(clip, fraction, asset_id, asset_duration, duration):
            missed = True
            continue
        try:
            check(Edit.model_validate(edit), float(duration))
        except Exception:
            clip['external_broll'] = None
            missed = True
            continue
        served.add(shot_index)
        used += 1
        attached = True
    if attached:
        report = dict(report)
        report['gaps'] = [gap for gap in report.get('gaps') or [] if gap.get('id') != 'broll']
        applied = list(report.get('applied') or [])
        if 'stock' not in applied:
            applied.append('stock')
        report['applied'] = applied
        return edit, report
    if missed and not any(clip.get('external_broll') for clip in clips):
        return _open_broll(edit, report)
    return edit, report

def _unfilled_broll(edit, shots, report):
    """An empty Commons search does not close the essential gap and does not write a picture."""
    clips = edit.get('clips') or []
    if any(clip.get('external_broll') or str(clip.get('stock_still') or '').strip() for clip in clips):
        return edit, report
    if any(gap.get('id') == 'broll' for gap in report.get('gaps') or []):
        return edit, report
    from .style_match import _blob, _has
    if not _has(_blob(shots or []), ('b-roll', 'broll', 'stock footage')):
        return edit, report
    return _open_broll(edit, report)

def attach(pid, edit, shots, script, report, duration, only=None):
    """Up to two licensed videos, then at most two extra licensed stills. A still failure keeps the cut."""
    edit, report = _attach_video(pid, edit, shots, script, report, duration, only)
    try:
        from .style_pictures import attach_stills
        edit, report = attach_stills(pid, edit, shots, script, report, duration, only)
    except Exception:
        return _unfilled_broll(edit, shots, report)
    return _unfilled_broll(edit, shots, report)
