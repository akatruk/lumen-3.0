"""Optional visual-style match. Builds a normal manual edit from reference DNA and renders it with the existing pipeline.

Reference files, dialogue, music and packaging never become export inputs. Effects the renderer cannot reproduce are listed on the fidelity report.
"""
import copy
import json
import re
from fastapi import APIRouter, Depends, HTTPException
from .auth import current_user
from .db import connect, enqueue, project
from .manual import Clip, Edit, check
from .schemas import Caption

router = APIRouter(prefix='/api/studio')
SCORE_KEYS = ('shot_structure', 'visual_pacing', 'effect_similarity', 'motion_graphic_style', 'color_treatment', 'production_quality')
FRAMES_NOT_COMPARED = 'Frames have not been compared yet.'
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
    from .transitions import KINDS
    blob = plain(shot.get('transition')).lower()
    name = 'cut'
    # The transition sentence only. Motion copy that says "zoom" is not a join.
    for needle, kind in (('circle', 'circle'), ('wipe', 'wipe'), ('crossfade', 'crossfade'), ('dissolve', 'crossfade'), ('fade', 'fade'), ('zoom', 'zoom')):
        if _has(blob, (needle,)):
            name = kind
            break
    picture = shot.get('picture') if isinstance(shot.get('picture'), dict) else {}
    measured = str(picture.get('join') or '').lower()
    if name == 'cut' and measured == 'zoom' and 'zoom' in KINDS:
        name = 'zoom'
    elif name == 'cut' and measured in ('wipe-right', 'wiperight', 'wipe') and 'wipe' in KINDS:
        # A right arrival is wipe-right in the picture. wipeleft is what actually reveals that side.
        name = 'wipe'
    if name == 'cut' and (picture.get('graphic') or picture.get('fade')):
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
        y = float(picture['y']) if picture.get('y') is not None else (0.45 if zoom > 1.05 else 0.5)
        y_end = picture.get('y_end')
        return {'zoom': zoom, 'zoom_end': zoom_end, 'x': x, 'y': y, 'x_end': x_end, 'y_end': y_end}
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

def _merged_spans(spans):
    rows = []
    for span in spans or []:
        try:
            start, end = float(span['start']), float(span['end'])
        except (KeyError, TypeError, ValueError):
            continue
        if end - start < 0.4:
            continue
        if rows and start <= rows[-1][1] + 0.05:
            rows[-1][1] = max(rows[-1][1], end)
        else:
            rows.append([start, end])
    return [{'start': round(start, 3), 'end': round(end, 3)} for start, end in rows]

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

def _highlight_fractions(shot):
    picture = shot.get('picture') if isinstance(shot.get('picture'), dict) else {}
    raw = picture.get('highlights')
    if not isinstance(raw, (list, tuple)):
        return []
    found = []
    for item in raw:
        try:
            frac = float(item)
        except (TypeError, ValueError):
            continue
        if 0 <= frac <= 1:
            found.append(frac)
    return found

def _kinetic_fractions(picture):
    raw = picture.get('kinetic_at') if isinstance(picture, dict) else None
    if not isinstance(raw, (list, tuple)):
        return []
    found = []
    for item in raw:
        try:
            frac = float(item)
        except (TypeError, ValueError):
            continue
        if frac == frac and 0 <= frac <= 1:
            found.append(round(frac, 2))
        if len(found) >= 8:
            break
    return found

def _caption_at(captions, moment):
    for cap in captions:
        if cap.start - 1e-3 <= moment < cap.end + 1e-3:
            return cap
    return None

def _owned_terms(text):
    if not text:
        return []
    return [word for word in _keywords(text) if word in text][:3]

def _highlight_spans(shot, start, end):
    """Map a measured highlight onto the owned clip. A stored start gets an exit so it does not cover the shot."""
    picture = shot.get('picture') if isinstance(shot.get('picture'), dict) else {}
    length = max(0.0, end - start)
    emphasis = picture.get('emphasis') if isinstance(picture, dict) else None
    if isinstance(emphasis, dict) and emphasis.get('in') is not None:
        try:
            inn = float(emphasis.get('in'))
            out = min(1.0, float(emphasis['out'])) if emphasis.get('out') is not None else min(1.0, inn + 0.15)
        except (TypeError, ValueError):
            inn = out = None
        else:
            if out <= inn:
                out = min(1.0, inn + 0.15)
            if 0 <= inn < out:
                return [(start + inn * length, start + out * length)]
    spans = []
    for frac in _highlight_fractions(shot):
        spans.append((start + frac * length, start + min(1.0, frac + 0.15) * length))
    return spans

def _emphasize_owned_hits(captions, shots, cuts):
    """Emphasize an owned keyword already in the caption that overlaps the measured window. Speech times stay put."""
    saw = False
    for index, (start, end) in enumerate(cuts):
        shot = shots[index % len(shots)] if shots else {}
        spans = _highlight_spans(shot, start, end)
        if not spans:
            continue
        saw = True
        for cap in captions:
            if not any(cap.end > left + 1e-3 and cap.start < right - 1e-3 for left, right in spans):
                continue
            en = _owned_terms(cap.en or cap.original)
            zh = _owned_terms(cap.zh)
            if en and not cap.emphasis_en:
                cap.emphasis_en = en
            if zh and not cap.emphasis_zh:
                cap.emphasis_zh = zh
    return saw

def _bars(facts):
    peak = max((item[2] for item in facts), default=0) or 1
    return [round(max(0.08, min(1, item[2] / peak)), 3) for item in facts[:5]]

def _owned_fill(facts):
    """A progress fraction only when the owned figure is a percent."""
    for _label, figure, value in facts:
        if '%' not in figure and 'percent' not in figure.lower():
            continue
        ratio = value / 100 if value > 1 else value
        return round(max(0, min(1, ratio)), 3)
    return None

