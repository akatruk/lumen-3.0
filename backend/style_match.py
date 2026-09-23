"""Optional visual-style match. Builds a normal manual edit from reference DNA and renders it with the existing pipeline.

Reference files, dialogue, music and packaging never become export inputs. Effects the renderer cannot reproduce are listed on the fidelity report.
"""
import json
import re
from fastapi import APIRouter, Depends, HTTPException
from .auth import current_user
from .db import connect, enqueue, project
from .manual import Clip, Edit, check
from .schemas import Caption

router = APIRouter(prefix='/api/studio')
SCORE_KEYS = ('shot_structure', 'visual_pacing', 'effect_similarity', 'motion_graphic_style', 'color_treatment', 'production_quality')
GAP_RULES = (
    ('motion_tracking', ('tracking', 'track the', 'follow the subject'), False),
    ('presenter_cutout', ('cutout', 'cut out', 'green screen'), False),
    ('background_replacement', ('background replace', 'replace the background', 'new background'), False),
    ('speed_ramp', ('speed ramp', 'slow motion', 'slow-mo'), False),
    ('mask', ('masking', 'mask'), False),
    ('split_screen', ('split screen', 'split-screen'), False),
    ('color_grade', ('color grade', 'colour grade', 'color match', 'lighting match'), False),
    ('kinetic_type', ('kinetic', 'animated title', 'title card'), False),
    ('number_card', ('chart', 'number card', 'statistic', 'progress bar', 'progress'), True),
    ('broll', ('b-roll', 'broll', 'stock footage'), True),
    ('blur', ('blur', 'bokeh'), False),
    ('glow', ('glow', 'bloom'), False),
    ('shadow', ('drop shadow', 'shadows', 'shadow'), False),
    ('stabilize', ('stabilize', 'stabilisation', 'shaky'), False),
)
STOP = {'the', 'a', 'an', 'and', 'or', 'to', 'of', 'in', 'on', 'for', 'is', 'it', 'this', 'that', 'with', 'from', 'your', 'none', 'na'}
FACT = re.compile(r'(?P<label>[A-Za-z\u0400-\u04FF][A-Za-z\u0400-\u04FF0-9 ]{1,40}?)\s+(?P<num>\d+(?:[.,]\d+)?)(?P<unit>\s*(?:%|percent|days|day|years|year|months|month|bedrooms|baths))?', re.I)

def plain(value):
    if isinstance(value, dict):
        return ' '.join(str(value.get(k) or '') for k in ('en', 'zh', 'original'))
    return '' if value is None else str(value)

def shots_of(dna):
    rows = []
    for entry in dna or []:
        for shot in (entry.get('analysis') or {}).get('shots') or []:
            if isinstance(shot, dict):
                rows.append(shot)
    return rows

def _blob(shots):
    keys = ('motion', 'transition', 'visual_type', 'narrative_role', 'subtitle_emphasis', 'reusable_method', 'observation', 'music', 'information_density')
    return ' '.join(plain(shot.get(key)) for shot in shots for key in keys).lower()

def _has(blob, needles):
    return any(re.search(r'(^|[^a-z])' + re.escape(needle) + r'([^a-z]|$)', blob) for needle in needles)

def _motion(shot):
    blob = (plain(shot.get('motion')) + ' ' + plain(shot.get('reusable_method'))).lower()
    if _has(blob, ('close-up', 'close up', 'tight', 'punch')):
        return 1.2, 1.45
    if _has(blob, ('zoom', 'push-in', 'push in', 'push')):
        return 1.05, 1.22
    return 1.0, None

def _transition(shot):
    blob = plain(shot.get('transition')).lower()
    name = 'cut'
    for needle, kind in (('circle', 'circle'), ('wipe', 'wipe'), ('crossfade', 'crossfade'), ('dissolve', 'crossfade'), ('fade', 'fade'), ('zoom', 'zoom')):
        if _has(blob, (needle,)):
            name = kind
            break
    if name == 'cut' and ((shot.get('picture') or {}).get('graphic') or (shot.get('picture') or {}).get('fade')):
        return 'fade'
    return name

def _shot_type(shot):
    blob = plain(shot.get('visual_type')).lower()
    if _has(blob, ('close-up', 'close up', 'tight')):
        return 'close_up'
    if _has(blob, ('document',)):
        return 'document'
    return 'presenter'

def _wants_captions(shots):
    ignore = {'', 'none', 'n/a', 'na', '-', '无', 'нет'}
    return any(plain(shot.get('subtitle_emphasis')).strip().lower() not in ignore for shot in shots)

