"""Optional visual-style match. Builds a normal manual edit from reference DNA and renders it with the existing pipeline.

Reference dialogue and reference music never become export inputs. A measured non-presenter picture may be copied from the reference file. Effects the renderer cannot reproduce are listed on the fidelity report.
"""
import copy
import json
import re
from fastapi import APIRouter, Depends, HTTPException
from .auth import current_user
from .db import connect, enqueue, project
from .manual import Clip, Edit, PictureInsert, check
from .schemas import Caption

router = APIRouter(prefix='/api/studio')
SCORE_KEYS = ('shot_structure', 'visual_pacing', 'effect_similarity', 'motion_graphic_style', 'color_treatment', 'production_quality')
FRAMES_NOT_COMPARED = 'Frames have not been compared yet.'
FRAME_RULES = (
    ('shot_structure', 'shot_structure_rule', 'measured_shot_structure', 'shot structure'),
    ('visual_pacing', 'visual_pacing_rule', 'measured_visual_pacing', 'pacing'),
    ('motion_graphic_style', 'motion_graphic_style_rule', 'measured_motion_graphic_style', 'graphic style'),
    ('production_quality', 'production_quality_rule', 'measured_production_quality', 'production quality'),
)
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
    ('key_light', ('key light', 'keylight'), False),
    ('fill_light', ('fill light',), False),
    ('rim_light', ('rim light', 'hair light', 'backlight'), False),
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

def _transition(shot):
    """A join comes from a measured picture. A transition sentence does not set one."""
    from .transitions import KINDS
    picture = shot.get('picture') if isinstance(shot.get('picture'), dict) else {}
    measured = str(picture.get('join') or '').lower()
    # wipeleft reveals the new picture from the right. wipeup reveals it from the bottom.
    # wipedown reveals it from the top.
    mapped = {
        'zoom': 'zoom',
        'wipe': 'wipe',
        'wipe-right': 'wipe',
        'wiperight': 'wipe',
        'wipe-up': 'wipe-up',
        'wipeup': 'wipe-up',
        'wipe-down': 'wipe-down',
        'wipedown': 'wipe-down',
        'diagtl': 'diagtl',
        'diagtr': 'diagtr',
        'diagbl': 'diagbl',
        'diagbr': 'diagbr',
        'fade': 'fade',
        'crossfade': 'crossfade',
        'circle': 'circle',
    }
    kind = mapped.get(measured)
    if kind in KINDS or kind == 'fade':
        return kind
    if picture.get('graphic') or picture.get('fade'):
        return 'fade'
    return 'cut'

def _join_seconds(picture, kind):
    """A measured blend longer than the default 800 ms window. Words do not set it."""
    if kind == 'cut' or not isinstance(picture, dict):
        return None
    try:
        span = float(picture.get('join_seconds'))
    except (TypeError, ValueError):
        return None
    if span != span or span <= 0.8:
        return None
    return round(min(2.4, span), 2)

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
    """Camera position comes from a measured picture. Motion words do not reframe."""
    picture = shot.get('picture') if isinstance(shot.get('picture'), dict) else None
    if not picture:
        return {'zoom': 1.0, 'zoom_end': None, 'x': 0.5, 'y': 0.5, 'x_end': None, 'y_end': None}
    zoom = float(picture.get('zoom') or 1)
    return {
        'zoom': zoom,
        'zoom_end': picture.get('zoom_end'),
        'x': float(picture.get('x') if picture.get('x') is not None else 0.5),
        'y': float(picture['y']) if picture.get('y') is not None else 0.5,
        'x_end': picture.get('x_end'),
        'y_end': picture.get('y_end'),
    }

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
    """A bright pop stays a measured time mark. It does not write keyword emphasis or callout text."""
    return False

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
    """Map a measured reference bar onto the owned clip. A missing exit stays to the end."""
    if not look or not look.get('bar'):
        return 0.0, 1.0
    try:
        start = float(look.get('bar_in') if look.get('bar_in') is not None else 0)
    except (TypeError, ValueError):
        start = 0.0
    raw_out = look.get('bar_out')
    if raw_out is None:
        end = 1.0
    else:
        try:
            end = float(raw_out)
        except (TypeError, ValueError):
            end = 1.0
    start = round(max(0.0, min(0.98, start)), 2)
    end = round(max(0.0, min(1.0, end)), 2)
    if end <= start:
        end = 1.0
    return start, end

def _card(facts, length):
    from .visuals import CardText, DataItem, VisualCard
    span = float(length)
    if span < 0.7 or not facts:
        return None
    source = CardText(en='From your script', zh='来自你的脚本')
    try:
        if len(facts) >= 2:
            items = [DataItem(label=CardText(en=label, zh=label), value=value) for label, _figure, value in facts]
            animation = 'grow' if 0.6 <= span - 0.3 else 'none'
            label, figure, _value = facts[0]
            return VisualCard(kind='bar_chart', start=0.0, end=span, title=CardText(en=label, zh=label), primary=CardText(en=figure, zh=figure), source=source, items=items, animation=animation, animation_seconds=0.6)
        label, figure, _value = facts[0]
        return VisualCard(kind='number', start=0.0, end=span, title=CardText(en=label, zh=label), primary=CardText(en=figure, zh=figure), source=source)
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
        closed = 1.0
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

def _presenter_box(raw):
    """A measured head-and-shoulders box. A full frame, or a sentence with no box, is not one."""
    if not isinstance(raw, dict):
        return None
    try:
        x, y, width, height = (float(raw[key]) for key in ('x', 'y', 'w', 'h'))
    except (KeyError, TypeError, ValueError):
        return None
    if any(value != value for value in (x, y, width, height)):
        return None
    if not (0.18 <= width <= 0.7 and 0.22 <= height <= 0.8):
        return None
    if width * height > 0.42:
        return None
    if not (0.28 <= x <= 0.72 and 0.18 <= y <= 0.7):
        return None
    if x - width / 2 < 0.08 or x + width / 2 > 0.92:
        return None
    return {'x': round(x, 3), 'y': round(y, 3), 'w': round(width, 3), 'h': round(height, 3)}