def _bar_window(look):
    """Map a measured reference bar onto the owned clip. Untimed bars span the clip."""
    if not look or not look.get('bar') or look.get('bar_in') is None or look.get('bar_out') is None:
        return 0.0, 1.0
    start = round(max(0.0, min(1.0, float(look.get('bar_in') or 0))), 2)
    end = round(max(0.0, min(1.0, float(look.get('bar_out')))), 2)
    if end < start + 0.04:
        end = min(1.0, round(start + 0.04, 2))
    return start, end

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
            label, figure, _value = facts[0]
            return VisualCard(kind='bar_chart', start=0.15, end=round(span, 3), title=CardText(en=label, zh=label), primary=CardText(en=figure, zh=figure), source=source, items=items, animation=animation, animation_seconds=0.6)
        label, figure, _value = facts[0]
        return VisualCard(kind='number', start=0.15, end=round(span, 3), title=CardText(en=label, zh=label), primary=CardText(en=figure, zh=figure), source=source)
    except Exception:
        return None

def _moment(picture):
    """Owned-clip fraction for a measured number card. Raw reference timestamps are not used."""
    moment = picture.get('card') if isinstance(picture, dict) else None
    if not isinstance(moment, dict):
        return None
    try:
        opened = float(moment.get('in'))
    except (TypeError, ValueError):
        return None
    if moment.get('out') is None:
        closed = min(1.0, round(opened + 0.35, 3))
    else:
        try:
            closed = float(moment.get('out'))
        except (TypeError, ValueError):
            return None
    if not 0 <= opened < closed <= 1:
        return None
    return {'in': opened, 'out': closed}

def _time_card(card, length, moment):
    start = max(0.0, min(length, moment['in'] * length))
    end = max(start, min(length, moment['out'] * length))
    if end - start < 0.5:
        end = min(length, start + 0.5)
        if end - start < 0.5:
            start = max(0.0, end - 0.5)
    start, end = round(start, 3), round(min(length, end), 3)
    if end <= start or end - start < 0.5 or end > length + 1e-9:
        return
    card.start = start
    card.end = end
    if card.animation == 'grow' and card.animation_seconds > card.end - card.start - 0.15:
        card.animation = 'none'

def _panel_start(start, end, duration):
    window = min(1.2, max(0.5, (end - start) * 0.45))
    if duration - end >= window:
        return round(end, 3)
    if start >= window:
        return 0.0
    return None

def _ref_span(shots):
    ends = []
    for shot in shots or []:
        if not isinstance(shot, dict):
            continue
        try:
            ends.append(float(shot.get('end') or 0))
        except (TypeError, ValueError):
            continue
    return max(ends) if ends else 0.0

