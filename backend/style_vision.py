"""Measurements taken from an uploaded reference. Reference pixels are never copied into the export."""
import re
from . import media

def _stats(path, vf, frames=8):
    out, err = media.ffmpeg('-i', path, '-vf', vf, '-frames:v', str(frames), '-f', 'null', '-', timeout=180)
    text = out + '\n' + err
    def values(key):
        return [float(item) for item in re.findall(r'signalstats\.' + key + r'=([\d.]+)', text)]
    ys, us, vs = values('YAVG'), values('UAVG'), values('VAVG')
    if not ys:
        return None
    sats, highs, lows, difs = values('SATAVG'), values('YHIGH'), values('YLOW'), values('YDIF')
    peaks, sat_peaks = values('YMAX'), values('SATMAX')
    spread = (sum(highs) / len(highs) - sum(lows) / len(lows)) if highs and lows else None
    return {
        'y': sum(ys) / len(ys),
        'u': sum(us) / len(us) if us else 128,
        'v': sum(vs) / len(vs) if vs else 128,
        'sat': sum(sats) / len(sats) if sats else None,
        'spread': spread,
        'ydif': sum(difs) / len(difs) if difs else None,
        'ymax': sum(peaks) / len(peaks) if peaks else None,
        'satmax': sum(sat_peaks) / len(sat_peaks) if sat_peaks else None,
    }

def color_sample(path):
    return _stats(path, 'fps=1,signalstats,metadata=print:file=-')

def frame_similarity(reference, output):
    """How close the rendered frame is to the reference on spread and edge strength."""
    ref_meta, out_meta = media.probe(reference), media.probe(output)
    ref_at = min(0.3, max(0.05, float(ref_meta['duration']) * 0.25))
    out_at = min(0.3, max(0.05, float(out_meta['duration']) * 0.25))
    ref = _stats(reference, f'trim=start={ref_at:.3f}:duration=0.12,signalstats,metadata=print:file=-', frames=1)
    out = _stats(output, f'trim=start={out_at:.3f}:duration=0.12,signalstats,metadata=print:file=-', frames=1)
    if not ref or not out:
        return None
    soft_ref = _softness(reference, ref_at, int(ref_meta['width']), int(ref_meta['height']))
    soft_out = _softness(output, out_at, int(out_meta['width']), int(out_meta['height']))
    spread_gap = abs((ref.get('spread') or 0) - (out.get('spread') or 0))
    soft_gap = abs(soft_ref - soft_out)
    score = 100 - min(50, spread_gap / 3) - min(50, soft_gap * 10)
    return round(max(0, min(100, score)), 1)

def flat_background(path):
    meta = media.probe(path)
    w, h = int(meta['width']), int(meta['height'])
    if w < 48 or h < 48:
        return False
    corners = ((0, 0), (w - 24, 0), (0, h - 24), (w - 24, h - 24))
    samples = []
    for x, y in corners:
        sample = _stats(path, f'crop=24:24:{x}:{y},signalstats,metadata=print:file=-', frames=1)
        if not sample:
            return False
        samples.append(sample['y'])
    return max(samples) - min(samples) <= 14

def scene_shots(path, duration):
    _, err = media.ffmpeg('-i', path, '-vf', "select='gt(scene,0.32)',showinfo", '-an', '-f', 'null', '-', timeout=240)
    times = [0.0]
    for line in err.splitlines():
        match = re.search(r'pts_time:([\d.]+)', line)
        if not match:
            continue
        stamp = float(match.group(1))
        if stamp - times[-1] >= 0.28:
            times.append(stamp)
    if duration - times[-1] >= 0.28:
        times.append(duration)
    else:
        times[-1] = duration
    shots = []
    for index in range(len(times) - 1):
        start, end = times[index], times[index + 1]
        if end - start < 0.28:
            continue
        short = end - start < 0.55
        motion = 'fast punch in' if short else 'slow push in' if end - start < 2.2 else 'static hold'
        try:
            transition = 'cut' if index == 0 else _join(path, start)
        except Exception:
            transition = 'cut'
        shots.append({
            'start': round(start, 3), 'end': round(end, 3),
            'observation': {'en': 'Measured shot', 'zh': '测量镜头'},
            'visual_type': {'en': 'presenter', 'zh': '主讲'},
            'narrative_role': {'en': 'beat', 'zh': '节拍'},
            'motion': {'en': motion, 'zh': '运镜'},
            'transition': {'en': transition, 'zh': '转场'},
            'subtitle_emphasis': {'en': 'keywords', 'zh': '关键词'},
            'music': {'en': '', 'zh': ''},
            'emotion': {'en': 'neutral', 'zh': '中性'},
            'information_density': {'en': 'spoken', 'zh': '口述'},
            'reusable_method': {'en': motion, 'zh': '运镜'},
        })
    return shots or [{
        'start': 0, 'end': round(float(duration), 3),
        'observation': {'en': 'Measured shot', 'zh': '测量镜头'},
        'visual_type': {'en': 'presenter', 'zh': '主讲'},
        'narrative_role': {'en': 'beat', 'zh': '节拍'},
        'motion': {'en': 'static hold', 'zh': '固定'},
        'transition': {'en': 'cut', 'zh': '切'},
        'subtitle_emphasis': {'en': 'keywords', 'zh': '关键词'},
        'music': {'en': '', 'zh': ''},
        'emotion': {'en': 'neutral', 'zh': '中性'},
        'information_density': {'en': 'spoken', 'zh': '口述'},
        'reusable_method': {'en': 'hold the frame', 'zh': '固定机位'},
    }]

def _clamp(value, low, high):
    return max(low, min(high, value))

def grade_between(reference, owned):
    """Move owned color toward the reference with the existing grade sliders."""
    if not reference or not owned:
        return None
    own_sat, ref_sat = owned.get('sat'), reference.get('sat')
    saturation = 1.0
    if own_sat is not None and ref_sat is not None:
        saturation = _clamp((ref_sat + 1) / (own_sat + 1), 0.5, 1.8)
    own_spread, ref_spread = owned.get('spread'), reference.get('spread')
    contrast = 1.0
    if own_spread and ref_spread and own_spread >= 8 and ref_spread >= 8:
        contrast = _clamp(ref_spread / own_spread, 0.8, 1.4)
    return {
        'brightness': round(_clamp((reference['y'] - owned['y']) / 255, -0.2, 0.2), 4),
        'contrast': round(contrast, 4),
        'saturation': round(saturation, 4),
        'gamma': 1.0,
        'rs': round(_clamp((reference['v'] - owned['v']) / 128, -0.3, 0.3), 4),
        'gs': 0.0,
        'bs': round(_clamp((reference['u'] - owned['u']) / 128, -0.3, 0.3), 4),
    }