def _frame(shot):
    picture = shot.get('picture') if isinstance(shot.get('picture'), dict) else None
    if picture:
        zoom = float(picture.get('zoom') or 1)
        zoom_end = picture.get('zoom_end')
        x = float(picture.get('x') if picture.get('x') is not None else 0.5)
        x_end = picture.get('x_end')
        return {'zoom': zoom, 'zoom_end': zoom_end, 'x': x, 'y': 0.45 if zoom > 1.05 else 0.5, 'x_end': x_end, 'y_end': None}
    blob = (plain(shot.get('motion')) + ' ' + plain(shot.get('reusable_method')) + ' ' + plain(shot.get('visual_type'))).lower()
    zoom, zoom_end = _motion(shot)
    x, y, x_end, y_end = 0.5, 0.5, None, None
    if _has(blob, ('pan left', 'move left')):
        x, x_end = 0.62, 0.38
    elif _has(blob, ('pan right', 'move right')):
        x, x_end = 0.38, 0.62
    if _has(blob, ('tilt up',)):
        y, y_end = 0.62, 0.38
    elif _has(blob, ('tilt down',)):
        y, y_end = 0.38, 0.62
    elif _has(blob, ('close-up', 'close up', 'tight', 'punch')):
        y = 0.4
    return {'zoom': zoom, 'zoom_end': zoom_end, 'x': x, 'y': y, 'x_end': x_end, 'y_end': y_end}

def _keywords(text):
    if not text:
        return []
    found = []
    for number in re.findall(r'\d+(?:[.,]\d+)?%?', text):
        if number in text and number not in found:
            found.append(number[:48])
    words = re.findall(r'[A-Za-z\u0400-\u04FF]{4,}', text)
    for word in sorted(words, key=len, reverse=True):
        if len(found) >= 3:
            break
        if word.lower() not in STOP and word in text and word not in found:
            found.append(word[:48])
    return found[:3]

def _facts(script, transcript):
    text = (script or '') + '\n' + '\n'.join((cap.get('original') or cap.get('en') or '') for cap in transcript or [])
    found = []
    seen = set()
    for match in FACT.finditer(text):
        words = [w for w in match.group('label').split() if w.lower() not in STOP]
        label = ' '.join(words[-3:]).strip()
        if len(label) < 3:
            continue
        raw = match.group('num').replace(',', '')
        try:
            value = float(raw)
        except ValueError:
            continue
        if not 0 <= value <= 1e12:
            continue
        figure = (match.group('num') + (match.group('unit') or '')).strip()[:48]
        key = (label.lower(), figure)
        if key in seen:
            continue
        seen.add(key)
        found.append((label[:48], figure, value))
        if len(found) == 4:
            break
    return found

def _safe_removes(recommendations, transcript, duration):
    removes = []
    for rec in recommendations or []:
        if rec.get('action') != 'remove':
            continue
        try:
            a, b = float(rec.get('start', 0)), float(rec.get('end', 0))
        except (TypeError, ValueError):
            continue
        if not 0 <= a < b <= duration or b - a < 0.3:
            continue
        if any(max(0, min(b, float(c.get('end', 0))) - max(a, float(c.get('start', 0)))) > 0.2 for c in transcript or []):
            continue
        removes.append((a, b))
    return removes

def _overlap(start, end, spans):
    return sum(max(0, min(end, b) - max(start, a)) for a, b in spans)

def _structure(cuts, removes, recommendations, duration):
    kept = [c for c in cuts if _overlap(c[0], c[1], removes) <= 0.7 * (c[1] - c[0])] or list(cuts)
    front = next((r for r in recommendations or [] if r.get('action') == 'move_to_front'), None)
    if not front:
        return kept
    try:
        a, b = float(front.get('start', 0)), float(front.get('end', 0))
    except (TypeError, ValueError):
        return kept
    if not (0 <= a < b <= duration and b - a >= 0.4) or _overlap(a, b, removes) >= 0.5 * (b - a):
        return kept
    index = max(range(len(kept)), key=lambda i: _overlap(kept[i][0], kept[i][1], [(a, b)]))
    if _overlap(kept[index][0], kept[index][1], [(a, b)]) <= 0.2:
        return kept
    return [kept[index], *kept[:index], *kept[index + 1:]]

def beat_count(shots, duration):
    lengths = []
    for shot in shots:
        try:
            lengths.append(max(0.2, float(shot['end']) - float(shot['start'])))
        except (KeyError, TypeError, ValueError):
            continue
    if not lengths:
        return 1
    average = sum(lengths) / len(lengths)
    return max(1, min(12, round(float(duration) / max(average, 0.8))))

def _snap(target, transcript, previous, duration):
    point = target
    for cap in transcript or []:
        start, end = float(cap.get('start', 0)), float(cap.get('end', 0))
        if start + 0.15 < target < end - 0.15:
            point = start if target - start <= end - target else end
            break
    return max(previous + 0.4, min(point, duration - 0.4))

def ranges(duration, count, transcript):
    duration = round(float(duration), 3)
    count = max(1, min(12, int(count)))
    if count == 1 or duration < 0.8:
        return [(0.0, duration)]
    points = [0.0]
    for i in range(1, count):
        point = _snap(duration * i / count, transcript, points[-1], duration)
        if duration - point < 0.4:
            break
        points.append(round(point, 3))
    points.append(duration)
    clips = []
    for index in range(len(points) - 1):
        start, end = points[index], points[index + 1]
        if end - start < 0.08 and clips:
            clips[-1] = (clips[-1][0], end)
        elif end > start:
            clips.append((round(start, 3), round(end, 3)))
    if not clips:
        return [(0.0, duration)]
    clips[-1] = (clips[-1][0], duration)
    return clips