def _fraction_of(value, ref_duration):
    """A measured insert start. Numbers in 0..1 are fractions of the reference."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if 0 <= number <= 1:
            return number
        if ref_duration and 0 <= number <= float(ref_duration) + 1e-6:
            return max(0.0, min(1.0, number / float(ref_duration)))
        return None
    if not isinstance(value, dict):
        return None
    if value.get('fraction') is not None:
        return _fraction_of(value.get('fraction'), ref_duration)
    if value.get('in') is not None:
        return _fraction_of(value.get('in'), ref_duration)
    if value.get('start') is None and value.get('at') is None:
        return None
    try:
        start = float(value.get('start', value.get('at')))
        end = float(value['end']) if value.get('end') is not None else None
    except (TypeError, ValueError):
        return None
    if end is not None and end > 1 and ref_duration:
        return max(0.0, min(1.0, start / float(ref_duration)))
    if 0 <= start <= 1:
        return start
    if ref_duration and 0 <= start <= float(ref_duration) + 1e-6:
        return max(0.0, min(1.0, start / float(ref_duration)))
    return None

def _measured_insert(shot, ref_duration):
    """Cutaway, graphic cover, or b-roll window already measured on the reference."""
    if not isinstance(shot, dict):
        return None
    picture = shot.get('picture') if isinstance(shot.get('picture'), dict) else {}
    for source in (picture, shot):
        for key in ('insert', 'cover', 'cutaway', 'broll'):
            if key not in source:
                continue
            frac = _fraction_of(source.get(key), ref_duration)
            if frac is not None:
                return frac
        graphic = source.get('graphic')
        if isinstance(graphic, dict):
            frac = _fraction_of(graphic, ref_duration)
            if frac is not None:
                return frac
    return None

def _insert_fraction(shot, ref_duration):
    """Where the reference covers the presenter, as a fraction of the reference."""
    measured = _measured_insert(shot, ref_duration)
    if measured is not None:
        return measured
    if not isinstance(shot, dict):
        return None
    blob = (plain(shot.get('visual_type')) + ' ' + plain(shot.get('reusable_method')) + ' ' + plain(shot.get('narrative_role'))).lower()
    if not _has(blob, ('b-roll', 'broll', 'cutaway', 'stock footage')):
        return None
    try:
        start = float(shot.get('start') or 0)
    except (TypeError, ValueError):
        start = 0.0
    length = float(ref_duration or 0)
    if length <= 0:
        return 0.0
    return max(0.0, min(1.0, start / length))

def _local_insert(fraction, start, end, duration):
    """Owned-clip start. Same fraction mapping as highlights and number cards."""
    try:
        fraction = float(fraction)
        start, end, duration = float(start), float(end), float(duration)
    except (TypeError, ValueError):
        return None
    span = end - start
    if span <= 0 or not 0 <= fraction <= 1:
        return None
    moment = start + span * fraction
    absolute = fraction * duration
    if start - 1e-6 <= absolute < end:
        moment = absolute
    local = moment - start
    if local < -1e-6 or local >= span:
        return None
    return max(0.0, local)

def _cutaway(shot, start, end, duration):
    from .manual import Cutaway
    blob = (plain(shot.get('visual_type')) + ' ' + plain(shot.get('reusable_method')) + ' ' + plain(shot.get('narrative_role'))).lower()
    fraction = _insert_fraction(shot, _ref_span([shot]))
    if not _has(blob, ('b-roll', 'broll', 'cutaway')) and not fraction:
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
    local = 0.12
    if fraction:
        mapped = _local_insert(fraction, start, end, duration)
        if mapped is None or mapped + window > length + 1e-9:
            return None
        local = mapped
    local_end = round(local + window, 3)
    if local_end > length or src + window > duration + 1e-6:
        return None
    return Cutaway(start=round(local, 3), end=local_end, source_start=src)

def _effects(shot, ref_len, flat, chroma=False, look_split=False, look_shake=False):
    blob = _blob([shot or {}])
    picture = shot.get('picture') or {}
    soft, bloom, shade = float(picture.get('blur') or 0), float(picture.get('glow') or 0), float(picture.get('shade') or 0)
    return {
        'blur': soft if soft >= 1 else 2.0 if _has(blob, ('blur', 'bokeh')) else 0,
        'glow': bloom >= 0.4 or _has(blob, ('glow', 'bloom')),
        'glow_amount': bloom if bloom >= 0.4 else 0.8 if _has(blob, ('glow', 'bloom')) else 0,
        'shadow': shade >= 0.4 or bool(picture.get('vignette')) or _has(blob, ('drop shadow', 'shadows', 'shadow')),
        'shade': shade if shade >= 0.4 else 0,
        'split': bool(look_split) or bool((shot.get('picture') or {}).get('split')),
        'stabilize': _has(blob, ('stabilize', 'stabilisation', 'shaky')) or bool(look_shake),
        'cutout': bool(flat or chroma) and _has(blob, ('cutout', 'cut out', 'green screen', 'background replace', 'replace the background')),
        'mask': bool((shot.get('picture') or {}).get('mask')),
        'speed': 1.35 if ref_len < 0.55 else 0.75 if _has(blob, ('slow motion', 'slow-mo')) else 1.0,
        'kinetic': _has(blob, ('kinetic', 'animated title', 'title card')),
    }

def _screen_fraction(picture):
    """Fraction of the reference where a screen was seen. Not a reference timestamp."""
    if not isinstance(picture, dict) or picture.get('fraction') is None:
        return None
    try:
        value = float(picture['fraction'])
    except (TypeError, ValueError):
        return None
    if value != value:
        return None
    return max(0.0, min(1.0, value))

def _owned_screen_time(fraction, start, end, duration):
    """Owned-source timestamp: fraction of the owned duration, inside this clip."""
    moment = max(0.0, min(float(duration), float(fraction) * float(duration)))
    low, high = float(start), float(end)
    if high < low:
        low, high = high, low
    if high > low:
        moment = min(max(moment, low), high)
    else:
        moment = low
    return round(moment, 3)

def _owned_frame_is_screen(source, at):
    """True when the owned frame at this source time has a bezel and an inner picture."""
    from pathlib import Path
    path = Path(source) if source else None
    if path is None or not path.is_file():
        return False
    try:
        from . import media
        from .style_vision import _screen
        meta = media.probe(path)
        return bool(_screen(path, float(at), int(meta['width']), int(meta['height'])))
    except Exception:
        return False

def _clip(shot, start, end, transcript, ident, duration, facts, allow_card, look=None, ref_len=None, progress=0, progress_play=False, script=''):
    look = look or {}
    frame = _frame(shot or {})
    track = look.get('track') if _has(_blob([shot or {}]), ('tracking', 'track the', 'follow the subject')) else None
    if track:
        frame['x'], frame['x_end'] = track['x0'], track['x1']
    moving = frame['zoom_end'] is not None or frame['x_end'] is not None or frame['y_end'] is not None
    spoken = _spoken(start, end, transcript)
    words = _keywords(spoken)
    blob = _blob([shot or {}])
    picture = shot.get('picture') or {}
    callout = bool(words) and (_wants_captions([shot or {}]) or _has(blob, ('title', 'overlay', 'callout', 'keyword', 'kinetic', 'icon')) or look.get('lower') or look.get('bar') or picture.get('lower'))
    moment = _moment(picture)
    card = _card(facts, end - start) if (allow_card and _has(blob, ('chart', 'number', 'statistic', 'progress'))) or picture.get('graphic') or moment else None
    fx = _effects(shot, end - start if ref_len is None else ref_len, look.get('flat'), chroma=bool(look.get('chroma')), look_split=bool(look.get('split')), look_shake=bool(look.get('shake')))
    slot = end - start if ref_len is None else ref_len
    opening, closing = picture.get('speed'), picture.get('speed_end')
    if slot >= 0.55 and opening is not None and closing is not None and abs(float(opening) - float(closing)) > 0.08:
        speed, speed_end = max(0.5, min(2, float(opening))), max(0.5, min(2, float(closing)))
    else:
        speed, speed_end = fx['speed'], None
    open_shot = not fx['split'] and not fx['cutout'] and not (picture.get('graphic') and facts)
    wants_screen = open_shot and (bool(picture.get('screen')) or _has(blob, ('screenshot', 'screen recording', 'screen capture')))
    fraction = _screen_fraction(picture) if wants_screen else None
    if wants_screen and fraction is None:
        fraction = 0.5
    screen = _owned_screen_time(fraction, start, end, duration) if fraction is not None else None
    tiles = int(picture.get('tiles') or 0)
    diagram = (tiles if 1 <= tiles <= 4 else max(1, min(4, len(words) or 3))) if open_shot and screen is None and _has(blob, ('illustration', 'diagram', 'infographic', 'drawing')) else 0
    text = (words[0][:40] if callout else '')
    if diagram and words and not text:
        text = words[0][:40]
    motion = picture.get('title') if isinstance(picture.get('title'), dict) else None
    title_in = title_out = title_x = title_y = title_x_end = title_y_end = None
    if motion and words:
        lead = words[0][:40]
        text = f'{lead} {words[1]}'[:80] if len(words) >= 2 and words[1] not in lead.split() else lead
        title_in = max(0, min(1, float(motion.get('in') or 0)))
        title_out = max(title_in, min(1, float(motion.get('out') or 1)))
        title_x = max(0, min(1, float(motion.get('x0') or 0.2)))
        title_y = max(0, min(1, float(motion.get('y0') or 0.2)))
        title_x_end = max(0, min(1, float(motion.get('x1') if motion.get('x1') is not None else title_x)))
        title_y_end = max(0, min(1, float(motion.get('y1') if motion.get('y1') is not None else title_y)))
    elif fx['kinetic'] and len(words) >= 2:
        lead = text or words[0][:40]
        if words[1] not in lead.split():
            text = f'{lead} {words[1]}'[:80]
    if title_in is not None and shot.get('text_at') is not None:
        title_in = max(0.0, min(1.0, _clip_fraction(shot['text_at'], duration, start, end)))
        if title_out is not None:
            title_out = max(title_in, title_out)
    owned = list(words)
    for word in _keywords(script or ''):
        if len(owned) >= 3:
            break
        if word not in owned:
            owned.append(word)
    hits = _kinetic_fractions(picture) if owned else []
    if motion and len(hits) < 2:
        hits = []
    if hits and not motion:
        text = ' '.join(word[:40] for word in owned)[:160]
    elif hits and not text:
        text = ' '.join(word[:40] for word in owned)[:160]
    if text and _has(blob, ('icon', 'chart', 'progress')):
        mark = '▮ ' if _has(blob, ('chart', 'progress')) else '● '
        text = (mark + text)[:160]
    grade = None
    if look.get('grade'):
        from .manual import Grade
        grade = Grade.model_validate(look['grade'])
    raw_exposure = look.get('exposure')
    # A missing measurement is not a light shift, and a measured 0 stays 0. Never invent 0.18.
    exposure = 0.0 if raw_exposure is None else float(raw_exposure)
    icon = bool((look.get('lower') or picture.get('lower')) and not picture.get('graphic') and not fx['split'] and not fx['cutout'] and not fx['mask'] and screen is None and not diagram)
    try:
        chip_at = float(picture.get('callout') or 0)
    except (TypeError, ValueError):
        chip_at = 0.0
    chip_room = title_x is None and not picture.get('graphic') and not fx['split'] and not fx['cutout'] and not fx['mask'] and screen is None and not diagram
    placed = 0.2 <= chip_at <= 0.85 and bool(owned) and chip_room
    if placed:
        icon = True
        if not text:
            text = owned[0][:40]
        if not text.startswith(('● ', '▮ ')):
            text = ('● ' + text)[:160]
    elif chip_at >= 0.2 and not owned:
        icon = False
        text = ''
    radius = int(look.get('shake_rx') or 0)
    shake_rx = max(4, min(64, radius)) if fx['stabilize'] and radius else 16 if fx['stabilize'] else 0
    effect_at = float(picture.get('hold') or 0)
    if placed and effect_at < 0.2:
        effect_at = min(0.85, chip_at)
    mapped = _local_insert(shot.get('event_at'), start, end, duration) if shot.get('event_at') is not None and (fx['blur'] or fx['glow'] or fx['shadow']) else None
    if mapped is not None and end > start:
        effect_at = min(0.85, mapped / (end - start))
    elif effect_at < 0.2 or not (fx['blur'] or fx['glow'] or fx['shadow'] or icon):
        effect_at = 0
    effect_end = 1.0
    exit_frac = picture.get('callout_out')
    if exit_frac is None:
        exit_frac = picture.get('release')
    try:
        exit_frac = 1.0 if exit_frac is None else float(exit_frac)
    except (TypeError, ValueError):
        exit_frac = 1.0
    if (placed or icon) and effect_at < exit_frac < 0.999:
        effect_end = round(min(1.0, exit_frac), 2)
    if card is not None and shot.get('card_at') is not None:
        local_in = _clip_fraction(shot['card_at'], duration, start, end)
        if shot.get('card_to') is None:
            local_out = min(1.0, local_in + 0.35)
        else:
            local_out = _clip_fraction(shot['card_to'], duration, start, end)
        _time_card(card, end - start, {'in': local_in, 'out': max(local_in + 0.001, local_out)})
    elif card is not None and moment:
        _time_card(card, end - start, moment)
    elif card is not None and shot.get('event_at') is not None:
        offset = _local_insert(shot['event_at'], start, end, duration)
        if offset is not None:
            window = max(0.2, float(card.end) - float(card.start))
            length = end - start
            begin = min(max(0.0, offset), max(0.0, length - window))
            card.start = round(begin, 3)
            card.end = round(min(length, begin + window), 3)
    elif card is not None and effect_at >= 0.2:
        slot = end - start
        if effect_end < 0.999:
            _time_card(card, slot, {'in': effect_at, 'out': effect_end})
        else:
            card.start = round(min(max(float(card.start), effect_at * slot), max(float(card.start), slot - 0.45)), 3)
    cutaway = None if card or fx['cutout'] or fx['split'] else _cutaway(shot or {}, start, end, duration)
    # A measured insert already has its fraction. Do not slide it to the effect hold.
    insert_at = _measured_insert(shot or {}, _ref_span([shot or {}]))
    if cutaway is not None and insert_at is None and shot.get('event_at') is not None:
        offset = _local_insert(shot['event_at'], start, end, duration)
        if offset is not None:
            window = cutaway.end - cutaway.start
            begin = round(min(offset, max(0.12, (end - start) - window)), 3)
            if begin >= 0.2 and begin + window <= (end - start) + 1e-6:
                cutaway = cutaway.model_copy(update={'start': begin, 'end': round(begin + window, 3)})
    elif cutaway is not None and effect_at >= 0.2 and insert_at is None:
        window = cutaway.end - cutaway.start
        begin = round(min(effect_at * (end - start), max(0.12, (end - start) - window)), 3)
        if begin >= 0.2 and begin + window <= (end - start) + 1e-6:
            cutaway = cutaway.model_copy(update={'start': begin, 'end': round(begin + window, 3)})
    progress_at, progress_end = _bar_window(look)
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
        cutaway=cutaway,
        effect_at=round(effect_at, 2),
        effect_end=round(effect_end, 2),
        card=card,
        enhance=False,
        speed=speed,
        speed_end=speed_end,
        blur=fx['blur'],
        glow=fx['glow'],
        glow_amount=fx['glow_amount'],
        shadow=fx['shadow'],
        shade=fx['shade'],
        split=fx['split'],
        stabilize=fx['stabilize'],
        shake_rx=shake_rx,
        cutout=fx['cutout'],
        kinetic=bool(text) and (title_x is not None or fx['kinetic'] or bool(hits)),
        title_in=0 if title_in is None else title_in,
        title_out=1 if title_out is None else title_out,
        title_x=title_x,
        title_y=title_y,
        title_x_end=title_x_end,
        title_y_end=title_y_end,
        kinetic_at=hits,
        mask=bool(fx['mask'] and not fx['cutout'] and not fx['split']),
        track=bool(track),
        exposure=exposure,
        progress=max(0, min(1, float(progress or 0))),
        progress_at=progress_at,
        progress_end=progress_end,
        progress_play=bool(progress_play),
        plate='1A1F1C' if fx['cutout'] else '',
        graphic=bool(picture.get('graphic') and facts and not fx['split'] and not fx['cutout']),
        bars=_bars(facts) if picture.get('graphic') and facts and not fx['split'] and not fx['cutout'] else [],
        lower=icon,
        icon=icon,
        mark=(_owned_fill(facts) or 0) if icon else 0,
        panel=_panel_start(start, end, duration) if fx['split'] and not fx['cutout'] else None,
        still=(_panel_start(start, end, duration) if _panel_start(start, end, duration) is not None else start) if picture.get('graphic') and not facts and not fx['split'] and not fx['cutout'] and screen is None and not diagram else None,
        screen=screen,
        bezel=float(picture.get('bezel') or 0.1) if screen is not None and 0.06 <= float(picture.get('bezel') or 0) <= 0.28 else 0.1,
        diagram=diagram,
        grade=grade,
        approved=True,
        locked=False,
    )

def _gaps(shots, edit, source=None):
    blob = _blob(shots)
    found = [{'id': ident, 'essential': essential} for ident, needles, essential in GAP_RULES if _has(blob, needles)]
    if _wants_captions(shots) and not edit['subtitles']:
        found.append({'id': 'captions_need_speech', 'essential': True})
    if any(plain(shot.get('music')).strip() for shot in shots):
        found.append({'id': 'reference_music', 'essential': False})
    if any(c.get('card') for c in edit['clips']):
        found = [g for g in found if g['id'] != 'number_card']
    elif any(_moment(shot.get('picture') or {}) for shot in shots) and not any(g['id'] == 'number_card' for g in found):
        found.append({'id': 'number_card', 'essential': True})
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
    if any(abs((c.get('speed') or 1) - 1) > 0.04 or (c.get('speed_end') is not None and abs(c['speed_end'] - (c.get('speed') or 1)) > 0.04) for c in clips): done.add('speed_ramp')
    if any(c.get('kinetic') for c in clips): done.add('kinetic_type')
    if any(isinstance((shot.get('picture') or {}).get('title'), dict) for shot in shots) and not any(c.get('kinetic') and c.get('text') for c in clips):
        found.append({'id': 'owned_title', 'essential': True})
    if any(c.get('track') for c in clips): done.add('motion_tracking')
    if any(c.get('mask') for c in clips): done.add('mask')
    for index, shot in enumerate(shots or []):
        picture = shot.get('picture') if isinstance(shot.get('picture'), dict) else {}
        join = str(picture.get('join') or '')
        applied = clips[index].get('transition') if index < len(clips) else 'cut'
        if join == 'zoom' and applied != 'zoom':
            found.append({'id': 'zoom_transition', 'essential': False})
        if join in ('wipe-right', 'wiperight') and applied not in ('wipe', 'wipe-right'):
            found.append({'id': 'wipe_right', 'essential': False})
    screens = [c.get('screen') for c in clips if c.get('screen') is not None]
    if screens and not all(_owned_frame_is_screen(source, stamp) for stamp in screens):
        found.append({'id': 'owned_screen_frame', 'essential': False, 'note': 'owned frame, not a reference screenshot'})
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
            same = same and abs(clip['y'] - frame['y']) < 0.01
            same = same and (frame['x_end'] is None or abs((clip.get('x_end') or clip['x']) - frame['x_end']) < 0.01)
            same = same and (frame['y_end'] is None or abs((clip.get('y_end') or clip['y']) - frame['y_end']) < 0.01)
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
    if any(abs((c.get('speed') or 1) - 1) > 0.04 or (c.get('speed_end') is not None and abs(c['speed_end'] - (c.get('speed') or 1)) > 0.04) for c in edit['clips']):
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

def _report(shots, edit, duration, trimmed, source=None):
    gaps = _gaps(shots, edit, source)
    scores = _scores(shots, edit, gaps, duration)
    return {
        'scores': scores,
        'applied': _applied(edit, trimmed),
        'gaps': gaps,
        'sections': [{'index': i, 'start': c['start'], 'end': c['end'], 'transition': c['transition'], 'zoom': c['zoom']} for i, c in enumerate(edit['clips'])],
        'note': 'owned_only',
        'compared': False,
        'effect_similarity_rule': scores['effect_similarity'],
        'comparison_note': FRAMES_NOT_COMPARED,
    }

def _unit_fraction(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return max(0.0, min(1.0, number))

def _shot_fraction(shot, inner):
    """Where `inner` sits in the whole reference, using this shot's pre-scale window."""
    shot_in = float(shot.get('shot_in') or 0)
    shot_out = float(shot['shot_out']) if shot.get('shot_out') is not None else shot_in
    return max(0.0, min(1.0, shot_in + float(inner) * (shot_out - shot_in)))