def light_between(reference, owned):
    """Exposure for the luma that the brightness slider cannot cover."""
    if not reference or not owned:
        return 0
    remainder = (reference['y'] - owned['y']) - _clamp((reference['y'] - owned['y']) / 255, -0.2, 0.2) * 255
    exposure = _clamp(remainder / 80, -1, 1)
    if abs(exposure) < 0.05:
        return 0
    return round(exposure, 3)

def _timed_levels(path):
    out, err = media.ffmpeg('-i', path, '-vf', 'fps=1,signalstats,metadata=print:file=-', '-an', '-f', 'null', '-', timeout=240)
    rows = []
    current = {}

    def flush():
        if current.get('t') is None or current.get('y') is None:
            return
        high, low = current.get('high'), current.get('low')
        spread = high - low if high is not None and low is not None else 0
        rows.append((current['t'], current['y'], spread))

    for line in (out + '\n' + err).splitlines():
        found = re.search(r'pts_time:([\d.]+)', line)
        if found:
            flush()
            current = {'t': float(found.group(1))}
        top = re.search(r'signalstats\.YHIGH=([\d.]+)', line)
        if top:
            current['high'] = float(top.group(1))
        bottom = re.search(r'signalstats\.YLOW=([\d.]+)', line)
        if bottom:
            current['low'] = float(bottom.group(1))
        level = re.search(r'signalstats\.YAVG=([\d.]+)', line)
        if level:
            current['y'] = float(level.group(1))
    flush()
    return rows

def black_spans(path):
    _, err = media.ffmpeg('-i', path, '-vf', 'blackframe=amount=92:threshold=32', '-an', '-f', 'null', '-', timeout=240)
    times = [float(item) for item in re.findall(r'blackframe.*\st:([\d.]+)', err)]
    if not times:
        return []
    spans = []
    start = prev = times[0]
    for stamp in times[1:] + [times[-1] + 1]:
        if stamp - prev > 0.08:
            if prev - start >= 0.4:
                spans.append({'start': round(start, 3), 'end': round(prev + 0.05, 3)})
            start = stamp
        prev = stamp
    return spans

def freeze_spans(path):
    """Near-identical holds. A shot that never moves is left alone."""
    duration = float(media.probe(path)['duration'])
    _, err = media.ffmpeg('-i', path, '-vf', 'freezedetect=n=-70dB:d=0.5', '-an', '-f', 'null', '-', timeout=240)
    starts = [float(item) for item in re.findall(r'freeze_start: ([\d.]+)', err)]
    ends = [float(item) for item in re.findall(r'freeze_end: ([\d.]+)', err)]
    spans = []
    for index, start in enumerate(starts):
        end = ends[index] if index < len(ends) else duration
        if end - start < 0.5 or end - start > duration * 0.85:
            continue
        spans.append({'start': round(start, 3), 'end': round(min(duration, end), 3)})
    return spans

def unusable_spans(path):
    pending = sorted((float(span['start']), float(span['end'])) for span in [*black_spans(path), *freeze_spans(path)] if float(span['end']) - float(span['start']) >= 0.4)
    rows = []
    for start, end in pending:
        if rows and start <= rows[-1]['end'] + 0.05:
            rows[-1]['end'] = round(max(rows[-1]['end'], end), 3)
        else:
            rows.append({'start': round(start, 3), 'end': round(end, 3)})
    return rows

def visual_track(path):
    meta = media.probe(path)
    width, height, duration = int(meta['width']), int(meta['height']), float(meta['duration'])
    if width < 90 or height < 90 or duration < 0.6:
        return None
    def column(at):
        scores = []
        crop_w = width // 3
        for index in range(3):
            sample = _stats(path, f'trim=start={at:.3f}:duration=0.08,crop={crop_w}:{height}:{index * crop_w}:0,signalstats,metadata=print:file=-', frames=1)
            scores.append(sample['y'] if sample else 0)
        if max(scores) - min(scores) < 12:
            return None
        return (0.22, 0.5, 0.78)[scores.index(max(scores))]
    early = column(min(0.12, duration / 3))
    late = column(max(0.2, duration - 0.28))
    if early is None or late is None or abs(early - late) < 0.2:
        return None
    return {'x0': early, 'x1': late}

def chroma_plate(path):
    meta = media.probe(path)
    width, height = int(meta['width']), int(meta['height'])
    if width < 48 or height < 48:
        return None
    samples = []
    for x, y in ((0, 0), (width - 24, 0), (0, height - 24), (width - 24, height - 24)):
        sample = _stats(path, f'crop=24:24:{x}:{y},signalstats,metadata=print:file=-', frames=1)
        if not sample:
            return None
        samples.append(sample)
    us = [item['u'] for item in samples]
    vs = [item['v'] for item in samples]
    if max(us) - min(us) > 18 or max(vs) - min(vs) > 18:
        return None
    luma = sum(item['y'] for item in samples) / 4
    u, v = sum(us) / 4, sum(vs) / 4
    if v < 70 and u < 110 and luma > 60:
        return 'green'
    if u > 150 and v < 150:
        return 'blue'
    return None

def _hex_from_samples(samples):
    if not samples:
        return ''
    sat = sum(item.get('sat') or 0 for item in samples) / len(samples)
    y = sum(item['y'] for item in samples) / len(samples)
    u = sum(item['u'] for item in samples) / len(samples)
    v = sum(item['v'] for item in samples) / len(samples)
    if sat < 16 or (abs(u - 128) < 8 and abs(v - 128) < 8):
        return ''
    chroma_y = 1.164 * (y - 16)
    red = chroma_y + 1.596 * (v - 128)
    green = chroma_y - 0.391 * (u - 128) - 0.813 * (v - 128)
    blue = chroma_y + 2.018 * (u - 128)

    def channel(value):
        return max(0, min(255, int(round(value))))

    return f'{channel(red):02X}{channel(green):02X}{channel(blue):02X}'

