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

def attach(pid, edit, shots, script, report, duration, only=None):
    from .manual import Edit, check
    from .style_match import _blob, _has
    indexes = [only] if only is not None else range(len(edit.get('clips') or []))
    chosen = None
    for index in indexes:
        if index < 0 or index >= len(edit['clips']):
            continue
        clip = edit['clips'][index]
        shot = shots[index % len(shots)] if shots else {}
        if clip.get('external_broll') or clip.get('graphic') or clip.get('split') or clip.get('cutout'):
            continue
        if not _has(_blob([shot]), ('b-roll', 'broll', 'stock footage')):
            continue
        chosen = index
        break
    if chosen is None:
        return edit, report
    query = subject(edit['clips'][chosen].get('text'), script)
    if len(query) < 2:
        return edit, report
    try:
        pages = stock.query(generator='search', gsrsearch=query + ' filetype:video', gsrnamespace=6, gsrlimit=8)
        item = first_licensed(pages)
        if not item:
            return edit, report
        asset_id, asset_duration = stock.import_licensed(pid, item)
    except Exception:
        return edit, report
    clip = edit['clips'][chosen]
    span = float(clip['end']) - float(clip['start'])
    length = min(1.2, span * 0.45, asset_duration)
    end = round(0.12 + length, 3)
    if length < 0.5 or end > span:
        return edit, report
    clip['cutaway'] = None
    clip['external_broll'] = {'asset_id': asset_id, 'start': 0.12, 'end': end, 'source_start': 0}
    try:
        check(Edit.model_validate(edit), float(duration))
    except Exception:
        clip['external_broll'] = None
        return edit, report
    report = dict(report)
    report['gaps'] = [gap for gap in report.get('gaps') or [] if gap.get('id') != 'broll']
    applied = list(report.get('applied') or [])
    if 'stock' not in applied:
        applied.append('stock')
    report['applied'] = applied
    return edit, report