def _event_fraction(shot):
    picture = shot.get('picture') if isinstance(shot.get('picture'), dict) else {}
    if isinstance(picture, dict) and picture.get('event') is not None:
        parsed = _unit_fraction(picture.get('event'))
        if parsed is not None:
            return parsed
    if shot.get('event') is not None:
        parsed = _unit_fraction(shot.get('event'))
        if parsed is not None:
            return parsed
    if not isinstance(picture, dict) or shot.get('shot_in') is None:
        return None
    hold = _unit_fraction(picture.get('hold') or 0)
    if hold is None or hold < 0.2:
        return None
    return _shot_fraction(shot, hold)

def _mark_reference_windows(shots, measured):
    """Record each shot's share of the reference before lengths are scaled onto the owned video."""
    ref = 0.0
    try:
        ref = float((measured or {}).get('duration') or 0)
    except (TypeError, ValueError):
        ref = 0.0
    if ref <= 0:
        ends = []
        for shot in shots:
            try:
                ends.append(float(shot['end']))
            except (KeyError, TypeError, ValueError):
                continue
        ref = max(ends) if ends else 1.0
    ref = ref or 1.0
    for shot in shots:
        try:
            start, end = float(shot['start']), float(shot['end'])
        except (KeyError, TypeError, ValueError):
            continue
        shot['shot_in'] = round(max(0.0, min(1.0, start / ref)), 4)
        shot['shot_out'] = round(max(shot['shot_in'], min(1.0, end / ref)), 4)
        event = _event_fraction(shot)
        if event is not None:
            shot['event_at'] = event
        picture = shot.get('picture') if isinstance(shot.get('picture'), dict) else {}
        motion = picture.get('title') if isinstance(picture, dict) and isinstance(picture.get('title'), dict) else None
        if motion and motion.get('in') is not None:
            inner = _unit_fraction(motion.get('in'))
            if inner is not None:
                shot['text_at'] = _shot_fraction(shot, inner)
        moment = _moment(picture) if isinstance(picture, dict) else None
        if moment:
            shot['card_at'] = _shot_fraction(shot, moment['in'])
            shot['card_to'] = _shot_fraction(shot, moment['out'])