def _spoken(start, end, transcript):
    parts = []
    for cap in transcript or []:
        if float(cap.get('end', 0)) <= start or float(cap.get('start', 0)) >= end:
            continue
        parts.append((cap.get('original') or cap.get('en') or cap.get('zh') or '').strip())
    return ' '.join(part for part in parts if part)

def _captions(transcript, emphasize):
    rows = []
    for cap in transcript or []:
        try:
            row = Caption.model_validate(cap)
        except Exception:
            return []
        if not (row.en.strip() or row.zh.strip() or row.original.strip()):
            continue
        if emphasize:
            row.emphasis_en = [w for w in _keywords(row.en or row.original) if w in (row.en or row.original)][:3]
            row.emphasis_zh = [w for w in _keywords(row.zh) if w in row.zh][:3]
        rows.append(row)
    return rows

def _bars(facts):
    peak = max((item[2] for item in facts), default=0) or 1
    return [round(max(0.08, min(1, item[2] / peak)), 3) for item in facts[:5]]

def _card(facts, length):
    from .visuals import CardText, DataItem, VisualCard
    span = min(length - 0.05, 3.0)
    if span < 0.7 or not facts:
        return None
    source = CardText(en='From your script', zh='来自你的脚本')
    try:
        if len(facts) >= 2:
            items = [DataItem(label=CardText(en=label, zh=label), value=value) for label, _figure, value in facts]
            animation = 'grow' if 0.6 <= span - 0.3 else 'none'
            return VisualCard(kind='bar_chart', start=0.15, end=round(span, 3), title=CardText(en='Your figures', zh='你的数字'), primary=CardText(en='From your script', zh='来自你的脚本'), source=source, items=items, animation=animation, animation_seconds=0.6)
        label, figure, _value = facts[0]
        return VisualCard(kind='number', start=0.15, end=round(span, 3), title=CardText(en=label, zh=label), primary=CardText(en=figure, zh=figure), source=source)
    except Exception:
        return None

def _panel_start(start, end, duration):
    window = min(1.2, max(0.5, (end - start) * 0.45))
    if duration - end >= window:
        return round(end, 3)
    if start >= window:
        return 0.0
    return None

def _cutaway(shot, start, end, duration):
    from .manual import Cutaway
    blob = (plain(shot.get('visual_type')) + ' ' + plain(shot.get('reusable_method')) + ' ' + plain(shot.get('narrative_role'))).lower()
    if not _has(blob, ('b-roll', 'broll', 'cutaway')):
        return None
    length = end - start
    window = min(1.2, length * 0.45)
    if window < 0.5:
        return None
    if duration - end >= window:
        src = round(end, 3)
    elif start >= window:
        src = 0.0
    else:
        return None
    local_end = round(0.12 + window, 3)
    if local_end > length or src + window > duration + 1e-6:
        return None
    return Cutaway(start=0.12, end=local_end, source_start=src)

def _effects(shot, ref_len, flat, chroma=False, look_split=False, look_shake=False):
    blob = _blob([shot or {}])
    return {
        'blur': 2.0 if _has(blob, ('blur', 'bokeh')) else 0,
        'glow': _has(blob, ('glow', 'bloom')),
        'shadow': _has(blob, ('drop shadow', 'shadows', 'shadow')) or bool((shot.get('picture') or {}).get('vignette')),
        'split': _has(blob, ('split screen', 'split-screen')) or bool(look_split) or bool((shot.get('picture') or {}).get('split')),
        'stabilize': _has(blob, ('stabilize', 'stabilisation', 'shaky')) or bool(look_shake),
        'cutout': bool(flat or chroma) and _has(blob, ('cutout', 'cut out', 'green screen', 'background replace', 'replace the background')),
        'mask': _has(blob, ('masking', 'mask')),
        'speed': 1.35 if ref_len < 0.55 else 0.75 if _has(blob, ('slow motion', 'slow-mo', 'speed ramp')) else 1.0,
        'kinetic': _has(blob, ('kinetic', 'animated title', 'title card')),
    }