def owned_ink(path):
    """Saturated corner color of the owned file. Gray returns an empty string."""
    try:
        meta = media.probe(path)
        width, height = int(meta['width']), int(meta['height'])
    except Exception:
        return None
    if width < 48 or height < 48:
        return None
    samples = []
    for x, y in ((0, 0), (width - 24, 0), (0, height - 24), (width - 24, height - 24)):
        sample = _stats(path, f'crop=24:24:{x}:{y},signalstats,metadata=print:file=-', frames=1)
        if not sample:
            return None
        samples.append(sample)
    return _hex_from_samples(samples)

def highlight_window(path, duration):
    rows = [row for row in _timed_levels(path) if row[1] >= 30]
    if not rows:
        return None
    detailed = [row for row in rows if row[2] >= 12]
    stamp, _level, _spread = max(detailed or rows, key=lambda row: row[2] if detailed else row[1])
    if stamp < 0.8:
        return None
    end = min(float(duration), stamp + 1.2)
    if end - stamp < 0.4:
        return None
    return {'start': round(stamp, 3), 'end': round(end, 3)}

def _level(path, crop, at):
    sample = _stats(path, f'trim=start={max(0, at):.3f}:duration=0.08,{crop},signalstats,metadata=print:file=-', frames=1)
    return sample['y'] if sample else None

def _column_at(path, at):
    meta = media.probe(path)
    width, height = int(meta['width']), int(meta['height'])
    if width < 90 or height < 90:
        return None
    scores = []
    crop_w = width // 3
    for index in range(3):
        level = _level(path, f'crop={crop_w}:{height}:{index * crop_w}:0', at)
        scores.append(0 if level is None else level)
    if max(scores) - min(scores) < 12:
        return None
    return (0.22, 0.5, 0.78)[scores.index(max(scores))]

def _lumas(path, start, end, crop, samples):
    span = max(0.2, end - start)
    samples = max(4, min(24, int(samples)))
    rate = samples / span
    vf = f'trim=start={max(0, start):.3f}:duration={span:.3f},setpts=PTS-STARTPTS,fps={rate:.4f},{crop},signalstats,metadata=print:file=-'
    out, err = media.ffmpeg('-i', path, '-vf', vf, '-frames:v', str(samples), '-f', 'null', '-', timeout=180)
    return [float(item) for item in re.findall(r'signalstats\.YAVG=([\d.]+)', out + '\n' + err)]