def _clip_fraction(fraction, duration, start, end):
    """Same fraction of the owned duration, as a fraction of the clip that contains it."""
    at = _owned_screen_time(fraction, start, end, duration)
    span = float(end) - float(start)
    if span <= 1e-9:
        return 0.0
    return max(0.0, min(1.0, (float(at) - float(start)) / span))

def _scaled(shots, duration):
    merged = [dict(shot) for shot in shots]
    while len(merged) > 24:
        lengths = [max(0.28, float(shot['end']) - float(shot['start'])) for shot in merged]
        index = min(range(len(lengths) - 1), key=lambda n: lengths[n] + lengths[n + 1])
        nxt = merged[index + 1]
        kept = {**merged[index], 'end': nxt['end']}
        if nxt.get('shot_out') is not None:
            kept['shot_out'] = nxt['shot_out']
        merged[index] = kept
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
    return {'flat': measured.get('flat') or measured.get('chroma'), 'grade': measured.get('grade'), 'track': measured.get('track'), 'chroma': measured.get('chroma'), 'exposure': measured.get('exposure') or 0, 'split': layout.get('split'), 'bar': layout.get('bar'), 'bar_in': layout.get('bar_in'), 'bar_out': layout.get('bar_out'), 'lower': layout.get('lower'), 'shake': layout.get('shake'), 'shake_rx': int(layout.get('shake_rx') or 0)}