def _clip(shot, start, end, transcript, ident, duration, facts, allow_card, look=None, ref_len=None, progress=0):
    look = look or {}
    frame = _frame(shot or {})
    track = look.get('track') if _has(_blob([shot or {}]), ('tracking', 'track the', 'follow the subject')) else None
    if track:
        frame['x'], frame['x_end'] = track['x0'], track['x1']
    moving = frame['zoom_end'] is not None or frame['x_end'] is not None or frame['y_end'] is not None
    spoken = _spoken(start, end, transcript)
    words = _keywords(spoken)
    blob = _blob([shot or {}])
    callout = bool(words) and (_wants_captions([shot or {}]) or _has(blob, ('title', 'overlay', 'callout', 'keyword', 'kinetic', 'icon')) or look.get('lower') or look.get('bar'))
    picture = shot.get('picture') or {}
    card = _card(facts, end - start) if (allow_card and _has(blob, ('chart', 'number', 'statistic', 'progress'))) or picture.get('graphic') else None
    fx = _effects(shot, end - start if ref_len is None else ref_len, look.get('flat'), chroma=bool(look.get('chroma')), look_split=bool(look.get('split')), look_shake=bool(look.get('shake')))
    open_shot = not fx['split'] and not fx['cutout'] and not (picture.get('graphic') and facts)
    screen = (_panel_start(start, end, duration) if _panel_start(start, end, duration) is not None else start) if open_shot and (picture.get('screen') or _has(blob, ('screenshot', 'screen recording', 'screen capture'))) else None
    diagram = max(1, min(4, len(words) or 3)) if open_shot and screen is None and _has(blob, ('illustration', 'diagram', 'infographic', 'drawing')) else 0
    text = (words[0][:40] if callout else '')
    if diagram and words and not text:
        text = words[0][:40]
    if text and _has(blob, ('icon', 'chart', 'progress')):
        mark = '▮ ' if _has(blob, ('chart', 'progress')) else '● '
        text = (mark + text)[:160]
    grade = None
    if look.get('grade'):
        from .manual import Grade
        grade = Grade.model_validate(look['grade'])
    return Clip(
        id=ident,
        start=start,
        end=end,
        zoom=frame['zoom'],
        zoom_end=frame['zoom_end'],
        x=frame['x'],
        y=frame['y'],
        x_end=frame['x_end'],
        y_end=frame['y_end'],
        motion_seconds=round(min(end - start, 4.0), 3) if moving else None,
        transition=_transition(shot or {}),
        shot_type=_shot_type(shot or {}),
        text=text,
        audio_fade_ms=16 if _transition(shot or {}) != 'cut' else 0,
        cutaway=None if card or fx['cutout'] or fx['split'] else _cutaway(shot or {}, start, end, duration),
        card=card,
        enhance=grade is None,
        speed=fx['speed'],
        blur=fx['blur'],
        glow=fx['glow'],
        shadow=fx['shadow'],
        split=fx['split'],
        stabilize=fx['stabilize'],
        cutout=fx['cutout'],
        kinetic=bool(fx['kinetic'] and text),
        mask=bool(fx['mask'] and not fx['cutout'] and not fx['split']),
        track=bool(track),
        exposure=float(look.get('exposure') or 0),
        progress=max(0, min(1, float(progress or 0))),
        plate='1A1F1C' if fx['cutout'] else '',
        graphic=bool(picture.get('graphic') and facts and not fx['split'] and not fx['cutout']),
        bars=_bars(facts) if picture.get('graphic') and facts and not fx['split'] and not fx['cutout'] else [],
        lower=bool((look.get('lower') or _has(blob, ('icon',))) and not picture.get('graphic') and not fx['split'] and not fx['cutout'] and screen is None and not diagram),
        icon=bool((look.get('lower') or _has(blob, ('icon',))) and not picture.get('graphic') and not fx['split'] and not fx['cutout'] and screen is None and not diagram),
        panel=_panel_start(start, end, duration) if fx['split'] and not fx['cutout'] else None,
        still=(_panel_start(start, end, duration) if _panel_start(start, end, duration) is not None else start) if picture.get('graphic') and not facts and not fx['split'] and not fx['cutout'] and screen is None and not diagram else None,
        screen=screen,
        diagram=diagram,
        grade=grade,
        approved=True,
        locked=False,
    )

def _gaps(shots, edit):
    blob = _blob(shots)
    found = [{'id': ident, 'essential': essential} for ident, needles, essential in GAP_RULES if _has(blob, needles)]
    if _wants_captions(shots) and not edit['subtitles']:
        found.append({'id': 'captions_need_speech', 'essential': True})
    if any(plain(shot.get('music')).strip() for shot in shots):
        found.append({'id': 'reference_music', 'essential': False})
    if any(c.get('card') for c in edit['clips']):
        found = [g for g in found if g['id'] != 'number_card']
    if any(c.get('cutaway') or c.get('external_broll') for c in edit['clips']):
        found = [g for g in found if g['id'] != 'broll']
    clips = edit['clips']
    done = set()
    if any(c.get('blur') for c in clips): done.add('blur')
    if any(c.get('glow') for c in clips): done.add('glow')
    if any(c.get('shadow') for c in clips): done.add('shadow')
    if any(c.get('split') for c in clips): done.add('split_screen')
    if any(c.get('stabilize') for c in clips): done.add('stabilize')
    if any(c.get('cutout') for c in clips): done.update(('presenter_cutout', 'background_replacement'))
    if any(c.get('grade') for c in clips): done.add('color_grade')
    if any(abs((c.get('speed') or 1) - 1) > 0.04 for c in clips): done.add('speed_ramp')
    if any(c.get('kinetic') for c in clips): done.add('kinetic_type')
    if any(c.get('track') for c in clips): done.add('motion_tracking')
    if any(c.get('mask') for c in clips): done.add('mask')
    return [g for g in found if g['id'] not in done]