def _effects(shot, ref_len, flat, chroma=False, look_split=False, look_shake=False, room=None):
    """Blur, glow, shadow and pace come from the measured picture. Words do not turn them on."""
    blob = _blob([shot or {}])
    picture = shot.get('picture') or {}
    soft, bloom, shade = float(picture.get('blur') or 0), float(picture.get('glow') or 0), float(picture.get('shade') or 0)
    wants_key = _has(blob, ('cutout', 'cut out', 'green screen'))
    keyed = bool(flat or chroma) and wants_key
    box = None if chroma or keyed else _presenter_box(room)
    room_cut = box is not None
    return {
        'blur': soft if soft >= 1 else 0,
        'glow': bloom >= 0.4,
        'glow_amount': bloom if bloom >= 0.4 else 0,
        'shadow': shade >= 0.4 or bool(picture.get('vignette')),
        'shade': shade if shade >= 0.4 else 0,
        'split': bool(look_split) or bool((shot.get('picture') or {}).get('split')),
        'stabilize': bool(look_shake),
        'cutout': keyed or room_cut,
        'subject': box if room_cut else None,
        'mask': bool((shot.get('picture') or {}).get('mask')),
        'speed': 1.35 if ref_len < 0.55 else 1.0,
        'kinetic': isinstance(picture.get('title'), dict) or bool(_kinetic_fractions(picture)),
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

def _owned_screen_candidates(path, duration, width, height):
    """Owned timestamps whose border and inner picture look like a screen. Each one is checked again."""
    from .style_vision import _series
    bw, bh = max(8, width // 12), max(8, height // 12)
    inner_w, inner_h = width - 4 * bw, height - 4 * bh
    if inner_w < 16 or inner_h < 16:
        return []
    quarter = max(8, inner_w // 4)
    right_x = min(width - quarter, 2 * bw + inner_w - quarter)
    crops = (
        f'crop={width}:{bh}:0:0',
        f'crop={width}:{bh}:0:{height - bh}',
        f'crop={bw}:{height}:0:0',
        f'crop={bw}:{height}:{width - bw}:0',
        f'crop={quarter}:{inner_h}:{2 * bw}:{2 * bh}',
        f'crop={quarter}:{inner_h}:{right_x}:{2 * bh}',
    )
    try:
        rows = [_series(path, 0, float(duration), crop, fps=2, limit=48) for crop in crops]
    except Exception:
        return []
    count = min((len(row) for row in rows), default=0)
    found = []
    for index in range(count):
        borders = [rows[i][index] for i in range(4)]
        if max(borders) - min(borders) > 40:
            continue
        border = sum(borders) / 4
        left, right = rows[4][index], rows[5][index]
        if left - border < 22 or right - border < 22:
            continue
        found.append(min(float(duration), index / 2))
    return found

def _confirmed_screen(path, at, width, height, duration):
    """A timestamp that _screen accepts. A miss does not invent a bezel."""
    from .style_vision import _screen
    try:
        duration = float(duration)
    except (TypeError, ValueError):
        return None
    for nudge in (0.0, 0.2):
        stamp = float(at) + nudge
        if stamp < 0 or stamp > duration - 0.04:
            continue
        try:
            if _screen(path, stamp, int(width), int(height)):
                return round(stamp, 3)
        except Exception:
            return None
    return None

def _seek_owned_screen(source, preferred, duration, cache):
    """Keep the measured time when that owned frame is a screen. Otherwise a later owned screen, then an earlier one.
    None means no owned frame is a screen, so the measured time and its bezel stay."""
    from pathlib import Path
    path = Path(source) if source else None
    if path is None or not path.is_file():
        return None
    try:
        duration = float(duration)
        preferred = max(0.0, min(duration, float(preferred)))
    except (TypeError, ValueError):
        return None
    if 'size' not in cache:
        try:
            from . import media
            meta = media.probe(path)
            cache['size'] = (int(meta['width']), int(meta['height']))
        except Exception:
            cache['size'] = None
    size = cache.get('size')
    if not size or size[0] < 120 or size[1] < 120:
        return None
    width, height = size
    from .style_vision import _screen
    try:
        held = bool(_screen(path, preferred, width, height))
    except Exception:
        held = False
    if held:
        return round(preferred, 3)
    if 'candidates' not in cache:
        cache['candidates'] = _owned_screen_candidates(path, duration, width, height)
    later = [at for at in cache['candidates'] if at > preferred + 0.05]
    earlier = [at for at in cache['candidates'] if at < preferred - 0.05]
    for at in later:
        found = _confirmed_screen(path, at, width, height, duration)
        if found is not None:
            return found
    for at in reversed(earlier):
        found = _confirmed_screen(path, at, width, height, duration)
        if found is not None:
            return found
    return None

def _retarget_owned_screens(clips, source, duration):
    """Measured fraction when that owned frame has a bezel. Otherwise search the owned video.
    No owned screen leaves the measured time. The bezel is not invented, and reference pixels are not copied."""
    cache = {}
    for clip in clips or []:
        if clip.screen is None:
            continue
        found = _seek_owned_screen(source, clip.screen, duration, cache)
        if found is not None:
            clip.screen = found

def _measured_point(picture, key):
    """A measured frame center. Words and a missing axis do not invent the other coordinate."""
    raw = picture.get(key) if isinstance(picture, dict) else None
    if not isinstance(raw, dict):
        return None, None
    x, y = _unit_fraction(raw.get('x')), _unit_fraction(raw.get('y'))
    if x is None or y is None:
        return None, None
    return round(x, 2), round(y, 2)

def _measured_size(raw):
    """Width and height fractions. A missing axis, or words with no frame, leave the Lumen default."""
    if not isinstance(raw, dict):
        return None, None
    width, height = _unit_fraction(raw.get('w')), _unit_fraction(raw.get('h'))
    if width is None or height is None or width <= 0 or height <= 0:
        return None, None
    return round(width, 2), round(height, 2)

def _measured_groups(picture):
    """Separated bright groups, each with its own center. One averaged point is not a group list."""
    raw = picture.get('groups') if isinstance(picture, dict) else None
    if not isinstance(raw, list):
        return []
    found = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        x, y = _unit_fraction(item.get('x')), _unit_fraction(item.get('y'))
        if x is None or y is None:
            continue
        width, height = _measured_size(item)
        found.append({'x': round(x, 2), 'y': round(y, 2), 'w': width, 'h': height})
    return found

def _camera(picture, fx):
    """Roll, orbit, focus, mask radii, and the split ratio. Words do not set them."""
    picture = picture if isinstance(picture, dict) else {}

    def num(key, lo, hi):
        try:
            value = float(picture.get(key))
        except (TypeError, ValueError):
            return None
        if value != value:
            return None
        return max(lo, min(hi, value))

    roll = num('roll', -18, 18) or 0.0
    roll_end = num('roll_end', -18, 18)
    if abs(roll) < 4 and (roll_end is None or abs(roll_end) < 4):
        roll, roll_end = 0.0, None
    elif roll_end is not None and abs(roll_end - roll) < 4:
        roll_end = None
    orbit_x = num('orbit_x', -0.35, 0.35) or 0.0
    orbit_y = num('orbit_y', -0.35, 0.35) or 0.0
    if abs(orbit_x) < 0.08:
        orbit_x = 0.0
    if abs(orbit_y) < 0.08:
        orbit_y = 0.0
    focus = picture.get('focus') if picture.get('focus') in ('in', 'out') else None
    masked = bool(fx.get('mask') and not fx.get('cutout') and not fx.get('split'))
    mask_rx = num('mask_rx', 0.18, 0.48) if masked else None
    mask_ry = num('mask_ry', 0.18, 0.48) if masked else None
    split_at = num('split_at', 0.2, 0.8) if fx.get('split') else None
    return roll, roll_end, orbit_x, orbit_y, focus, mask_rx, mask_ry, split_at

def _centered_subject(picture):
    try:
        x = 0.5 if picture.get('x') is None else float(picture.get('x'))
        y = 0.5 if picture.get('y') is None else float(picture.get('y'))
    except (TypeError, ValueError):
        return True
    return abs(x - 0.5) <= 0.16 and abs(y - 0.5) <= 0.18

def _presenter_fill(picture):
    """A presenter-sized subject sits in the middle. A small or shifted mass does not."""
    if not isinstance(picture, dict) or not _centered_subject(picture):
        return False
    width, height = picture.get('mass_w'), picture.get('mass_h')
    if width is not None and height is not None:
        try:
            area = float(width) * float(height)
            tall = float(height) >= 0.5
        except (TypeError, ValueError):
            area, tall = None, False
        if area is not None:
            return tall or area >= 0.22
    try:
        zoom = float(picture.get('zoom') or 1)
    except (TypeError, ValueError):
        zoom = 1.0
    return zoom < 1.4

def _camera_move(picture):
    return any(picture.get(key) is not None for key in ('zoom_end', 'x_end', 'y_end'))

def _cover_fraction(picture, shot):
    """Insert or cover already measured on the picture. Words are not a cover."""
    ref = _ref_span([shot] if isinstance(shot, dict) else [])
    sources = [picture]
    if isinstance(shot, dict):
        sources.append(shot)
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in ('insert', 'cover'):
            if key not in source:
                continue
            frac = _fraction_of(source.get(key), ref)
            if frac is not None:
                return frac
    return None

def _reference_at(shot, fraction=None):
    try:
        start = max(0.0, float(shot.get('start') or 0))
        end = float(shot.get('end') if shot.get('end') is not None else start)
    except (TypeError, ValueError):
        return 0.0
    if fraction is None:
        return round(start, 3)
    span = max(0.0, end - start)
    return round(start + max(0.0, min(1.0, float(fraction))) * span, 3)

def _picture_insert(shot, start, end, duration):
    """Reference picture for a non-presenter span. A talking head and words alone copy nothing."""
    if not isinstance(shot, dict):
        return None
    picture = shot.get('picture') if isinstance(shot.get('picture'), dict) else None
    if not picture:
        return None
    try:
        length = float(end) - float(start)
    except (TypeError, ValueError):
        return None
    if length < 0.2:
        return None
    presenter = _presenter_fill(picture)
    moving = _camera_move(picture)
    screen = bool(picture.get('screen'))
    graphic = bool(picture.get('graphic'))
    try:
        zoom = float(picture.get('zoom') or 1)
    except (TypeError, ValueError):
        zoom = 1.0
    full_bleed = graphic and zoom <= 1.05 and _centered_subject(picture)
    cover = _cover_fraction(picture, shot)
    copy_span = screen or (graphic and not presenter) or full_bleed or (not presenter and not moving)
    if copy_span:
        return PictureInsert(start=0, end=round(length, 3), at=_reference_at(shot))
    if cover is None:
        return None
    local = _local_insert(cover, start, end, duration)
    if local is None:
        return None
    window = min(1.2, length * 0.45, max(0.0, length - local))
    if window < 0.2:
        return None
    return PictureInsert(start=round(local, 3), end=round(local + window, 3), at=_reference_at(shot, cover))

def _tile_count(picture, open_shot, screen):
    """Illustration tiles from a counted frame or illustration measured on the picture. Words add none."""
    if not open_shot or screen is not None:
        return 0
    picture = picture if isinstance(picture, dict) else {}
    if picture.get('graphic') or picture.get('mask') or picture.get('screen'):
        return 0
    try:
        tiles = int(picture.get('tiles') or 0)
    except (TypeError, ValueError):
        tiles = 0
    if tiles >= 2:
        return min(4, tiles)
    if picture.get('illustration'):
        return 2
    return 0

def _clip(shot, start, end, transcript, ident, duration, facts, allow_card, look=None, ref_len=None, progress=0, progress_play=False, script=''):
    look = look or {}
    frame = _frame(shot or {})
    picture_frame = shot.get('picture') if isinstance(shot.get('picture'), dict) else None
    column = look.get('track') if isinstance(look.get('track'), dict) else None
    tracked = (
        isinstance(column, dict)
        and column.get('face') is True
        and column.get('x0') is not None and column.get('x1') is not None
        and column.get('y0') is not None and column.get('y1') is not None
    )
    if tracked:
        # Reference zoom stays. The skin path is the owned camera even when picture exists.
        frame['x'] = max(0.0, min(1.0, float(column['x0'])))
        frame['x_end'] = max(0.0, min(1.0, float(column['x1'])))
        frame['y'] = max(0.0, min(1.0, float(column['y0'])))
        frame['y_end'] = max(0.0, min(1.0, float(column['y1'])))
    elif not picture_frame and isinstance(column, dict) and column.get('x0') is not None and column.get('x1') is not None:
        frame['x'], frame['x_end'] = float(column['x0']), float(column['x1'])
    moving = frame['zoom_end'] is not None or frame['x_end'] is not None or frame['y_end'] is not None
    spoken = _spoken(start, end, transcript)
    words = _keywords(spoken)
    blob = _blob([shot or {}])
    picture = shot.get('picture') or {}
    callout = bool(words) and (_wants_captions([shot or {}]) or _has(blob, ('callout', 'icon')) or look.get('lower') or look.get('bar') or picture.get('lower'))
    moment = _moment(picture)
    card = _card(facts, end - start) if (allow_card and _has(blob, ('chart', 'number', 'statistic', 'progress'))) or picture.get('graphic') or moment else None
    fx = _effects(shot, end - start if ref_len is None else ref_len, look.get('flat'), chroma=bool(look.get('chroma')), look_split=bool(look.get('split')), look_shake=bool(look.get('shake')), room=look.get('room'))
    slot = end - start if ref_len is None else ref_len
    opening, closing = picture.get('speed'), picture.get('speed_end')
    try:
        opening_f = float(opening) if opening is not None else None
        closing_f = float(closing) if closing is not None else None
    except (TypeError, ValueError):
        opening_f = closing_f = None
    if slot >= 0.55 and opening_f is not None and closing_f is not None and (abs(opening_f - closing_f) > 0.08 or abs(opening_f - 1) > 0.04):
        speed, speed_end = max(0.5, min(2, opening_f)), max(0.5, min(2, closing_f))
        if abs(speed - speed_end) <= 0.08:
            speed_end = None
    else:
        speed, speed_end = fx['speed'], None
    roll, roll_end, orbit_x, orbit_y, focus, mask_rx, mask_ry, split_at = _camera(picture, fx)
    open_shot = not fx['split'] and not fx['cutout'] and not (picture.get('graphic') and facts)
    wants_screen = open_shot and (bool(picture.get('screen')) or _has(blob, ('screenshot', 'screen recording', 'screen capture')))
    fraction = _screen_fraction(picture) if wants_screen else None
    if wants_screen and fraction is None:
        fraction = 0.5
    screen = _owned_screen_time(fraction, start, end, duration) if fraction is not None else None
    diagram = _tile_count(picture, open_shot, screen)
    text = (words[0][:40] if callout else '')
    if diagram and words and not text:
        text = words[0][:40]
    motion = picture.get('title') if isinstance(picture.get('title'), dict) else None
    title_in = title_out = title_x = title_y = title_x_end = title_y_end = None
    title_w = title_h = None
    if motion and words:
        lead = words[0][:40]
        text = f'{lead} {words[1]}'[:80] if len(words) >= 2 and words[1] not in lead.split() else lead
        title_in = max(0, min(1, float(motion.get('in') or 0)))
        title_out = max(title_in, min(1, float(motion.get('out') or 1)))
        title_x = max(0, min(1, float(motion.get('x0') or 0.2)))
        title_y = max(0, min(1, float(motion.get('y0') or 0.2)))
        title_x_end = max(0, min(1, float(motion.get('x1') if motion.get('x1') is not None else title_x)))
        title_y_end = max(0, min(1, float(motion.get('y1') if motion.get('y1') is not None else title_y)))
        title_w, title_h = _measured_size(motion)
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
    room = not picture.get('graphic') and not fx['split'] and not fx['cutout'] and not fx['mask'] and screen is None and not diagram
    try:
        chip_at = float(picture.get('callout') or 0)
    except (TypeError, ValueError):
        chip_at = 0.0
    # A measured plate or a measured chip owns the lower third. A title on the same frame does not remove it. Words do not.
    measured_plate = bool(look.get('lower') or picture.get('lower'))
    measured_chip = room and 0.2 <= chip_at <= 0.98
    lower_on = bool(room and measured_plate) or measured_chip
    icon = bool(lower_on and owned)
    placed = bool(measured_chip and owned)
    if placed and not text:
        text = owned[0][:40]
        if not text.startswith(('● ', '▮ ')):
            text = ('● ' + text)[:160]
    elif measured_chip and not owned:
        text = ''
    radius = int(look.get('shake_rx') or 0)
    shake_rx = max(4, min(64, radius)) if fx['stabilize'] and radius else 16 if fx['stabilize'] else 0
    effect_at = float(picture.get('hold') or 0)
    if placed and effect_at < 0.2:
        effect_at = min(0.98, chip_at)
    mapped = _local_insert(shot.get('event_at'), start, end, duration) if shot.get('event_at') is not None and (fx['blur'] or fx['glow'] or fx['shadow']) else None
    if mapped is not None and end > start:
        effect_at = min(0.98, mapped / (end - start))
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
    # Hold and release are fractions of this shot. Blur, glow, and vignette stop there.
    # An unmeasured exit stays at 1 and the filter runs to the clip end.
    timed = bool(fx['blur'] or fx['glow'] or fx['shadow'])
    if (placed or icon or lower_on or timed or picture.get('callout_out') is not None) and effect_at < exit_frac < 0.999:
        effect_end = round(min(1.0, exit_frac), 2)
    if card is not None and shot.get('card_at') is not None:
        local_in = _clip_fraction(shot['card_at'], duration, start, end)
        if shot.get('card_to') is None:
            local_out = 1.0
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
    lower_x, lower_y = _measured_point(picture, 'lower_place') if icon else (None, None)
    chart_ready = bool(picture.get('graphic') and facts and not fx['split'] and not fx['cutout'])
    groups = _measured_groups(picture)
    spots = [{'x': item['x'], 'y': item['y'], 'w': item['w'], 'h': item['h']} for item in groups]
    card_x = card_y = card_w = card_h = None
    chart_x = chart_y = chart_w = chart_h = None
    if len(groups) >= 2:
        # Fixed order: card, bars, title, then the next group on its own center.
        def group_at(index):
            return groups[index] if index < len(groups) else None
        first = group_at(0)
        if card is not None and first:
            card_x, card_y, card_w, card_h = first['x'], first['y'], first['w'], first['h']
        second = group_at(1)
        if chart_ready and second:
            chart_x, chart_y, chart_w, chart_h = second['x'], second['y'], second['w'], second['h']
        third = group_at(2)
        if third and text and (motion is not None or fx['kinetic'] or bool(hits) or title_x is not None):
            if title_x is None:
                title_x = title_x_end = third['x']
                title_y = title_y_end = third['y']
            if title_w is None:
                title_w, title_h = third['w'], third['h']
        fourth = group_at(3)
        if fourth and lower_x is None:
            lower_x, lower_y = fourth['x'], fourth['y']
    else:
        if card is not None:
            card_x, card_y = _measured_point(picture, 'card_place')
            card_w, card_h = _measured_size(picture.get('card_place') if isinstance(picture, dict) else None)
        if chart_ready:
            chart_x, chart_y = _measured_point(picture, 'chart_place')
            chart_w, chart_h = _measured_size(picture.get('chart_place') if isinstance(picture, dict) else None)
    letter = picture.get('letter') if isinstance(picture.get('letter'), dict) else {}
    kind_name = letter.get('kind') if letter.get('kind') in ('serif', 'sans') else ''
    weight_name = letter.get('weight') if letter.get('weight') in ('light', 'heavy') else ''
    type_style = f'{kind_name}-{weight_name}' if kind_name and weight_name else ''
    letter_face = ''
    if type_style:
        from .style_vision import choose_face
        letter_face = choose_face(kind_name, weight_name) or ''
    kind = _transition(shot or {})
    key_side, key_amount, fill_side, fill_amount, rim_amount = _clip_lights(look)
    copied = None if chart_ready or fx['cutout'] or fx['split'] else _picture_insert(shot or {}, start, end, duration)
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
        transition=kind,
        transition_seconds=_join_seconds(picture, kind),
        shot_type=_shot_type(shot or {}),
        text=text,
        audio_fade_ms=16 if kind != 'cut' else 0,
        cutaway=cutaway,
        effect_at=round(effect_at, 2),
        effect_end=round(effect_end, 2),
        card=card,
        enhance=False,
        speed=speed,
        speed_end=speed_end,
        roll=roll,
        roll_end=roll_end,
        orbit_x=orbit_x,
        orbit_y=orbit_y,
        focus=focus,
        blur=fx['blur'],
        glow=fx['glow'],
        glow_amount=fx['glow_amount'],
        shadow=fx['shadow'],
        shade=fx['shade'],
        split=fx['split'],
        split_at=split_at,
        stabilize=fx['stabilize'],
        shake_rx=shake_rx,
        cutout=fx['cutout'],
        kinetic=bool(text) and (title_x is not None or bool(hits)),
        title_in=0 if title_in is None else title_in,
        title_out=1 if title_out is None else title_out,
        title_x=title_x,
        title_y=title_y,
        title_x_end=title_x_end,
        title_y_end=title_y_end,
        title_w=title_w,
        title_h=title_h,
        kinetic_at=hits,
        mask=bool(fx['mask'] and not fx['cutout'] and not fx['split']),
        mask_rx=mask_rx,
        mask_ry=mask_ry,
        track=tracked,
        exposure=exposure,
        key_side=key_side,
        key_amount=key_amount,
        fill_side=fill_side,
        fill_amount=fill_amount,
        rim_amount=rim_amount,
        progress=max(0, min(1, float(progress or 0))),
        progress_at=progress_at,
        progress_end=progress_end,
        progress_play=bool(progress_play),
        plate='1A1F1C' if fx['cutout'] else '',
        subject_x=None if not fx.get('subject') else fx['subject']['x'],
        subject_y=None if not fx.get('subject') else fx['subject']['y'],
        subject_w=None if not fx.get('subject') else fx['subject']['w'],
        subject_h=None if not fx.get('subject') else fx['subject']['h'],
        graphic=chart_ready,
        bars=_bars(facts) if chart_ready else [],
        chart_x=chart_x,
        chart_y=chart_y,
        chart_w=chart_w,
        chart_h=chart_h,
        lower=lower_on,
        icon=icon,
        lower_x=lower_x,
        lower_y=lower_y,
        mark=(_owned_fill(facts) or 0) if icon else 0,
        card_x=card_x,
        card_y=card_y,
        card_w=card_w,
        card_h=card_h,
        panel=_panel_start(start, end, duration) if fx['split'] and not fx['cutout'] else None,
        still=(_panel_start(start, end, duration) if _panel_start(start, end, duration) is not None else start) if picture.get('graphic') and not facts and not fx['split'] and not fx['cutout'] and screen is None and not diagram else None,
        screen=screen,
        bezel=float(picture.get('bezel') or 0.1) if screen is not None and 0.06 <= float(picture.get('bezel') or 0) <= 0.28 else 0.1,
        diagram=diagram,
        grade=grade,
        picture_insert=copied,
        face=letter_face,
        type_style=type_style,
        spots=spots,
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
    if any(c.get('cutout') for c in clips): done.add('presenter_cutout')
    if any(c.get('cutout') and c.get('subject_w') for c in clips): done.add('background_replacement')
    if any(c.get('grade') for c in clips): done.add('color_grade')
    if any(abs((c.get('speed') or 1) - 1) > 0.04 or (c.get('speed_end') is not None and abs(c['speed_end'] - (c.get('speed') or 1)) > 0.04) for c in clips): done.add('speed_ramp')
    if any(c.get('kinetic') for c in clips): done.add('kinetic_type')
    if any(isinstance((shot.get('picture') or {}).get('title'), dict) for shot in shots) and not any(c.get('kinetic') and c.get('text') for c in clips):
        found.append({'id': 'owned_title', 'essential': True})
    if any(c.get('track') for c in clips): done.add('motion_tracking')
    if any(c.get('mask') for c in clips): done.add('mask')
    if any((c.get('key_amount') or 0) >= 0.04 for c in clips): done.add('key_light')
    if any((c.get('fill_amount') or 0) >= 0.04 for c in clips): done.add('fill_light')
    if any((c.get('rim_amount') or 0) >= 0.04 for c in clips): done.add('rim_light')
    for index, shot in enumerate(shots or []):
        picture = shot.get('picture') if isinstance(shot.get('picture'), dict) else {}
        join = str(picture.get('join') or '')
        applied = clips[index].get('transition') if index < len(clips) else 'cut'
        if join == 'zoom' and applied != 'zoom':
            found.append({'id': 'zoom_transition', 'essential': False})
        if join in ('wipe-right', 'wiperight') and applied not in ('wipe', 'wipe-right'):
            found.append({'id': 'wipe_right', 'essential': False})
        if join in ('wipe-up', 'wipeup') and applied != 'wipe-up':
            found.append({'id': 'wipe_up', 'essential': False})
        if join in ('wipe-down', 'wipedown') and applied != 'wipe-down':
            found.append({'id': 'wipe_down', 'essential': False})
    screens = [c.get('screen') for c in clips if c.get('screen') is not None]
    if screens and not all(_owned_frame_is_screen(source, stamp) for stamp in screens):
        found.append({'id': 'owned_screen_frame', 'essential': False, 'note': 'owned frame, not a reference screenshot'})
    return [g for g in found if g['id'] not in done]

def _lengths_of(rows):
    found = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        try:
            span = float(row.get('end', 0)) - float(row.get('start', 0))
        except (TypeError, ValueError):
            continue
        if span > 0:
            found.append(span)
    return found

def _shares(lengths):
    total = sum(lengths)
    if total <= 0:
        return []
    return [item / total for item in lengths]

def _series_score(left, right):
    """0-100 from normalized cut spacing. An extra cut counts as a miss, not as 100."""
    if not left or not right:
        return None
    width = max(len(left), len(right))
    gap = 0.0
    for index in range(width):
        a = left[index] if index < len(left) else 0.0
        b = right[index] if index < len(right) else 0.0
        gap += abs(a - b)
    return max(0.0, min(100.0, 100 - (gap / width) * 100))

def structure_and_pacing(reference_lengths, own_lengths):
    """Shot count and durations, and the spacing of the cuts. None when a side has no shots."""
    try:
        ref = [float(item) for item in reference_lengths or [] if float(item) > 0]
        own = [float(item) for item in own_lengths or [] if float(item) > 0]
    except (TypeError, ValueError):
        return {'shot_structure': None, 'visual_pacing': None}
    if not ref or not own:
        return {'shot_structure': None, 'visual_pacing': None}
    count = 100.0 * min(len(ref), len(own)) / max(len(ref), len(own))
    spacing = _series_score(_shares(ref), _shares(own))
    if spacing is None:
        return {'shot_structure': None, 'visual_pacing': None}
    return {
        'shot_structure': round((count + spacing) / 2, 1),
        'visual_pacing': round(spacing, 1),
    }

def _graphic_kinds(picture):
    """Measured card, title, chart, and lower plate. Words do not add a kind."""
    if not isinstance(picture, dict):
        return set()
    kinds = set()
    if picture.get('card') or isinstance(picture.get('card_place'), dict):
        kinds.add('card')
    if isinstance(picture.get('title'), dict):
        kinds.add('title')
    if picture.get('graphic') or picture.get('illustration') or isinstance(picture.get('chart_place'), dict):
        kinds.add('chart')
    if picture.get('lower') or isinstance(picture.get('lower_place'), dict):
        kinds.add('lower')
    return kinds

def _clip_graphic_kinds(clip):
    if not isinstance(clip, dict):
        return set()
    kinds = set()
    if clip.get('card'):
        kinds.add('card')
    if clip.get('kinetic') or clip.get('title_x') is not None:
        kinds.add('title')
    if clip.get('graphic') or clip.get('bars') or clip.get('diagram') or clip.get('chart_x') is not None:
        kinds.add('chart')
    if clip.get('lower'):
        kinds.add('lower')
    return kinds

def _graphic_rule(shots, clips):
    """Share of measured graphic kinds the paired clip actually has. No measured kind stays 100."""
    parts = []
    for index, shot in enumerate(shots or []):
        ref_kinds = _graphic_kinds(shot.get('picture') if isinstance(shot, dict) else None)
        if not ref_kinds:
            continue
        clip = clips[index] if index < len(clips) else {}
        parts.append(100 * len(ref_kinds & _clip_graphic_kinds(clip)) / len(ref_kinds))
    if not parts:
        return 100.0
    return round(sum(parts) / len(parts), 1)

def _as_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0

def _measured_effect_names(picture):
    """Effects the reference picture measured, aside from zoom, position, and the join."""
    if not isinstance(picture, dict):
        return []
    found = []
    if _as_float(picture.get('blur')) > 0:
        found.append('blur')
    if _as_float(picture.get('glow')) > 0:
        found.append('glow')
    if picture.get('vignette') or _as_float(picture.get('shade')) > 0:
        found.append('shadow')
    if picture.get('mask'):
        found.append('mask')
    if picture.get('split'):
        found.append('split')
    if picture.get('screen'):
        found.append('screen')
    try:
        speed = picture.get('speed')
        if speed is not None and abs(float(speed) - 1) > 0.04:
            found.append('speed')
    except (TypeError, ValueError):
        pass
    if picture.get('lower'):
        found.append('lower')
    return found

def _clip_has_effect(clip, name):
    if not isinstance(clip, dict):
        return False
    if name == 'blur':
        return float(clip.get('blur') or 0) > 0
    if name == 'glow':
        return bool(clip.get('glow'))
    if name == 'shadow':
        return bool(clip.get('shadow'))
    if name == 'mask':
        return bool(clip.get('mask'))
    if name == 'split':
        return bool(clip.get('split'))
    if name == 'screen':
        return clip.get('screen') is not None
    if name == 'speed':
        try:
            speed = float(clip.get('speed') or 1)
            end = clip.get('speed_end')
            moved = end is not None and abs(float(end) - 1) > 0.04
        except (TypeError, ValueError):
            return False
        return abs(speed - 1) > 0.04 or moved
    if name == 'lower':
        return bool(clip.get('lower'))
    return False

def _production_rule(shots, clips, duration):
    """A measured effect the clip does not carry lowers the rule. Nothing measured keeps coverage."""
    requested = applied = 0
    for index, shot in enumerate(shots or []):
        picture = shot.get('picture') if isinstance(shot, dict) else None
        clip = clips[index] if index < len(clips) else {}
        for name in _measured_effect_names(picture):
            requested += 1
            if _clip_has_effect(clip, name):
                applied += 1
    if requested:
        return round(100 * applied / requested, 1)
    covered = abs(sum(float(c.get('end', 0)) - float(c.get('start', 0)) for c in clips) - float(duration)) < 0.05
    return 80.0 if covered else 70.0 if clips else 40.0

def _scores(shots, edit, gaps, duration):
    clips = edit['clips']
    paced = structure_and_pacing(_lengths_of(shots), _lengths_of(clips))
    if paced['shot_structure'] is None:
        reference_count = max(1, len(shots))
        structure = round(100 * min(reference_count, len(clips)) / max(reference_count, len(clips)), 1)
        pacing = 50.0
    else:
        structure = paced['shot_structure']
        pacing = paced['visual_pacing']
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
    graphics = _graphic_rule(shots, clips)
    graded = any(c.get('grade') for c in clips)
    enhanced = any(c.get('enhance') for c in clips)
    color = 72.0 if graded else 35.0 if 'color_grade' in gap_ids and enhanced else 0.0 if 'color_grade' in gap_ids else 75.0 if enhanced else 100.0
    production = _production_rule(shots, clips, duration)
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

def _report(shots, edit, duration, trimmed, source=None, brand=None):
    gaps = _gaps(shots, edit, source)
    painted = any(c.get('text') or c.get('bars') or c.get('graphic') or c.get('lower') or c.get('progress') for c in edit['clips'])
    if brand == '' and painted and not any(g['id'] == 'owned_brand' for g in gaps):
        gaps.append({'id': 'owned_brand', 'essential': False})
    scores = _scores(shots, edit, gaps, duration)
    return {
        'scores': scores,
        'applied': _applied(edit, trimmed),
        'gaps': gaps,
        'sections': [{'index': i, 'start': c['start'], 'end': c['end'], 'transition': c['transition'], 'zoom': c['zoom']} for i, c in enumerate(edit['clips'])],
        'note': 'owned_only',
        'compared': False,
        'shot_structure_rule': scores['shot_structure'],
        'visual_pacing_rule': scores['visual_pacing'],
        'effect_similarity_rule': scores['effect_similarity'],
        'motion_graphic_style_rule': scores['motion_graphic_style'],
        'color_treatment_rule': scores['color_treatment'],
        'production_quality_rule': scores['production_quality'],
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
    from .style_vision import kept_shots
    merged = kept_shots(shots)
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
    lights = measured.get('lights') if isinstance(measured.get('lights'), dict) else None
    return {'flat': measured.get('flat') or measured.get('chroma'), 'grade': measured.get('grade'), 'track': measured.get('track'), 'chroma': measured.get('chroma'), 'room': measured.get('room') if isinstance(measured.get('room'), dict) else None, 'exposure': measured.get('exposure') or 0, 'lights': lights, 'split': layout.get('split'), 'bar': layout.get('bar'), 'bar_in': layout.get('bar_in'), 'bar_out': layout.get('bar_out'), 'lower': layout.get('lower'), 'shake': layout.get('shake'), 'shake_rx': int(layout.get('shake_rx') or 0)}

def _clip_lights(look):
    """Copy a measured key, fill, and rim. A lighting sentence does not set one."""
    lights = look.get('lights') if isinstance(look.get('lights'), dict) else {}

    def amount(name, cap, present):
        if not present:
            return 0.0
        try:
            value = float(lights.get(name) or 0)
        except (TypeError, ValueError):
            return 0.0
        if value != value or value < 0.04:
            return 0.0
        return round(min(cap, value), 3)

    key = lights.get('key') if lights.get('key') in ('left', 'right', 'top') else None
    fill = lights.get('fill') if lights.get('fill') in ('left', 'right', 'bottom') else None
    return key, amount('key_amount', 0.35, bool(key)), fill, amount('fill_amount', 0.2, bool(fill)), amount('rim_amount', 0.35, True)

def _punch(cuts, spans, transcript):
    """Drop black or frozen holes of at least 0.2s. Speech on the hole does not keep it."""
    del transcript
    holes = []
    for span in spans or []:
        try:
            start, end = float(span['start']), float(span['end'])
        except (KeyError, TypeError, ValueError):
            continue
        if end - start < 0.2:
            continue
        holes.append((start, end))
    if not holes:
        return list(cuts)
    punched = []
    for start, end in cuts:
        cursor = start
        for hole_start, hole_end in holes:
            if hole_end <= cursor or hole_start >= end:
                continue
            left = min(hole_start, end)
            if left - cursor >= 0.28:
                punched.append((round(cursor, 3), round(left, 3)))
            cursor = max(cursor, min(hole_end, end))
        if end - cursor >= 0.28:
            punched.append((round(cursor, 3), round(end, 3)))
    if not punched:
        return list(cuts)
    return punched

def _line_key(text):
    words = re.findall(r'[A-Za-z\u0400-\u04FF]{3,}', (text or '').lower())
    return ' '.join(words[:6])

def _has_speech(start, end, transcript):
    for row in transcript or []:
        try:
            row_start, row_end = float(row['start']), float(row['end'])
        except (KeyError, TypeError, ValueError):
            continue
        if min(end, row_end) - max(start, row_start) > 0:
            return True
    return False

def _repeated_lines(transcript):
    groups = {}
    for row in transcript or []:
        key = _line_key(row.get('original') or row.get('en') or '')
        if len(key) < 3:
            continue
        try:
            start, end = float(row['start']), float(row['end'])
        except (KeyError, TypeError, ValueError):
            continue
        if end - start < 0.4:
            continue
        groups.setdefault(key, []).append((start, end))
    return [spans for spans in groups.values() if len(spans) >= 2]

def _best_takes(cuts, transcript, unusable):
    """Overlapping copies keep the smaller unusable overlap. Speech breaks a tie."""
    if not cuts or not transcript:
        return list(cuts)
    holes = []
    for span in unusable or []:
        try:
            holes.append((float(span['start']), float(span['end'])))
        except (KeyError, TypeError, ValueError):
            continue
    repeated = _repeated_lines(transcript)
    chosen = list(cuts)
    parent = list(range(len(chosen)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for i, (start, end) in enumerate(chosen):
        for j in range(i + 1, len(chosen)):
            other_start, other_end = chosen[j]
            if min(end, other_end) - max(start, other_start) > 0.2:
                parent[find(j)] = find(i)
    clusters = {}
    for index in range(len(chosen)):
        clusters.setdefault(find(index), []).append(index)
    drop_at = set()
    for members in clusters.values():
        if len(members) < 2:
            continue
        scored = []
        for index in members:
            start, end = chosen[index]
            if end <= start:
                continue
            scored.append((_overlap(start, end, holes), 0 if _has_speech(start, end, transcript) else 1, index))
        if not scored:
            continue
        scored.sort()
        best_bad = scored[0][0]
        cleanest = [index for bad, _speech, index in scored if bad == best_bad]
        speakers = [index for index in cleanest if _has_speech(*chosen[index], transcript)]
        if speakers:
            same_line = False
            if len(speakers) > 1:
                for spans in repeated:
                    covered = [index for index in speakers if _overlap(*chosen[index], spans) > 0]
                    if len(covered) > 1:
                        speakers = covered
                        same_line = True
                        break
            winners = speakers if len(speakers) > 1 and not same_line else speakers[:1]
        elif len(cleanest) == 1:
            winners = cleanest
        else:
            continue
        for index in members:
            if index in winners:
                continue
            start, end = chosen[index]
            if any(min(end, chosen[win][1]) - max(start, chosen[win][0]) > 0.2 for win in winners):
                drop_at.add(index)
    kept = [cut for index, cut in enumerate(chosen) if index not in drop_at]
    if not kept:
        return list(cuts)
    return kept

def _title_word(title):
    for word in re.findall(r'[A-Za-z\u0400-\u04FF]{3,}', title or ''):
        if word.lower() not in STOP:
            return word[:24]
    return ''

def _prefix_title(text, word):
    if not word or not str(text or '').strip():
        return text or ''
    if str(text).split()[0].lower() == word.lower():
        return text
    return f'{word} {text}'[:160]

def build(shots, duration, transcript, has_audio, script='', recommendations=None, measured=None, source=None, title=''):
    measured = measured or {}
    timed = list(shots)
    if measured.get('shots'):
        timed = [{**(shots[i % len(shots)] if shots else {}), **span, 'start': span['start'], 'end': span['end']} for i, span in enumerate(measured['shots'])]
    extra = list(recommendations or [])
    for span in measured.get('silences') or []:
        if float(span['end']) - float(span['start']) >= 1:
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
    cuts = _punch(cuts, measured.get('unusable'), transcript)
    cuts = _best_takes(cuts, transcript, measured.get('unusable'))
    facts = _facts(script, transcript)
    look = _look(measured)
    graphic = next((i for i, (start, end) in enumerate(cuts) if end - start >= 1.2 and _has(_blob([timed[i % len(timed)] if timed else {}]), ('chart', 'number', 'statistic', 'progress'))), None)
    owned_bar = _owned_fill(facts) if look.get('bar') else None
    playhead = bool(look.get('bar')) and owned_bar is None
    clips = [_clip(timed[i % len(timed)] if timed else {}, start, end, transcript, f'style_{i}', float(duration), facts, allow_card=(i == graphic), look=look, ref_len=(timed[i % len(timed)].get('ref_len') if timed else None), progress=(owned_bar if owned_bar is not None else ((i + 1) / len(cuts) if look.get('bar') else 0)), progress_play=playhead, script=script) for i, (start, end) in enumerate(cuts)]
    word = _title_word(title)
    brand = None
    if source:
        try:
            from .style_vision import owned_ink
            brand = owned_ink(source)
        except Exception:
            brand = None
    for clip in clips:
        if word:
            clip.text = _prefix_title(clip.text, word)
        if brand and (clip.text or clip.bars or clip.graphic or clip.lower or clip.progress):
            clip.ink = brand
    _retarget_owned_screens(clips, source, float(duration))
    emphasize = _wants_captions(timed or shots)
    captions = _captions(transcript, emphasize)
    saw_highlight = _emphasize_owned_hits(captions, timed, cuts)
    subtitles = bool(captions) and (emphasize or saw_highlight)
    emphasized = any(c.emphasis_en or c.emphasis_zh for c in captions) if subtitles else False
    edit = Edit(clips=clips, captions=captions if subtitles else [], subtitles=subtitles, normalize=bool(has_audio), font_size='large' if emphasized else 'medium', color='yellow' if emphasized else 'white')
    check(edit, float(duration))
    dumped = edit.model_dump()
    trimmed = abs(sum(c['end'] - c['start'] for c in dumped['clips']) - float(duration)) >= 0.5
    return dumped, _report(timed or shots, dumped, duration, trimmed, source, brand)

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

def _store(db, pid, edit, report, status, render, *, baked=False):
    current, context = _context(db, pid)
    context['style_match'] = True
    context['style_report'] = report
    context['style_match_status'] = status
    if baked:
        previous = context.get('effect_board')
        context['effect_board_in_edit'] = copy.deepcopy(previous) if isinstance(previous, dict) else previous
    else:
        # The stored cut stays the style-match base. Picture render applies the saved board.
        context['effect_board_in_edit'] = None
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

def board_for_render(edit, context):
    """Apply the project's saved effect recipe when the picture is rendered."""
    if not isinstance(edit, dict):
        return edit
    context = context or {}
    board = context.get('effect_board')
    if not isinstance(board, dict):
        return edit
    # Missing means an older cut already includes the board it was built with.
    if 'effect_board_in_edit' not in context:
        return edit
    if context.get('effect_board_in_edit') == board:
        return edit
    return _with_board(edit, context)

def _with_board(edit, context):
    board = (context or {}).get('effect_board')
    if not isinstance(board, dict):
        return edit
    try:
        return Edit.model_validate(apply_effect_board(edit, board)).model_dump()
    except Exception:
        return edit

def _stored_reference(context, pid):
    """Uploaded reference file or a held upload id. A Douyin id alone does not count."""
    context = context or {}
    if context.get('reference_file'):
        return True
    if str(context.get('reference_upload_id') or '').strip():
        return True
    if not pid:
        return False
    from .config import settings
    return (settings.data_dir / pid / 'reference_source').is_file()

def _style_on(current, pid):
    context = (current or {}).get('context') or {}
    return bool(context.get('style_match')) or _stored_reference(context, pid)

def match_project(pid):
    from .studio import state
    current = state(pid)
    if not _style_on(current, pid):
        return
    item = project(pid)
    from .config import settings
    owned_source = settings.data_dir / pid / 'source'
    shots = shots_of(current.get('dna'))
    transcript = (current.get('plan') or {}).get('transcript') or []
    edit, report = build(shots, item['metadata']['duration'], transcript, item['metadata'].get('has_audio'), script=item.get('brief') or '', recommendations=(current.get('plan') or {}).get('recommendations') or [], measured=current['context'].get('measured') or {}, source=owned_source if owned_source.is_file() else None, title=item.get('title') or '')
    try:
        from .style_stock import attach
        edit, report = attach(pid, edit, shots, item.get('brief') or '', report, item['metadata']['duration'])
    except Exception:
        pass
    with connect() as db:
        db.lock()
        _store(db, pid, edit, report, 'pending', True)

def record_failure(pid):
    report = {'scores': {key: 0 for key in (*SCORE_KEYS, 'overall')}, 'applied': [], 'gaps': [{'id': 'style_match_failed', 'essential': True}], 'sections': [], 'note': 'owned_only', 'compared': False, 'shot_structure_rule': 0, 'visual_pacing_rule': 0, 'effect_similarity_rule': 0, 'motion_graphic_style_rule': 0, 'color_treatment_rule': 0, 'production_quality_rule': 0, 'comparison_note': FRAMES_NOT_COMPARED}
    with connect() as db:
        db.lock()
        current, context = _context(db, pid)
        if not _style_on(current, pid):
            return
        context['style_match'] = True
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
        stored = _stored_reference(current.get('context'), pid)
        if not current['context'].get('style_match') and not stored:
            raise HTTPException(422, 'style_match_off')
        if not current.get('plan') and not stored:
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
    from .style_vision import chroma_plate, color_sample, flat_background, grade_between, highlight_window, light_between, lights_of, measure, reference_layout, room_subject, unusable_spans, visual_track
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
        'room': quiet(lambda: room_subject(source), None),
        'grade': grade,
        'exposure': exposure,
        'lights': quiet(lambda: lights_of(reference), None) if reference else None,
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

def _refresh_overall(scores):
    if all(key in scores for key in SCORE_KEYS):
        scores['overall'] = round(sum(float(scores[key]) for key in SCORE_KEYS) / len(SCORE_KEYS), 1)

def _neutral_grade(grade):
    if not isinstance(grade, dict):
        return True
    try:
        gamma = float(grade.get('gamma') if grade.get('gamma') is not None else 1)
        gs = float(grade.get('gs') or 0)
    except (TypeError, ValueError):
        return True
    return abs(gamma - 1) < 0.02 and abs(gs) < 0.02

def _light_amounts(source):
    found = {}
    for key in ('key_amount', 'fill_amount', 'rim_amount'):
        try:
            found[key] = float((source or {}).get(key) or 0) if isinstance(source, dict) else 0.0
        except (TypeError, ValueError):
            found[key] = 0.0
    return found

def _clip_grade(clips):
    grade = None
    lights = {'key_amount': 0.0, 'fill_amount': 0.0, 'rim_amount': 0.0}
    for clip in clips or []:
        if not isinstance(clip, dict):
            continue
        if grade is None and isinstance(clip.get('grade'), dict):
            grade = clip['grade']
        for key in lights:
            try:
                lights[key] = max(lights[key], float(clip.get(key) or 0))
            except (TypeError, ValueError):
                pass
    return grade, lights

def grade_alignment(reference_grade, reference_lights, clips):
    """Closeness of applied gamma, green shift, and key/fill/rim.

    None when neither side has a grade, so a missing grade is not scored as a match.
    0 when the reference measured a grade and the clip applied none.
    """
    applied_grade, applied_lights = _clip_grade(clips)
    ref_lights = _light_amounts(reference_lights)
    wanted = not _neutral_grade(reference_grade) or any(value >= 0.04 for value in ref_lights.values())
    applied = isinstance(applied_grade, dict) or any(value >= 0.04 for value in applied_lights.values())
    if not wanted and not applied:
        return None
    if wanted and not applied:
        return 0.0
    target_gamma, target_gs = 1.0, 0.0
    if isinstance(reference_grade, dict):
        try:
            target_gamma = float(reference_grade.get('gamma') if reference_grade.get('gamma') is not None else 1)
            target_gs = float(reference_grade.get('gs') or 0)
        except (TypeError, ValueError):
            target_gamma, target_gs = 1.0, 0.0
    have_gamma, have_gs = 1.0, 0.0
    if isinstance(applied_grade, dict):
        try:
            have_gamma = float(applied_grade.get('gamma') if applied_grade.get('gamma') is not None else 1)
            have_gs = float(applied_grade.get('gs') or 0)
        except (TypeError, ValueError):
            have_gamma, have_gs = 1.0, 0.0
    parts = [
        max(0.0, 100 - abs(have_gamma - target_gamma) / 0.6 * 100),
        max(0.0, 100 - abs(have_gs - target_gs) / 0.4 * 100),
    ]
    for key, span in (('key_amount', 0.35), ('fill_amount', 0.2), ('rim_amount', 0.35)):
        parts.append(max(0.0, 100 - abs(applied_lights[key] - ref_lights[key]) / span * 100))
    return round(sum(parts) / len(parts), 1)

def color_after_render(distance, reference_grade, reference_lights, clips):
    """Luma/chroma distance, folded with the grade the clip actually applied."""
    distance_score = max(0.0, min(100.0, 100 - float(distance)))
    aligned = grade_alignment(reference_grade, reference_lights, clips)
    if aligned is None:
        return round(distance_score, 1)
    return round((distance_score + aligned) / 2, 1)

def _rendered_terms(reference, output):
    """Frame measurements for structure, pacing, graphic style, and production. Unreadable terms stay None."""
    from .style_vision import contrast_similarity, graphic_similarity, shot_lengths
    terms = {key: None for key, _rule, _measured, _label in FRAME_RULES}
    try:
        ref_lengths = shot_lengths(reference)
        out_lengths = shot_lengths(output)
    except Exception:
        ref_lengths = out_lengths = None
    if ref_lengths and out_lengths:
        paced = structure_and_pacing(ref_lengths, out_lengths)
        terms['shot_structure'] = paced.get('shot_structure')
        terms['visual_pacing'] = paced.get('visual_pacing')
    try:
        terms['motion_graphic_style'] = graphic_similarity(reference, output)
    except Exception:
        terms['motion_graphic_style'] = None
    try:
        terms['production_quality'] = contrast_similarity(reference, output)
    except Exception:
        terms['production_quality'] = None
    return terms

def blend_effect_similarity(report, frame_similarity, measured=None):
    """Average each rule with its frame measurement. No frames leaves every score on the rule.

    Effect similarity already blends contrast, edge, layout, the title box, and the
    title-box edge shape. Shot structure, pacing, graphic style, and production
    quality blend the same way when those terms can be read. A term that cannot
    be measured stays the rule, and the note says so. It is not rewritten to 100.
    """
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
        _refresh_overall(scores)
        return report
    scores['effect_similarity'] = round((rule + float(frame_similarity)) / 2, 1)
    report['measured_effect_similarity'] = frame_similarity
    report['compared'] = True
    if measured is None:
        report['comparison_note'] = ''
        _refresh_overall(scores)
        return report
    pending = []
    for score_key, rule_key, measured_key, label in FRAME_RULES:
        value = measured.get(score_key) if isinstance(measured, dict) else None
        term_rule = report.get(rule_key)
        if term_rule is None:
            term_rule = scores.get(score_key, 0)
        term_rule = float(term_rule)
        report[rule_key] = term_rule
        if value is None:
            scores[score_key] = term_rule
            report.pop(measured_key, None)
            pending.append(label)
        else:
            scores[score_key] = round((term_rule + float(value)) / 2, 1)
            report[measured_key] = value
    report['comparison_note'] = '' if not pending else 'Left on the rule: ' + ', '.join(pending) + '.'
    _refresh_overall(scores)
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
            if report.get('color_treatment_rule') is None:
                report['color_treatment_rule'] = report.get('scores', {}).get('color_treatment', 0)
            report['measured_color_distance'] = round(distance, 2)
            edit = None
            try:
                from .manual import read
                edit = read(pid, db)
            except Exception:
                edit = None
            measured_ctx = context.get('measured') if isinstance(context.get('measured'), dict) else {}
            clips = (edit or {}).get('clips') if isinstance(edit, dict) else []
            report['scores']['color_treatment'] = color_after_render(distance, measured_ctx.get('grade'), measured_ctx.get('lights'), clips)
        if measured is None:
            blend_effect_similarity(report, None)
        else:
            try:
                terms = _rendered_terms(reference, output)
            except Exception:
                terms = {key: None for key, _rule, _measured_key, _label in FRAME_RULES}
            blend_effect_similarity(report, measured, terms)
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
        stored = _stored_reference(current.get('context'), pid)
        if not current['context'].get('style_match') and not stored:
            raise HTTPException(422, 'style_match_off')
        if not current['context'].get('style_report') and not stored:
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
        context['style_match'] = True
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
    plan = current.get('plan') or {}
    transcript = plan.get('transcript') or []
    owned_source = None
    try:
        from .config import settings
        candidate = settings.data_dir / pid / 'source'
        owned_source = candidate if candidate.is_file() else None
    except Exception:
        owned_source = None
    edit, report = build(shots, item['metadata']['duration'], transcript, item['metadata'].get('has_audio'), script=item.get('brief') or '', recommendations=plan.get('recommendations') or [], measured=current['context'].get('measured') or {}, source=owned_source, title=item.get('title') or '')
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
        raise HTTPException(422, 'save_manual_first' if _stored_reference(current.get('context'), pid) else 'style_match_off')
    shots = shots_of(current.get('dna'))
    transcript = (current.get('plan') or {}).get('transcript') or []
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
        _store(db, pid, dumped, report, 'pending', True, baked=True)
    return {'ok': True}