def build(shots, duration, transcript, has_audio, script='', recommendations=None, measured=None, source=None):
    measured = measured or {}
    timed = list(shots)
    if measured.get('shots'):
        timed = [{**(shots[i % len(shots)] if shots else {}), **span, 'start': span['start'], 'end': span['end']} for i, span in enumerate(measured['shots'])]
    extra = list(recommendations or [])
    for span in measured.get('silences') or []:
        if float(span['end']) - float(span['start']) >= 1:
            extra.append({'action': 'remove', 'start': span['start'], 'end': span['end']})
    for span in _merged_spans(measured.get('unusable')):
        extra.append({'action': 'remove', 'start': span['start'], 'end': span['end']})
    if measured.get('highlight') and not any(item.get('action') == 'move_to_front' for item in extra):
        extra.append({'action': 'move_to_front', **measured['highlight']})
    removes = _safe_removes(extra, transcript, duration)
    if measured.get('shots'):
        _mark_reference_windows(timed, measured)
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
    owned_bar = _owned_fill(facts) if look.get('bar') else None
    playhead = bool(look.get('bar')) and owned_bar is None
    clips = [_clip(timed[i % len(timed)] if timed else {}, start, end, transcript, f'style_{i}', float(duration), facts, allow_card=(i == graphic), look=look, ref_len=(timed[i % len(timed)].get('ref_len') if timed else None), progress=(owned_bar if owned_bar is not None else ((i + 1) / len(cuts) if look.get('bar') else 0)), progress_play=playhead, script=script) for i, (start, end) in enumerate(cuts)]
    emphasize = _wants_captions(timed or shots)
    captions = _captions(transcript, emphasize)
    saw_highlight = _emphasize_owned_hits(captions, timed, cuts)
    subtitles = bool(captions) and (emphasize or saw_highlight)
    emphasized = any(c.emphasis_en or c.emphasis_zh for c in captions) if subtitles else False
    edit = Edit(clips=clips, captions=captions if subtitles else [], subtitles=subtitles, normalize=bool(has_audio), font_size='large' if emphasized else 'medium', color='yellow' if emphasized else 'white')
    check(edit, float(duration))
    dumped = edit.model_dump()
    trimmed = abs(sum(c['end'] - c['start'] for c in dumped['clips']) - float(duration)) >= 0.5
    return dumped, _report(timed or shots, dumped, duration, trimmed, source)

def _context(db, pid):
    from .studio import state
    current = state(pid, db)
    return current, json.loads(json.dumps(current['context']))

def _carry_selected_music(db, pid, edit):
    """Keep a selected music bed on the next picture without changing the saved edit."""
    shaped = json.loads(json.dumps(edit))
    if shaped.get('music'):
        return shaped
    result = (project(pid) or {}).get('result') or {}
    render_id = result.get('render_id') or ''
    if not render_id:
        return shaped
    from .final_music import config_of
    from .final_output import current
    selected = current(db, pid, render_id)
    music = config_of(selected, result) if selected else None
    if not music:
        return shaped
    try:
        from .music import Music
        shaped['music'] = Music.model_validate(music).model_dump()
    except Exception:
        return json.loads(json.dumps(edit))
    return shaped

def _selected_voice_id(db, pid):
    result = (project(pid) or {}).get('result') or {}
    render_id = result.get('render_id') or ''
    if not render_id:
        return ''
    from .final_music import voice_of
    from .final_output import current
    selected = current(db, pid, render_id)
    return voice_of(selected) if selected else ''

def _style_render_payload(db, pid, current, edit):
    payload = {'revision': current['revision'], 'plan': current['plan'], 'decisions': [], 'manual': _carry_selected_music(db, pid, edit), 'quality_review': False}
    voice_id = _selected_voice_id(db, pid)
    if voice_id:
        payload['voice_id'] = voice_id
    return payload

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
    enqueue(db, pid, 'studio_render', _style_render_payload(db, pid, current, edit))
    db.execute("UPDATE projects SET status='queued',stage='render_queued',progress=0,error=NULL WHERE id=?", (pid,))