def _scores(shots, edit, gaps, duration):
    clips = edit['clips']
    reference_count = max(1, len(shots))
    structure = round(100 * min(reference_count, len(clips)) / max(reference_count, len(clips)), 1)
    if shots:
        ref_avg = sum(max(0.2, float(s.get('end', 0)) - float(s.get('start', 0))) for s in shots) / len(shots)
        own_avg = sum(c['end'] - c['start'] for c in clips) / len(clips)
        pacing = round(100 * min(ref_avg, own_avg) / max(ref_avg, own_avg), 1)
    else:
        pacing = 50.0
    requested = applied = 0
    for index, clip in enumerate(clips):
        shot = shots[index % len(shots)] if shots else None
        if not shot:
            continue
        frame = _frame(shot)
        transition = _transition(shot)
        if frame['zoom'] > 1 or transition != 'cut' or frame['x_end'] is not None or frame['y_end'] is not None:
            requested += 1
            same = abs(clip['zoom'] - frame['zoom']) < 0.01 and clip['transition'] == transition
            same = same and (frame['x_end'] is None or abs((clip.get('x_end') or clip['x']) - frame['x_end']) < 0.01)
            if same:
                applied += 1
    effects = 100.0 if requested == 0 else round(100 * applied / requested, 1)
    gap_ids = {gap['id'] for gap in gaps}
    has_card = any(c.get('card') for c in clips)
    has_emphasis = any(c.get('emphasis_en') or c.get('emphasis_zh') for c in edit['captions'])
    if ('kinetic_type' in gap_ids or 'number_card' in gap_ids) and not has_card:
        graphics = 55.0 if has_emphasis or any(c.get('text') for c in clips) else 40.0 if edit['subtitles'] else 15.0
    elif has_card or has_emphasis:
        graphics = 80.0
    else:
        graphics = 100.0
    graded = any(c.get('grade') for c in clips)
    enhanced = any(c.get('enhance') for c in clips)
    color = 72.0 if graded else 35.0 if 'color_grade' in gap_ids and enhanced else 0.0 if 'color_grade' in gap_ids else 75.0 if enhanced else 100.0
    covered = abs(sum(c['end'] - c['start'] for c in clips) - float(duration)) < 0.05
    production = 80.0 if covered else 70.0 if clips else 40.0
    scores = {
        'shot_structure': structure,
        'visual_pacing': pacing,
        'effect_similarity': effects,
        'motion_graphic_style': graphics,
        'color_treatment': color,
        'production_quality': production,
    }
    scores['overall'] = round(sum(scores[key] for key in SCORE_KEYS) / len(SCORE_KEYS), 1)
    return scores

def _applied(edit, trimmed):
    rows = ['cuts']
    if trimmed:
        rows.append('trimmed')
    if any(c['zoom'] > 1 or c.get('zoom_end') or c['x'] != 0.5 or c['y'] != 0.5 or c.get('x_end') or c.get('y_end') for c in edit['clips']):
        rows.append('framing')
    if any(c['zoom'] > 1 or c.get('zoom_end') for c in edit['clips']):
        rows.append('zoom')
    if any(c['transition'] != 'cut' for c in edit['clips']):
        rows.append('transitions')
    if any(c.get('text') for c in edit['clips']):
        rows.append('callouts')
    if any(c.get('card') for c in edit['clips']):
        rows.append('cards')
    if any(c.get('cutaway') or c.get('external_broll') for c in edit['clips']):
        rows.append('cutaway')
    if any(c.get('emphasis_en') or c.get('emphasis_zh') for c in edit['captions']):
        rows.append('emphasis')
    rows.append('captions' if edit['subtitles'] else 'no_captions')
    if edit['normalize']:
        rows.append('normalize')
    if any(c.get('enhance') for c in edit['clips']):
        rows.append('enhance')
    if any(c.get('grade') for c in edit['clips']):
        rows.append('grade')
    if any(abs((c.get('speed') or 1) - 1) > 0.04 for c in edit['clips']):
        rows.append('speed')
    if any(c.get('blur') for c in edit['clips']):
        rows.append('blur')
    if any(c.get('glow') for c in edit['clips']):
        rows.append('glow')
    if any(c.get('shadow') for c in edit['clips']):
        rows.append('shadow')
    if any(c.get('split') for c in edit['clips']):
        rows.append('split')
    if any(c.get('stabilize') for c in edit['clips']):
        rows.append('stabilize')
    if any(c.get('cutout') for c in edit['clips']):
        rows.append('cutout')
    if any(c.get('kinetic') for c in edit['clips']):
        rows.append('kinetic')
    if any(c.get('track') for c in edit['clips']):
        rows.append('track')
    if any(c.get('mask') for c in edit['clips']):
        rows.append('mask')
    if any(abs(c.get('exposure') or 0) > 0.02 for c in edit['clips']):
        rows.append('exposure')
    if any((c.get('progress') or 0) > 0.02 for c in edit['clips']):
        rows.append('progress')
    if any(c.get('graphic') for c in edit['clips']):
        rows.append('illustration')
    if any(c.get('lower') for c in edit['clips']):
        rows.append('lower')
    if any(c.get('icon') for c in edit['clips']):
        rows.append('icon')
    if any(c.get('still') is not None for c in edit['clips']):
        rows.append('still')
    if any(c.get('screen') is not None for c in edit['clips']):
        rows.append('screen')
    if any(c.get('diagram') for c in edit['clips']):
        rows.append('diagram')
    if any(c.get('art') for c in edit['clips']):
        rows.append('art')
    if any(c.get('panel') is not None for c in edit['clips']):
        rows.append('panel')
    return rows