def _bar_span(path, width, height, duration):
    """In and out fractions of a thin bright full-width bottom strip."""
    if width < 64 or height < 64 or duration < 0.4:
        return False, 0.0, 1.0
    band = max(12, height // 14)
    samples = 16
    half = max(16, width // 2)
    bottom = _lumas(path, 0, duration, f'crop={width}:{band}:0:{height - band}', samples)
    above = _lumas(path, 0, duration, f'crop={width}:{band}:0:{max(0, height - 2 * band)}', samples)
    left = _lumas(path, 0, duration, f'crop={half}:{band}:0:{height - band}', samples)
    right = _lumas(path, 0, duration, f'crop={half}:{band}:{width - half}:{height - band}', samples)
    count = min(len(bottom), len(above), len(left), len(right))
    if count < 4:
        return False, 0.0, 1.0
    flags = [abs(bottom[i] - above[i]) >= 28 and abs(left[i] - right[i]) <= 16 for i in range(count)]
    if not any(flags):
        return False, 0.0, 1.0
    first = flags.index(True)
    last = count - 1 - flags[::-1].index(True)
    start = 0.0 if first == 0 else (first - 0.5) / count
    end = 1.0 if last >= count - 1 else (last + 0.5) / count
    if end - start < 0.08:
        return False, 0.0, 1.0
    return True, round(max(0.0, min(1.0, start)), 2), round(max(0.0, min(1.0, end)), 2)

def reference_layout(path):
    meta = media.probe(path)
    width, height, duration = int(meta['width']), int(meta['height']), float(meta['duration'])
    empty = {'split': False, 'bar': False, 'lower': False, 'shake': False, 'shake_rx': 0, 'bar_in': 0.0, 'bar_out': 1.0}
    if width < 64 or height < 64:
        return empty
    at = min(0.3, max(0, duration / 3))
    half = max(16, width // 2)
    left = _level(path, f'crop={half}:{height}:0:0', at)
    right = _level(path, f'crop={half}:{height}:{width - half}:0', at)
    split = left is not None and right is not None and abs(left - right) >= 28
    bar, bar_in, bar_out = _bar_span(path, width, height, duration)
    middle = _level(path, f'crop={width}:{max(16, height // 3)}:0:{height // 3}', at)
    lower_band = _level(path, f'crop={width}:{max(16, height // 5)}:0:{height - max(16, height // 5)}', at)
    lower = (not bar) and middle is not None and lower_band is not None and abs(middle - lower_band) >= 40
    later = min(duration - 0.1, at + 0.24)
    first, second = _column_at(path, at), _column_at(path, later)
    moved = abs(first - second) if first is not None and second is not None else 0
    shake = moved >= 0.2
    radius = 32 if moved >= 0.4 else 8 if shake else 0
    return {'split': split, 'bar': bar, 'lower': lower, 'shake': shake, 'shake_rx': radius, 'bar_in': bar_in, 'bar_out': bar_out}

def _arrived(old, now, new):
    return abs(now - new) + 12 < abs(now - old)

def _stayed(old, now, new):
    return abs(now - old) + 12 < abs(now - new)

def _bright_zoom(center, corner):
    """A zoom-in grows a bright center across the cut, or flashes that center while the corner holds."""
    if None in (*center, *corner):
        return False
    grew = center[0] >= corner[0] + 28 and center[1] >= corner[1] + 18 and corner[2] >= corner[0] + 22 and center[2] >= center[0] - 12
    flashed = _arrived(*center) and _stayed(*corner) and center[1] >= corner[1] + 28 and center[1] >= center[0] + 18
    return grew or flashed

def _join(path, at):
    """Name a boundary only when an existing filter reproduces it."""
    meta = media.probe(path)
    width, height, duration = int(meta['width']), int(meta['height']), float(meta['duration'])
    if width < 80 or height < 80 or at < 0.2 or duration - at < 0.2:
        return 'cut'
    before, after = at - 0.16, at + 0.16
    full = [_level(path, f'crop={width}:{height}:0:0', stamp) for stamp in (before, at, after)]
    if any(level is None for level in full):
        return 'cut'
    old, now, new = full
    if old < 45 and now >= old + 22 and new >= old + 22:
        return 'fade'
    if now < 45 and old > now + 22 and new > now + 22:
        return 'fade'
    if abs(old - new) < 12:
        return 'cut'
    half = max(16, width // 2)
    left = [_level(path, f'crop={half}:{height}:0:0', stamp) for stamp in (before, at, after)]
    right = [_level(path, f'crop={half}:{height}:{width - half}:0', stamp) for stamp in (before, at, after)]
    if None not in left + right and _arrived(*left) and _stayed(*right):
        return 'wipe'
    # wipeleft is the installed xfade that shows the new picture on the right first.
    if None not in left + right and _arrived(*right) and _stayed(*left):
        return 'wipe-right'
    band = max(16, height // 2)
    top = [_level(path, f'crop={width}:{band}:0:0', stamp) for stamp in (before, at, after)]
    bottom = [_level(path, f'crop={width}:{band}:0:{height - band}', stamp) for stamp in (before, at, after)]
    # wipeup shows the new picture on the bottom first.
    if None not in top + bottom and _arrived(*bottom) and _stayed(*top):
        return 'wipe-up'
    if None not in top + bottom and _arrived(*top) and _stayed(*bottom):
        return 'wipe-down'
    crop_w, crop_h = max(16, width // 3), max(16, height // 3)
    center = [_level(path, f'crop={crop_w}:{crop_h}:{(width - crop_w) // 2}:{(height - crop_h) // 2}', stamp) for stamp in (before, at, after)]
    corner = [_level(path, 'crop=24:24:0:0', stamp) for stamp in (before, at, after)]
    if _bright_zoom(center, corner):
        return 'zoom'
    if None not in center + corner and _arrived(*center) and _stayed(*corner):
        return 'circle'
    gap = abs(old - new)
    if gap >= 18 and abs(now - (old + new) / 2) <= gap * 0.35:
        return 'crossfade'
    return 'cut'

def _bands(path, at, width, height):
    crop_w = max(16, width // 3)
    scores = []
    for index in range(3):
        level = _level(path, f'crop={crop_w}:{height}:{min(index * crop_w, width - crop_w)}:0', at)
        scores.append(0 if level is None else level)
    return scores

def _grid(path, at, width, height):
    crop_w, crop_h = max(16, width // 3), max(16, height // 3)
    cells = []
    for row in range(3):
        for col in range(3):
            level = _level(path, f'crop={crop_w}:{crop_h}:{min(col * crop_w, width - crop_w)}:{min(row * crop_h, height - crop_h)}', at)
            cells.append(0 if level is None else level)
    return cells

def _subject(cells):
    peak, floor = max(cells), min(cells)
    if peak - floor < 12:
        return 1.0, 0.5, 0.5
    cut = floor + max(18, 0.45 * (peak - floor))
    hot = [index for index, score in enumerate(cells) if score >= cut] or [cells.index(peak)]
    fill = len(hot) / 9
    zoom = round(min(1.45, max(1.0, 1 + 0.45 * (1 - fill) / (1 - 1 / 9))), 2)
    xs, ys = (0.22, 0.5, 0.78), (0.22, 0.5, 0.78)
    return zoom, sum(xs[index % 3] for index in hot) / len(hot), sum(ys[index // 3] for index in hot) / len(hot)

def _series(path, start, end, crop, fps=4, limit=6):
    span = max(0.2, end - start)
    frames = max(3, min(int(limit), int(span * fps)))
    vf = f'trim=start={max(0, start):.3f}:duration={span:.3f},setpts=PTS-STARTPTS,fps={fps},{crop},signalstats,metadata=print:file=-'
    out, err = media.ffmpeg('-i', path, '-vf', vf, '-frames:v', str(frames), '-f', 'null', '-', timeout=180)
    return [float(item) for item in re.findall(r'signalstats\.YAVG=([\d.]+)', out + '\n' + err)]

def _plate_bounds(path, start, end, width, height):
    """Entrance and exit fractions for a lower plate. The exit stays 1 when the plate never leaves."""
    span = end - start
    if span < 0.9 or width < 80 or height < 80:
        return 0.0, 1.0
    fps = 4
    band = max(16, height // 5)
    mid_h = max(16, height // 3)
    lower = _series(path, start, end, f'crop={width}:{band}:0:{height - band}', fps)
    middle = _series(path, start, end, f'crop={width}:{mid_h}:0:{height // 3}', fps)
    count = min(len(lower), len(middle))
    if count < 3:
        return 0.0, 1.0
    flags = [abs(lower[index] - middle[index]) >= 40 for index in range(count)]
    if not any(flags):
        return 0.0, 1.0
    first = flags.index(True)
    entered = 0.0 if first == 0 else round(min(0.7, (first / fps) / span), 2)
    last = count - 1 - flags[::-1].index(True)
    if last >= count - 1:
        left = 1.0
    else:
        left = round(min(1.0, ((last + 1) / fps) / span), 2)
        if left <= entered:
            left = 1.0
    return entered, left

def _entered(path, start, end, width, height):
    """Fraction where a lower plate appears after the opening, else 0."""
    return _plate_bounds(path, start, end, width, height)[0]

def picture_of(path, start, end):
    meta = media.probe(path)
    width, height = int(meta['width']), int(meta['height'])
    wide = {'zoom': 1.0, 'zoom_end': None, 'x': 0.5, 'x_end': None, 'y': 0.5, 'y_end': None, 'split': False, 'graphic': False, 'mask': False, 'lower': False, 'hold': 0.0, 'tiles': 0}
    if width < 90 or height < 90 or end - start < 0.2:
        return wide
    opening_at = min(start + 0.04, end - 0.12)
    closing_at = max(start + 0.04, end - 0.12)
    opening = _bands(path, opening_at, width, height)
    zoom, x, y = _subject(_grid(path, opening_at, width, height))
    zoom_end, x_end, y_end = _subject(_grid(path, closing_at, width, height))
    left, mid, right = opening
    stamp = min(start + 0.04, max(start, end - 0.08))
    shade = _shade(path, stamp, width, height)
    softness = _softness(path, stamp, width, height)
    bloom = 0.0 if softness else _bloom(path, stamp, width, height)
    screen_at = stamp if _screen(path, stamp, width, height) else None
    if screen_at is None and end - start >= 2.5:
        span = float(end) - float(start)
        at = float(start) + span * 0.5
        if _screen(path, at, width, height):
            screen_at = at
    screen = screen_at is not None
    bezel = _bezel(path, screen_at, width, height) if screen else 0.0
    length = float(meta.get('duration') or 0) or float(end - start) or 1.0
    fraction = round(max(0.0, min(1.0, screen_at / length)), 3) if screen else None
    mask = _window(path, stamp, width, height)
    lower = False if mask else _lower_strip(path, stamp, width, height)
    hold = 0.0
    release = 1.0
    if end - start >= 0.9 and not mask and (lower or (softness <= 0 and bloom <= 0 and shade <= 0)):
        entered, left = _plate_bounds(path, start, end, width, height)
        if not lower and softness <= 0 and bloom <= 0 and shade <= 0:
            hold = entered
            if hold >= 0.2:
                late = min(end - 0.08, start + hold * (end - start) + 0.05)
                lower = False if mask else _lower_strip(path, late, width, height)
                softness = _softness(path, late, width, height) or softness
                shade = _shade(path, late, width, height) or shade
                bloom = 0.0 if softness else (_bloom(path, late, width, height) or bloom)
                if not (lower or softness or shade or bloom):
                    hold = 0.0
                    left = 1.0
            else:
                hold = 0.0
                left = 1.0
            release = left
        elif lower and left < 0.98:
            release = left
    edge = _level(path, f'crop={width}:{height}:0:0', min(start + 0.02, max(start, end - 0.08)))
    middle = _level(path, f'crop={width}:{height}:0:0', (start + end) / 2)
    return {
        'zoom': zoom,
        'zoom_end': zoom_end if abs(zoom_end - zoom) >= 0.1 else None,
        'x': x,
        'x_end': x_end if abs(x_end - x) >= 0.2 else None,
        'y': y,
        'y_end': y_end if abs(y_end - y) >= 0.2 else None,
        'split': (not mask) and abs(left - right) >= 28 and abs(mid - (left + right) / 2) <= 14,
        'graphic': (not mask) and mid >= left + 22 and mid >= right + 22,
        'mask': mask,
        'lower': lower,
        'fade': edge is not None and middle is not None and middle - edge >= 22,
        'join': _join(path, float(start)),
        'vignette': shade > 0,
        'shade': shade,
        'blur': softness,
        'glow': bloom,
        'hold': hold,
        'release': release,
        'screen': screen,
        'bezel': bezel,
        'fraction': fraction,
        'tiles': _tiles(path, stamp, width, height),
    }

def _tiles(path, at, width, height):
    """How many of the four equal illustration slots are brighter than the corner."""
    if width < 90 or height < 90:
        return 0
    corner = _level(path, 'crop=16:16:0:0', at)
    if corner is None:
        return 0
    count = 0
    for x, y in ((0.18, 0.32), (0.56, 0.32), (0.18, 0.58), (0.56, 0.58)):
        left = min(width - 16, int(width * (x + 0.08)))
        top = min(height - 16, int(height * (y + 0.05)))
        sample = _level(path, f'crop=16:16:{left}:{top}', at)
        if sample is not None and sample >= corner + 36:
            count += 1
    return count

def _window(path, at, width, height):
    """True when the frame is the ellipse the mask filter already cuts."""
    if width < 80 or height < 80:
        return False
    side = 24
    corners = []
    for x, y in ((0, 0), (width - side, 0), (0, height - side), (width - side, height - side)):
        level = _level(path, f'crop={side}:{side}:{x}:{y}', at)
        if level is None:
            return False
        corners.append(level)
    if max(corners) > 42 or max(corners) - min(corners) > 16:
        return False
    plate = sum(corners) / 4
    center = _level(path, f'crop=40:40:{(width - 40) // 2}:{(height - 40) // 2}', at)
    inset = max(8, int(width * 0.18))
    inside = _level(path, f'crop=16:16:{max(0, width // 2 - inset)}:{(height - 16) // 2}', at)
    edge_h = max(16, height // 5)
    edge = _level(path, f'crop=12:{edge_h}:0:{(height - edge_h) // 2}', at)
    if None in (center, inside, edge):
        return False
    return center >= plate + 40 and inside >= plate + 30 and edge <= plate + 12

def _lower_strip(path, at, width, height):
    """True for a full-width lower band, and false for the thin progress bar."""
    if width < 80 or height < 80:
        return False
    thin = max(12, height // 14)
    bottom = _level(path, f'crop={width}:{thin}:0:{height - thin}', at)
    above = _level(path, f'crop={width}:{thin}:0:{max(0, height - 2 * thin)}', at)
    half = max(16, width // 2)
    bar_left = _level(path, f'crop={half}:{thin}:0:{height - thin}', at)
    bar_right = _level(path, f'crop={half}:{thin}:{width - half}:{height - thin}', at)
    if None in (bottom, above, bar_left, bar_right):
        return False
    if abs(bottom - above) >= 28 and abs(bar_left - bar_right) <= 16:
        return False
    middle = _level(path, f'crop={width}:{max(16, height // 3)}:0:{height // 3}', at)
    band = max(16, height // 5)
    lower = _level(path, f'crop={width}:{band}:0:{height - band}', at)
    return middle is not None and lower is not None and abs(middle - lower) >= 40

def _screen(path, at, width, height):
    if width < 120 or height < 120:
        return False
    bw, bh = max(8, width // 12), max(8, height // 12)
    borders = []
    for crop in (f'crop={width}:{bh}:0:0', f'crop={width}:{bh}:0:{height - bh}', f'crop={bw}:{height}:0:0', f'crop={bw}:{height}:{width - bw}:0'):
        level = _level(path, crop, at)
        if level is None:
            return False
        borders.append(level)
    if max(borders) - min(borders) > 40:
        return False
    border = sum(borders) / 4
    inner_w, inner_h = width - 4 * bw, height - 4 * bh
    quarter = max(8, inner_w // 4)
    left = _level(path, f'crop={quarter}:{inner_h}:{2 * bw}:{2 * bh}', at)
    right = _level(path, f'crop={quarter}:{inner_h}:{2 * bw + inner_w - quarter}:{2 * bh}', at)
    if left is None or right is None:
        return False
    return left - border >= 22 and right - border >= 22

def _bezel(path, at, width, height):
    """Fraction of the frame taken by the dark border around a screen."""
    edge = _level(path, f'crop={max(8, width // 12)}:{max(8, height // 12)}:0:0', at)
    if edge is None:
        return 0.1
    band = max(12, height // 8)
    top = (height - band) // 2
    for frac in (0.06, 0.10, 0.14, 0.18, 0.24):
        x = min(width - 12, int(width * frac))
        sample = _level(path, f'crop=12:{band}:{x}:{top}', at)
        if sample is not None and sample >= edge + 22:
            return round(frac, 2)
    return 0.1

def _shade(path, at, width, height):
    """Vignette angle from how much darker the corners are than the center."""
    if width < 80 or height < 80:
        return 0.0
    side = 24
    center = _level(path, f'crop=40:40:{(width - 40) // 2}:{(height - 40) // 2}', at)
    if center is None or center < 40:
        return 0.0
    corners = []
    for x, y in ((0, 0), (width - side, 0), (0, height - side), (width - side, height - side)):
        level = _level(path, f'crop={side}:{side}:{x}:{y}', at)
        if level is None:
            return 0.0
        corners.append(level)
    depth = center - max(corners)
    if depth < 18:
        return 0.0
    return round(min(1.35, 0.4 + (depth - 18) / 90), 3)

def _softness(path, at, width, height):
    """Blur sigma when the frame still has range but its edges are weak."""
    if width < 80 or height < 80:
        return 0.0
    full = _stats(path, f'trim=start={max(0, at):.3f}:duration=0.08,signalstats,metadata=print:file=-', frames=1)
    edges = _stats(path, f'trim=start={max(0, at):.3f}:duration=0.08,convolution="0 -1 0 -1 4 -1 0 -1 0",signalstats,metadata=print:file=-', frames=1)
    if not full or not edges or not full.get('spread') or edges.get('y') is None:
        return 0.0
    if full['spread'] < 40 or edges['y'] >= 0.7:
        return 0.0
    return round(min(8.0, max(1.2, (0.7 - edges['y']) * 12)), 2)

def _bloom(path, at, width, height):
    """Unsharp amount when a bright core has a lifted ring and the corners stay dark."""
    if width < 90 or height < 90:
        return 0.0
    cx, cy = (width - 12) // 2, (height - 12) // 2
    origin = min(width - 8, (width // 2) + max(24, int(width * 0.23)))
    center = _level(path, f'crop=12:12:{cx}:{cy}', at)
    ring = _level(path, f'crop=8:8:{origin}:{(height - 8) // 2}', at)
    corner = _level(path, 'crop=16:16:0:0', at)
    if None in (center, ring, corner):
        return 0.0
    if center < 100 or ring < corner + 18 or center < ring + 25:
        return 0.0
    return round(min(1.4, max(0.4, (ring - corner) / 50)), 2)

def pace_of(path, start, end):
    """Name a speed change only when the two halves of a shot move differently."""
    span = end - start
    if span < 0.8:
        return None
    window = span * 0.34
    early = _stats(path, f'trim=start={max(0, start):.3f}:duration={window:.3f},signalstats,metadata=print:file=-', frames=4)
    late = _stats(path, f'trim=start={max(0, end - window):.3f}:duration={window:.3f},signalstats,metadata=print:file=-', frames=4)
    if not early or not late or early.get('ydif') is None or late.get('ydif') is None:
        return None
    opening, closing = early['ydif'], late['ydif']
    if closing >= opening + 3 and closing >= max(1, opening) * 1.4:
        return 1.0, 1.45
    if opening >= closing + 3 and opening >= max(1, closing) * 1.4:
        return 1.45, 0.8
    return None

def title_motion(path, start, end):
    """When a bright upper-band mark appears, slides, and leaves. Positions are fractions, not pixels."""
    meta = media.probe(path)
    width, height = int(meta['width']), int(meta['height'])
    span = float(end) - float(start)
    if width < 80 or height < 80 or span < 0.6:
        return None
    cols = 4
    col_w = max(16, width // cols)
    band_h = max(16, height // 5)
    band_y = min(height - band_h, max(0, int(height * 0.08)))
    stamps = (0.12, 0.32, 0.52, 0.72, 0.9)
    grid = []
    for frac in stamps:
        at = float(start) + span * frac
        scores = []
        for index in range(cols):
            left = min(width - col_w, index * col_w)
            level = _level(path, f'crop={col_w}:{band_h}:{left}:{band_y}', at)
            scores.append(0 if level is None else level)
        grid.append(scores)
    present = [index for index, scores in enumerate(grid) if max(scores) - min(scores) >= 22 and max(scores) >= 36]
    if not present:
        return None
    first, last = present[0], present[-1]

    def center(scores):
        peak = max(range(cols), key=lambda index: scores[index])
        return round(min(0.92, max(0.08, (peak + 0.5) / cols)), 2)

    x0, x1 = center(grid[first]), center(grid[last])
    y = round(min(0.85, max(0.08, (band_y + band_h / 2) / height)), 2)
    entered, left = first > 0, last < len(grid) - 1
    if not (entered or left or abs(x1 - x0) >= 0.15):
        return None
    return {'in': round(stamps[first], 2), 'out': round(max(stamps[first] + 0.12, stamps[last]), 2), 'x0': x0, 'y0': y, 'x1': x1, 'y1': y}

def highlight_moments(path, start, end):
    """Fractions of a shot where a short local bright or saturated patch pops, then is gone in the neighbor sample."""
    meta = media.probe(path)
    width, height = int(meta['width']), int(meta['height'])
    span = float(end) - float(start)
    if width < 48 or height < 48 or span < 0.45:
        return []
    stamps = (0.2, 0.35, 0.5, 0.65, 0.8)

    def frame_at(frac):
        at = float(start) + span * frac
        return _stats(path, f'trim=start={max(0, at):.3f}:duration=0.06,signalstats,metadata=print:file=-', frames=1)

    frames = [frame_at(frac) for frac in stamps]
    cols = rows = 3
    cell_w, cell_h = max(12, width // cols), max(12, height // rows)
    found = []

    def cell(frac, col, row):
        at = float(start) + span * frac
        x = min(width - cell_w, col * (width // cols))
        y = min(height - cell_h, row * (height // rows))
        sample = _stats(path, f'trim=start={max(0, at):.3f}:duration=0.06,crop={cell_w}:{cell_h}:{x}:{y},signalstats,metadata=print:file=-', frames=1)
        if not sample:
            return 0.0, 0.0
        return sample['y'], sample.get('sat') or 0.0

    for index, frac in enumerate(stamps):
        now = frames[index]
        neighbors = [(i, frames[i]) for i in (index - 1, index + 1) if 0 <= i < len(frames) and frames[i]]
        if not now or not neighbors:
            continue
        ceiling = now['y'] if now.get('ymax') is None else now['ymax']
        sat_peak = now.get('satmax') or 0
        # A small patch lifts the maximum without moving the percentile spread.
        local_span = ceiling >= now['y'] + 36 or sat_peak >= (now.get('sat') or 0) + 24
        popped = local_span and all(
            ceiling >= (item['y'] if item.get('ymax') is None else item['ymax']) + 28
            or sat_peak >= (item.get('satmax') or 0) + 18
            or (now.get('spread') or 0) >= (item.get('spread') or 0) + 16
            for _i, item in neighbors
        )
        if not popped:
            continue
        scores = [cell(frac, col, row) for row in range(rows) for col in range(cols)]
        peak = max(range(len(scores)), key=lambda i: scores[i][0] + 0.5 * scores[i][1])
        bright, chroma = scores[peak]
        others = [scores[i] for i in range(len(scores)) if i != peak]
        local = bright >= min(item[0] for item in others) + 22 or chroma >= min(item[1] for item in others) + 16
        if not local:
            continue
        col, row = peak % cols, peak // cols
        absent = all(
            bright >= cell(stamps[i], col, row)[0] + 18 or chroma >= cell(stamps[i], col, row)[1] + 14
            for i, _item in neighbors
        )
        if absent:
            found.append(round(frac, 2))
    return found

def _layout_bar(path, at, width, height):
    """A thin full-width bar, the same measurement as the reference layout bar."""
    band = max(12, height // 14)
    bottom = _level(path, f'crop={width}:{band}:0:{height - band}', at)
    above = _level(path, f'crop={width}:{band}:0:{max(0, height - 2 * band)}', at)
    half = max(16, width // 2)
    bar_left = _level(path, f'crop={half}:{band}:0:{height - band}', at)
    bar_right = _level(path, f'crop={half}:{band}:{width - half}:{height - band}', at)
    if None in (bottom, above, bar_left, bar_right):
        return False
    return abs(bottom - above) >= 28 and abs(bar_left - bar_right) <= 16

def card_moment(path, start, end):
    """Fraction of the shot where a bright center card or layout bar is on screen. A flat frame is not a card."""
    meta = media.probe(path)
    width, height = int(meta['width']), int(meta['height'])
    span = float(end) - float(start)
    if width < 80 or height < 80 or span < 0.6:
        return None
    stamps = (0.12, 0.32, 0.50, 0.68, 0.88)
    present = []
    for frac in stamps:
        at = float(start) + span * frac
        left, mid, right = _bands(path, at, width, height)
        center = mid >= left + 22 and mid >= right + 22
        if center or _layout_bar(path, at, width, height):
            present.append(frac)
    if not present:
        return None
    opened = round(present[0], 2)
    # The last sample is still a card, so the exit was not measured.
    closed = 1.0 if present[-1] == stamps[-1] else round(present[-1], 2)
    if closed <= opened:
        closed = 1.0
    if closed <= opened:
        return None
    return {'in': opened, 'out': closed}

def _band_luma(path, start, end, crop, count):
    span = max(0.2, float(end) - float(start))
    count = max(4, min(40, int(count)))
    fps = count / span
    vf = f'trim=start={max(0, float(start)):.3f}:duration={span:.3f},setpts=PTS-STARTPTS,fps={fps:.4f},{crop},signalstats,metadata=print:file=-'
    out, err = media.ffmpeg('-i', path, '-vf', vf, '-frames:v', str(count), '-f', 'null', '-', timeout=180)
    return [float(item) for item in re.findall(r'signalstats\.YAVG=([\d.]+)', out + '\n' + err)]

def kinetic_appearances(path, start, end):
    """Fractions where a bright title hits the upper band. A hold is one onset, not every bright frame."""
    meta = media.probe(path)
    width, height = int(meta['width']), int(meta['height'])
    span = float(end) - float(start)
    if width < 80 or height < 80 or span < 0.45:
        return []
    band_h = max(16, height // 5)
    band_y = min(height - band_h, max(0, int(height * 0.08)))
    lower_y = min(height - band_h, max(band_y + band_h, int(height * 0.62)))
    count = max(8, min(40, int(round(span * 10))))
    upper = _band_luma(path, start, end, f'crop={width}:{band_h}:0:{band_y}', count)
    lower = _band_luma(path, start, end, f'crop={width}:{band_h}:0:{lower_y}', count)
    samples = min(len(upper), len(lower), count)
    if samples < 4:
        return []
    hot = [upper[i] >= 72 and upper[i] >= lower[i] + 32 for i in range(samples)]
    for index in range(1, samples - 1):
        if not hot[index] and hot[index - 1] and hot[index + 1]:
            hot[index] = True
    runs = []
    index = 0
    while index < samples:
        if not hot[index]:
            index += 1
            continue
        runs.append(index)
        while index < samples and hot[index]:
            index += 1
    if len(runs) == 1 and runs[0] == 0 and hot[-1]:
        return []
    return [round(min(0.98, item / count), 2) for item in runs[:8]]

def callout_window(path, start, end):
    """Entrance and exit fractions for a small side or lower chip. None when no chip appears after the open."""
    span = float(end) - float(start)
    if span < 0.8:
        return 0.0
    meta = media.probe(path)
    width, height = int(meta['width']), int(meta['height'])
    if width < 80 or height < 80:
        return 0.0
    fps, limit = 5, 10

    def box(x, y, pw, ph):
        left = min(width - 12, max(0, int(width * x)))
        top = min(height - 12, max(0, int(height * y)))
        cw = max(12, min(width - left, int(width * pw)))
        ch = max(12, min(height - top, int(height * ph)))
        return f'crop={cw}:{ch}:{left}:{top}', pw * ph

    full = _series(path, start, end, f'crop={width}:{height}:0:0', fps, limit)
    if len(full) < 4:
        return 0.0
    # Side and lower chips only. The upper band belongs to title motion.
    patches = ((0.02, 0.36, 0.24, 0.26), (0.74, 0.36, 0.24, 0.26), (0.04, 0.68, 0.28, 0.22), (0.68, 0.68, 0.28, 0.22))
    series, areas = [], []
    for x, y, pw, ph in patches:
        crop, area = box(x, y, pw, ph)
        levels = _series(path, start, end, crop, fps, limit)
        if len(levels) < 4:
            return 0.0
        series.append(levels)
        areas.append(area)
    count = min(len(full), *(len(row) for row in series))
    if count < 4:
        return None
    first = last = None
    for index in range(1, count):
        if full[index] - full[0] >= 18:
            if first is not None:
                break
            continue
        hot = []
        for region, levels in enumerate(series):
            if levels[0] >= full[0] + 28:
                continue
            if levels[index] >= levels[0] + 36 and levels[index] >= full[index] + 22:
                hot.append(region)
        if not hot or len(hot) > 2 or sum(areas[region] for region in hot) > 0.22:
            if first is not None:
                break
            continue
        if first is None:
            first = index
        last = index
    if first is None:
        return None
    opened = round(min(0.98, (first / fps) / span), 2)
    if last >= count - 1:
        closed = 1.0
    else:
        closed = round(min(1.0, ((last + 1) / fps) / span), 2)
        if closed <= opened:
            closed = min(1.0, round(opened + 0.08, 2))
    return {'in': opened, 'out': closed}

def _place_point(cells, cols, rows):
    xs = [(col + 0.5) / cols for _row, col in cells]
    ys = [(row + 0.5) / rows for row, _col in cells]
    return {
        'x': round(min(0.96, max(0.04, sum(xs) / len(xs))), 2),
        'y': round(min(0.96, max(0.04, sum(ys) / len(ys))), 2),
    }

def _classify_places(hot, cols, rows):
    """One measured center each for a solid card, a full-width plate or small chip, and separated bars."""
    cells = [(row, col) for row in range(rows) for col in range(cols) if hot[row][col]]
    if not cells or len(cells) > cols * rows * 0.8:
        return None
    found = {}
    full_rows = [row for row in range(rows) if sum(hot[row]) == cols]
    band = full_rows and len(full_rows) <= 2 and full_rows[-1] - full_rows[0] + 1 == len(full_rows)
    if band:
        group = [cell for cell in cells if cell[0] in full_rows]
        others = [cell for cell in cells if cell[0] not in full_rows]
        if group and len(others) <= 1:
            found['lower_place'] = _place_point(group, cols, rows)
            cells = others
    hot_rows = sorted({row for row, _col in cells})
    gaps = any(hot_rows[index + 1] - hot_rows[index] > 1 for index in range(len(hot_rows) - 1))
    partial = bool(hot_rows) and all(sum(hot[row]) < cols for row in hot_rows)
    if gaps and len(hot_rows) >= 2 and partial:
        found['chart_place'] = _place_point(cells, cols, rows)
        cells = []
    if len(cells) <= 2 and cells and 'lower_place' not in found:
        found['lower_place'] = _place_point(cells, cols, rows)
        cells = []
    if cells:
        used_rows = {row for row, _col in cells}
        used_cols = {col for _row, col in cells}
        box = len(used_rows) * len(used_cols)
        solid = box and len(cells) / box >= 0.65 and max(used_rows) - min(used_rows) + 1 == len(used_rows)
        wide_band = len(used_cols) == cols and len(used_rows) <= 2
        if solid and not wide_band:
            found['card_place'] = _place_point(cells, cols, rows)
    return found or None

def graphic_places(path, start, end):
    """Centers of a card, an icon/lower plate, and a bar chart, as frame fractions.

    A flat frame and a full-frame fill have no position. Fractions only: the reference picture is not returned.
    """
    meta = media.probe(path)
    width, height = int(meta['width']), int(meta['height'])
    span = float(end) - float(start)
    if width < 80 or height < 80 or span < 0.4:
        return None
    at = float(start) + span * 0.5
    sample = _stats(path, f'trim=start={max(0, at):.3f}:duration=0.08,signalstats,metadata=print:file=-', frames=1)
    if not sample or (sample.get('spread') or 0) < 24:
        return None
    cols, rows = 4, 6
    cell_w, cell_h = max(8, width // cols), max(8, height // rows)
    grid = []
    for row in range(rows):
        line = []
        for col in range(cols):
            left = min(width - cell_w, col * (width // cols))
            top = min(height - cell_h, row * (height // rows))
            level = _level(path, f'crop={cell_w}:{cell_h}:{left}:{top}', at)
            line.append(0.0 if level is None else level)
        grid.append(line)
    floor = min(value for line in grid for value in line)
    hot = [[value >= 80 and value >= floor + 36 for value in line] for line in grid]
    return _classify_places(hot, cols, rows)

def callout_at(path, start, end):
    """Fraction of the shot where a small side or lower chip appears. A flat frame, a full-frame card, or a chip already present at the open is 0."""
    window = callout_window(path, start, end)
    if not isinstance(window, dict):
        return 0.0
    return float(window['in'])

def annotate_pictures(path, shots):
    for shot in list(shots or [])[:6]:
        try:
            shot['picture'] = picture_of(path, float(shot['start']), float(shot['end']))
        except Exception:
            shot['picture'] = None
        picture = shot.get('picture')
        if not isinstance(picture, dict):
            continue
        try:
            pace = pace_of(path, float(shot['start']), float(shot['end']))
        except Exception:
            pace = None
        if pace:
            picture['speed'], picture['speed_end'] = pace
        try:
            motion = title_motion(path, float(shot['start']), float(shot['end']))
        except Exception:
            motion = None
        if motion:
            picture['title'] = motion
        try:
            pops = highlight_moments(path, float(shot['start']), float(shot['end']))
        except Exception:
            pops = []
        if pops:
            picture['highlights'] = pops
            picture['emphasis'] = {'in': pops[0], 'out': round(min(1.0, float(pops[-1]) + 0.15), 2)}
        try:
            moment = card_moment(path, float(shot['start']), float(shot['end']))
        except Exception:
            moment = None
        if moment:
            picture['card'] = moment
        try:
            appearances = kinetic_appearances(path, float(shot['start']), float(shot['end']))
        except Exception:
            appearances = []
        if appearances:
            picture['kinetic_at'] = appearances
        try:
            window = callout_window(path, float(shot['start']), float(shot['end']))
        except Exception:
            window = None
        if isinstance(window, dict):
            picture['callout'] = float(window['in'])
            if float(window['out']) < 0.999:
                picture['callout_out'] = float(window['out'])
        else:
            picture['callout'] = 0.0
        try:
            places = graphic_places(path, float(shot['start']), float(shot['end']))
        except Exception:
            places = None
        if isinstance(places, dict):
            for key in ('card_place', 'lower_place', 'chart_place'):
                if isinstance(places.get(key), dict):
                    picture[key] = places[key]
    return shots

def measure(path):
    meta = media.probe(path)
    shots = scene_shots(path, meta['duration'])
    annotate_pictures(path, shots)
    return {
        'duration': meta['duration'],
        'shots': shots,
        'color': color_sample(path),
        'flat': flat_background(path),
    }