def _limit(value, low, high, digits=2):
    return round(max(low, min(high, float(value))), digits)

def apply_effect_board(edit, board):
    """User look from the visual-effect plaque. Missing switches stay as the style match built them."""
    if not isinstance(board, dict) or not isinstance(board.get('effects'), dict):
        return edit
    effects = board['effects']
    try:
        amount = max(0.4, min(1.6, float(board.get('amount') or 1)))
    except (TypeError, ValueError):
        amount = 1.0
    shaped = copy.deepcopy(edit)
    for clip in shaped.get('clips') or []:
        if not isinstance(clip, dict):
            continue
        blur = effects.get('blur')
        if blur is False:
            clip['blur'] = 0
        elif blur is True:
            clip['blur'] = _limit((clip.get('blur') or 2) * amount, 0, 12)
        glow = effects.get('glow')
        if glow is False:
            clip['glow'] = False
            clip['glow_amount'] = 0
        elif glow is True:
            clip['glow'] = True
            clip['glow_amount'] = _limit((clip.get('glow_amount') or 0.55) * amount, 0, 1.5)
        shadow = effects.get('shadow')
        if shadow is False:
            clip['shadow'] = False
            clip['shade'] = 0
        elif shadow is True:
            clip['shadow'] = True
            clip['shade'] = _limit((clip.get('shade') or 0.55) * amount, 0, 1.35, 3)
        color = effects.get('color')
        if color is False:
            clip['enhance'] = False
            clip['exposure'] = 0
            clip['grade'] = None
        elif color is True:
            clip['enhance'] = True
            clip['exposure'] = _limit((clip.get('exposure') or 0.18) * amount, -1, 1)
            grade = clip.get('grade')
            if isinstance(grade, dict):
                grade['brightness'] = _limit((grade.get('brightness') or 0) * amount, -0.2, 0.2)
                grade['contrast'] = _limit((grade.get('contrast') or 1) * amount, 0.8, 1.4)
                grade['saturation'] = _limit((grade.get('saturation') or 1) * amount, 0.5, 1.8)
                grade['gamma'] = _limit((grade.get('gamma') or 1) * amount, 0.7, 1.4)
                for key in ('rs', 'gs', 'bs'):
                    grade[key] = _limit((grade.get(key) or 0) * amount, -0.3, 0.3)
        speed = effects.get('speed')
        if speed is False:
            clip['speed'] = 1
            clip['speed_end'] = None
        elif speed is True:
            base = clip.get('speed') if clip.get('speed') not in (None, 1) else 1.15
            clip['speed'] = _limit(base * amount, 0.5, 2)
            if clip.get('speed_end') not in (None, 1):
                clip['speed_end'] = _limit(clip['speed_end'] * amount, 0.5, 2)
        if effects.get('stabilize') is False:
            clip['stabilize'] = False
        elif effects.get('stabilize') is True:
            clip['stabilize'] = True
        kinetic = effects.get('kinetic')
        if kinetic is False:
            clip['kinetic'] = False
        elif kinetic is True and str(clip.get('text') or '').strip():
            clip['kinetic'] = True
        if effects.get('progress') is False:
            clip['progress'] = 0
        elif effects.get('progress') is True and not clip.get('progress'):
            clip['progress'] = 0.7
        if effects.get('split') is False:
            clip['split'] = False
            clip['panel'] = None
        elif effects.get('split') is True:
            clip['split'] = True
        if effects.get('screen') is False:
            clip['screen'] = None
        elif effects.get('screen') is True and clip.get('screen') is None:
            clip['screen'] = _limit(clip.get('start') or 0, 0, 10_000)
    return shaped

def _with_board(edit, context):
    board = (context or {}).get('effect_board')
    if not isinstance(board, dict):
        return edit
    try:
        return Edit.model_validate(apply_effect_board(edit, board)).model_dump()
    except Exception:
        return edit

def match_project(pid):
    from .studio import state
    current = state(pid)
    if not current['context'].get('style_match'):
        return
    item = project(pid)
    from .config import settings
    owned_source = settings.data_dir / pid / 'source'
    shots = shots_of(current.get('dna'))
    transcript = (current.get('plan') or {}).get('transcript') or []
    edit, report = build(shots, item['metadata']['duration'], transcript, item['metadata'].get('has_audio'), script=item.get('brief') or '', recommendations=(current.get('plan') or {}).get('recommendations') or [], measured=current['context'].get('measured') or {}, source=owned_source if owned_source.is_file() else None)
    try:
        from .style_stock import attach
        edit, report = attach(pid, edit, shots, item.get('brief') or '', report, item['metadata']['duration'])
    except Exception:
        pass
    edit = _with_board(edit, current['context'])
    with connect() as db:
        db.lock()
        _store(db, pid, edit, report, 'pending', True)

def record_failure(pid):
    report = {'scores': {key: 0 for key in (*SCORE_KEYS, 'overall')}, 'applied': [], 'gaps': [{'id': 'style_match_failed', 'essential': True}], 'sections': [], 'note': 'owned_only', 'compared': False, 'effect_similarity_rule': 0, 'comparison_note': FRAMES_NOT_COMPARED}
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
    playhead = bool((look or {}).get('bar')) and _owned_fill(facts) is None
    replacement = _clip(shot, clip['start'], clip['end'], transcript, clip['id'], duration, facts, allow, look=look, progress=clip.get('progress') or 0, progress_play=playhead).model_dump()
    edit['clips'][index] = replacement
    return edit

def reference_video(folder, context=None):
    """Uploaded reference, otherwise the downloaded reference file. Never a render input."""
    direct = folder / 'reference_source'
    if direct.is_file():
        return direct
    root = folder / 'references'
    if not root.is_dir():
        return None
    wanted = []
    for item in (context or {}).get('references') or []:
        if isinstance(item, str):
            wanted.append(item)
        elif isinstance(item, dict):
            wanted.extend(str(item[key]) for key in ('id', 'aweme_id', 'reference_id') if item.get(key))
    for ident in wanted:
        path = root / ident / 'source'
        if path.is_file():
            return path
    found = sorted(path for path in root.glob('*/source') if path.is_file())
    return found[0] if found else None