def _report(shots, edit, duration, trimmed):
    gaps = _gaps(shots, edit)
    return {
        'scores': _scores(shots, edit, gaps, duration),
        'applied': _applied(edit, trimmed),
        'gaps': gaps,
        'sections': [{'index': i, 'start': c['start'], 'end': c['end'], 'transition': c['transition'], 'zoom': c['zoom']} for i, c in enumerate(edit['clips'])],
        'note': 'owned_only',
    }

def _scaled(shots, duration):
    merged = [dict(shot) for shot in shots]
    while len(merged) > 24:
        lengths = [max(0.28, float(shot['end']) - float(shot['start'])) for shot in merged]
        index = min(range(len(lengths) - 1), key=lambda n: lengths[n] + lengths[n + 1])
        merged[index] = {**merged[index], 'end': merged[index + 1]['end']}
        del merged[index + 1]
    lengths = [max(0.28, float(shot['end']) - float(shot['start'])) for shot in merged]
    total = sum(lengths) or 1
    cursor = 0.0
    cuts = []
    for length in lengths:
        end = min(float(duration), cursor + float(duration) * length / total)
        if end - cursor >= 0.28:
            cuts.append((round(cursor, 3), round(end, 3)))
        cursor = end
    if cuts:
        cuts[-1] = (cuts[-1][0], round(float(duration), 3))
    return merged, cuts or [(0.0, round(float(duration), 3))]

def _look(measured):
    measured = measured or {}
    layout = measured.get('layout') or {}
    return {'flat': measured.get('flat') or measured.get('chroma'), 'grade': measured.get('grade'), 'track': measured.get('track'), 'chroma': measured.get('chroma'), 'exposure': measured.get('exposure') or 0, 'split': layout.get('split'), 'bar': layout.get('bar'), 'lower': layout.get('lower'), 'shake': layout.get('shake')}

def build(shots, duration, transcript, has_audio, script='', recommendations=None, measured=None):
    measured = measured or {}
    timed = list(shots)
    if measured.get('shots'):
        timed = [{**(shots[i % len(shots)] if shots else {}), **span, 'start': span['start'], 'end': span['end']} for i, span in enumerate(measured['shots'])]
    extra = list(recommendations or [])
    for span in measured.get('silences') or []:
        if float(span['end']) - float(span['start']) >= 1:
            extra.append({'action': 'remove', 'start': span['start'], 'end': span['end']})
    for span in measured.get('unusable') or []:
        if float(span['end']) - float(span['start']) >= 0.4:
            extra.append({'action': 'remove', 'start': span['start'], 'end': span['end']})
    if measured.get('highlight') and not any(item.get('action') == 'move_to_front' for item in extra):
        extra.append({'action': 'move_to_front', **measured['highlight']})
    removes = _safe_removes(extra, transcript, duration)
    if measured.get('shots'):
        for span in timed:
            span['ref_len'] = max(0.28, float(span['end']) - float(span['start']))
        timed, cuts = _scaled(timed, duration)
        cuts = _structure(cuts, removes, extra, float(duration))
    else:
        count = beat_count(timed, duration)
        cuts = _structure(ranges(duration, count, transcript), removes, extra, float(duration))
    facts = _facts(script, transcript)
    look = _look(measured)
    graphic = next((i for i, (start, end) in enumerate(cuts) if end - start >= 1.2 and _has(_blob([timed[i % len(timed)] if timed else {}]), ('chart', 'number', 'statistic', 'progress'))), None)
    clips = [_clip(timed[i % len(timed)] if timed else {}, start, end, transcript, f'style_{i}', float(duration), facts, allow_card=(i == graphic), look=look, ref_len=(timed[i % len(timed)].get('ref_len') if timed else None), progress=((i + 1) / len(cuts) if look.get('bar') else 0)) for i, (start, end) in enumerate(cuts)]
    emphasize = _wants_captions(timed or shots)
    captions = _captions(transcript, emphasize)
    subtitles = bool(captions) and emphasize
    emphasized = any(c.emphasis_en or c.emphasis_zh for c in captions) if subtitles else False
    edit = Edit(clips=clips, captions=captions if subtitles else [], subtitles=subtitles, normalize=bool(has_audio), font_size='large' if emphasized else 'medium', color='yellow' if emphasized else 'white')
    check(edit, float(duration))
    dumped = edit.model_dump()
    trimmed = abs(sum(c['end'] - c['start'] for c in dumped['clips']) - float(duration)) >= 0.5
    return dumped, _report(timed or shots, dumped, duration, trimmed)

def _context(db, pid):
    from .studio import state
    current = state(pid, db)
    return current, json.loads(json.dumps(current['context']))

def _store(db, pid, edit, report, status, render):
    current, context = _context(db, pid)
    context['style_match'] = True
    context['style_report'] = report
    context['style_match_status'] = status
    db.execute('INSERT INTO studio_manual(project_id,config) VALUES(?,?) ON CONFLICT(project_id) DO UPDATE SET config=excluded.config', (pid, json.dumps(edit)))
    db.execute('UPDATE studio_projects SET context=?,revision=revision+1 WHERE project_id=?', (json.dumps(context, ensure_ascii=False), pid))
    if not render:
        return
    current, _context_again = _context(db, pid)
    enqueue(db, pid, 'studio_render', {'revision': current['revision'], 'plan': current['plan'], 'decisions': [], 'manual': edit, 'quality_review': False})
    db.execute("UPDATE projects SET status='queued',stage='render_queued',progress=0,error=NULL WHERE id=?", (pid,))

def match_project(pid):
    from .studio import state
    current = state(pid)
    if not current['context'].get('style_match'):
        return
    item = project(pid)
    shots = shots_of(current.get('dna'))
    transcript = (current.get('plan') or {}).get('transcript') or []
    edit, report = build(shots, item['metadata']['duration'], transcript, item['metadata'].get('has_audio'), script=item.get('brief') or '', recommendations=(current.get('plan') or {}).get('recommendations') or [], measured=current['context'].get('measured') or {})
    try:
        from .style_stock import attach
        edit, report = attach(pid, edit, shots, item.get('brief') or '', report, item['metadata']['duration'])
    except Exception:
        pass
    with connect() as db:
        db.lock()
        _store(db, pid, edit, report, 'pending', True)

def record_failure(pid):
    report = {'scores': {key: 0 for key in (*SCORE_KEYS, 'overall')}, 'applied': [], 'gaps': [{'id': 'style_match_failed', 'essential': True}], 'sections': [], 'note': 'owned_only'}
    with connect() as db:
        db.lock()
        current, context = _context(db, pid)
        if not current['context'].get('style_match'):
            return
        context['style_report'] = report
        context['style_match_status'] = 'failed'
        db.execute('UPDATE studio_projects SET context=? WHERE project_id=?', (json.dumps(context, ensure_ascii=False), pid))

def _owned_state(pid, user):
    from .studio import owned, state
    item = owned(pid, user)
    with connect() as db:
        db.lock()
        if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')", (pid,)).fetchone():
            raise HTTPException(409, 'job_already_running')
        current = state(pid, db)
        if not current['context'].get('style_match') or not current.get('plan'):
            raise HTTPException(422, 'style_match_off')
        return item, current

def _restyle(edit, shots, transcript, index, duration, facts, look=None):
    if index < 0 or index >= len(edit['clips']):
        raise HTTPException(422, 'invalid_clip_range')
    clip = edit['clips'][index]
    if clip.get('locked'):
        raise HTTPException(409, 'locked_decision')
    shot = shots[index % len(shots)] if shots else {}
    allow = _has(_blob([shot]), ('chart', 'number', 'statistic', 'progress'))
    replacement = _clip(shot, clip['start'], clip['end'], transcript, clip['id'], duration, facts, allow, look=look, progress=clip.get('progress') or 0).model_dump()
    edit['clips'][index] = replacement
    return edit

def attach_measurement(pid):
    from . import media
    from .config import settings
    from .studio import state
    from .style_vision import black_spans, chroma_plate, color_sample, flat_background, grade_between, highlight_window, measure, reference_layout, visual_track
    folder = settings.data_dir / pid
    item = project(pid)
    current = state(pid)
    source = folder / 'source'
    def quiet(fn, default):
        try:
            return fn()
        except Exception:
            return default
    vision = quiet(lambda: measure(folder / 'reference_source'), None) if (folder / 'reference_source').exists() else None
    owned = quiet(lambda: color_sample(source), None)
    grade = grade_between(vision.get('color') if vision else None, owned)
    exposure = 0
    if vision and vision.get('color') and owned:
        exposure = max(-0.5, min(0.5, round((vision['color']['y'] - owned['y']) / 100, 3)))
        if abs(exposure) < 0.05:
            exposure = 0
    silences = media.silence_ranges(source, item['metadata']['duration']) if item['metadata'].get('has_audio') else []
    payload = {
        'shots': vision['shots'] if vision else [],
        'flat': quiet(lambda: flat_background(source), False),
        'chroma': quiet(lambda: chroma_plate(source), None),
        'grade': grade,
        'exposure': exposure,
        'silences': silences,
        'unusable': quiet(lambda: black_spans(source), []),
        'track': quiet(lambda: visual_track(source), None),
        'highlight': quiet(lambda: highlight_window(source, item['metadata']['duration']), None),
        'layout': quiet(lambda: reference_layout(folder / 'reference_source'), {}) if (folder / 'reference_source').exists() else {},
    }
    dna = list(current.get('dna') or [])
    if vision and not any(row.get('reference_id') == 'upload' for row in dna):
        dna.append({'reference_id': 'upload', 'duration': vision['duration'], 'analysis': {'summary': {'en': 'Measured from the uploaded reference.', 'zh': '根据上传的参考视频测量。'}, 'shots': vision['shots']}})
    with connect() as db:
        db.lock()
        _current, context = _context(db, pid)
        context['measured'] = payload
        db.execute('UPDATE studio_projects SET dna=?,context=? WHERE project_id=?', (json.dumps(dna, ensure_ascii=False), json.dumps(context, ensure_ascii=False), pid))