def attach_measurement(pid):
    from . import media
    from .config import settings
    from .studio import state
    from .style_vision import chroma_plate, color_sample, flat_background, grade_between, highlight_window, light_between, measure, reference_layout, unusable_spans, visual_track
    folder = settings.data_dir / pid
    item = project(pid)
    current = state(pid)
    source = folder / 'source'
    def quiet(fn, default):
        try:
            return fn()
        except Exception:
            return default
    reference = reference_video(folder, current.get('context'))
    vision = quiet(lambda: measure(reference), None) if reference else None
    owned = quiet(lambda: color_sample(source), None)
    sampled = vision.get('color') if vision else None
    grade = grade_between(sampled, owned)
    exposure = light_between(sampled, owned)
    silences = media.silence_ranges(source, item['metadata']['duration']) if item['metadata'].get('has_audio') else []
    payload = {
        'shots': vision['shots'] if vision else [],
        'flat': quiet(lambda: flat_background(source), False),
        'chroma': quiet(lambda: chroma_plate(source), None),
        'grade': grade,
        'exposure': exposure,
        'silences': silences,
        'unusable': quiet(lambda: unusable_spans(source), []),
        'track': quiet(lambda: visual_track(source), None),
        'highlight': quiet(lambda: highlight_window(source, item['metadata']['duration']), None),
        'layout': quiet(lambda: reference_layout(reference), {}) if reference else {},
    }
    dna = list(current.get('dna') or [])
    if vision and not any(row.get('reference_id') == 'upload' for row in dna):
        dna.append({'reference_id': 'upload', 'duration': vision['duration'], 'analysis': {'summary': {'en': 'Measured from the uploaded reference.', 'zh': '根据上传的参考视频测量。'}, 'shots': vision['shots']}})
    with connect() as db:
        db.lock()
        _current, context = _context(db, pid)
        context['measured'] = payload
        db.execute('UPDATE studio_projects SET dna=?,context=? WHERE project_id=?', (json.dumps(dna, ensure_ascii=False), json.dumps(context, ensure_ascii=False), pid))

def blend_effect_similarity(report, frame_similarity):
    """Average the rule with a measured frame. No measurement leaves the rule uncompared."""
    scores = report.setdefault('scores', {})
    rule = report.get('effect_similarity_rule')
    if rule is None:
        rule = scores.get('effect_similarity', 0)
    rule = float(rule)
    report['effect_similarity_rule'] = rule
    if frame_similarity is None:
        report['compared'] = False
        report['comparison_note'] = FRAMES_NOT_COMPARED
        scores['effect_similarity'] = rule
        report.pop('measured_effect_similarity', None)
        return report
    scores['effect_similarity'] = round((rule + float(frame_similarity)) / 2, 1)
    report['measured_effect_similarity'] = frame_similarity
    report['compared'] = True
    report['comparison_note'] = ''
    return report

def score_output(pid):
    from .config import settings
    from .studio import state
    from .style_vision import color_sample, frame_similarity
    item = project(pid)
    render_id = (item.get('result') or {}).get('render_id')
    folder = settings.data_dir / pid
    output = folder / 'renders' / str(render_id or '') / 'result.mp4'
    current = state(pid) or {}
    reference = reference_video(folder, current.get('context'))
    if not output.exists() or not reference:
        return
    left, right = color_sample(reference), color_sample(output)
    try:
        measured = frame_similarity(reference, output)
    except Exception:
        measured = None
    if (not left or not right) and measured is None:
        return
    with connect() as db:
        db.lock()
        _current, context = _context(db, pid)
        report = context.get('style_report')
        if not report:
            return
        if left and right:
            distance = abs(left['y'] - right['y']) + 0.5 * abs(left['u'] - right['u']) + 0.5 * abs(left['v'] - right['v'])
            report['scores']['color_treatment'] = round(max(0, min(100, 100 - distance)), 1)
            report['measured_color_distance'] = round(distance, 2)
        blend_effect_similarity(report, measured)
        report['scores']['overall'] = round(sum(report['scores'][key] for key in SCORE_KEYS) / len(SCORE_KEYS), 1)
        context['style_report'] = report
        db.execute('UPDATE studio_projects SET context=? WHERE project_id=?', (json.dumps(context, ensure_ascii=False), pid))

@router.post('/projects/{pid}/style-match/approve')
def approve(pid: str, user=Depends(current_user)):
    from .studio import owned, state
    from .manual import Edit, check, read
    item = owned(pid, user)
    with connect() as db:
        db.lock()
        if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')", (pid,)).fetchone():
            raise HTTPException(409, 'job_already_running')
        current = state(pid, db)
        if not current['context'].get('style_match') or not current['context'].get('style_report'):
            raise HTTPException(422, 'style_match_off')
        edit = read(pid, db)
        if not edit:
            raise HTTPException(422, 'save_manual_first')
        payload = _style_render_payload(db, pid, current, edit)
        checked = Edit.model_validate(payload['manual'])
        check(checked, item['metadata']['duration'])
        if not any(c.approved for c in checked.clips):
            raise HTTPException(422, 'no_approved_changes')
        if any(not c.approved for c in checked.clips):
            raise HTTPException(422, 'approve_shots_first')
        from .assets import validate as validate_assets
        validate_assets(checked, pid, db)
        from .render_audio import summary as audio_summary
        audio = audio_summary(db, project(pid), [(c.start, c.end) for c in checked.clips])
        if audio and audio.get('error'):
            raise HTTPException(422, audio['error'])
        context = json.loads(json.dumps(current['context']))
        context['style_match_status'] = 'approved'
        db.execute('UPDATE studio_projects SET context=? WHERE project_id=?', (json.dumps(context, ensure_ascii=False), pid))
        enqueue(db, pid, 'studio_render', payload)
        db.execute("UPDATE projects SET status='queued',stage='render_queued',progress=0,error=NULL WHERE id=?", (pid,))
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
    edit = _with_board(edit, current['context'])
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
    edit = _with_board(_restyle(saved, shots, transcript, index, item['metadata']['duration'], _facts(item.get('brief') or '', transcript), look=_look(measured)), current['context'])
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