def score_output(pid):
    from .config import settings
    from .style_vision import color_sample
    item = project(pid)
    render_id = (item.get('result') or {}).get('render_id')
    folder = settings.data_dir / pid
    output = folder / 'renders' / str(render_id or '') / 'result.mp4'
    reference = folder / 'reference_source'
    if not output.exists() or not reference.exists():
        return
    left, right = color_sample(reference), color_sample(output)
    if not left or not right:
        return
    distance = abs(left['y'] - right['y']) + 0.5 * abs(left['u'] - right['u']) + 0.5 * abs(left['v'] - right['v'])
    color = round(max(0, min(100, 100 - distance)), 1)
    with connect() as db:
        db.lock()
        _current, context = _context(db, pid)
        report = context.get('style_report')
        if not report:
            return
        report['scores']['color_treatment'] = color
        report['scores']['overall'] = round(sum(report['scores'][key] for key in SCORE_KEYS) / len(SCORE_KEYS), 1)
        report['measured_color_distance'] = round(distance, 2)
        context['style_report'] = report
        db.execute('UPDATE studio_projects SET context=? WHERE project_id=?', (json.dumps(context, ensure_ascii=False), pid))

@router.post('/projects/{pid}/style-match/approve')
def approve(pid: str, user=Depends(current_user)):
    from .studio import owned, state
    owned(pid, user)
    with connect() as db:
        db.lock()
        current = state(pid, db)
        if not current['context'].get('style_match') or not current['context'].get('style_report'):
            raise HTTPException(422, 'style_match_off')
        context = json.loads(json.dumps(current['context']))
        context['style_match_status'] = 'approved'
        db.execute('UPDATE studio_projects SET context=? WHERE project_id=?', (json.dumps(context, ensure_ascii=False), pid))
    return {'ok': True, 'style_match_status': 'approved'}

@router.post('/projects/{pid}/style-match/regenerate')
def regenerate(pid: str, user=Depends(current_user)):
    item, current = _owned_state(pid, user)
    from .manual import read
    with connect() as db:
        saved = read(pid, db)
    if saved and any(c.get('locked') for c in saved['clips']):
        raise HTTPException(409, 'locked_decision')
    shots = shots_of(current.get('dna'))
    transcript = current['plan'].get('transcript') or []
    edit, report = build(shots, item['metadata']['duration'], transcript, item['metadata'].get('has_audio'), script=item.get('brief') or '', recommendations=current['plan'].get('recommendations') or [], measured=current['context'].get('measured') or {})
    try:
        from .style_stock import attach
        edit, report = attach(pid, edit, shots, item.get('brief') or '', report, item['metadata']['duration'])
    except Exception:
        pass
    with connect() as db:
        db.lock()
        if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')", (pid,)).fetchone():
            raise HTTPException(409, 'job_already_running')
        _store(db, pid, edit, report, 'pending', True)
    return {'ok': True}

@router.post('/projects/{pid}/style-match/sections/{index}/regenerate')
def regenerate_section(pid: str, index: int, user=Depends(current_user)):
    item, current = _owned_state(pid, user)
    from .manual import read
    with connect() as db:
        saved = read(pid, db)
    if not saved:
        raise HTTPException(422, 'style_match_off')
    shots = shots_of(current.get('dna'))
    transcript = current['plan'].get('transcript') or []
    measured = current['context'].get('measured') or {}
    edit = _restyle(saved, shots, transcript, index, item['metadata']['duration'], _facts(item.get('brief') or '', transcript), look=_look(measured))
    checked = Edit.model_validate(edit)
    check(checked, item['metadata']['duration'])
    dumped = checked.model_dump()
    trimmed = abs(sum(c['end'] - c['start'] for c in dumped['clips']) - float(item['metadata']['duration'])) >= 0.5
    report = _report(shots, dumped, item['metadata']['duration'], trimmed)
    try:
        from .style_stock import attach
        dumped, report = attach(pid, dumped, shots, item.get('brief') or '', report, item['metadata']['duration'], only=index)
    except Exception:
        pass
    with connect() as db:
        db.lock()
        if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')", (pid,)).fetchone():
            raise HTTPException(409, 'job_already_running')
        _store(db, pid, dumped, report, 'pending', True)
    return {'ok': True}
