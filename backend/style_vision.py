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
    spread = (sum(highs) / len(highs) - sum(lows) / len(lows)) if highs and lows else None
    return {
        'y': sum(ys) / len(ys),
        'u': sum(us) / len(us) if us else 128,
        'v': sum(vs) / len(vs) if vs else 128,
        'sat': sum(sats) / len(sats) if sats else None,
        'spread': spread,
        'ydif': sum(difs) / len(difs) if difs else None,
    }

def color_sample(path):
    return _stats(path, 'fps=1,signalstats,metadata=print:file=-')

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
    stamp = None
    for line in (out + '\n' + err).splitlines():
        found = re.search(r'pts_time:([\d.]+)', line)
        if found:
            stamp = float(found.group(1))
        level = re.search(r'signalstats\.YAVG=([\d.]+)', line)
        if level and stamp is not None:
            rows.append((stamp, float(level.group(1))))
            stamp = None
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

def highlight_window(path, duration):
    rows = [(stamp, level) for stamp, level in _timed_levels(path) if level >= 30]
    if not rows:
        return None
    stamp, _level = max(rows, key=lambda row: row[1])
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

def reference_layout(path):
    meta = media.probe(path)
    width, height, duration = int(meta['width']), int(meta['height']), float(meta['duration'])
    empty = {'split': False, 'bar': False, 'lower': False, 'shake': False}
    if width < 64 or height < 64:
        return empty
    at = min(0.3, max(0, duration / 3))
    half = max(16, width // 2)
    left = _level(path, f'crop={half}:{height}:0:0', at)
    right = _level(path, f'crop={half}:{height}:{width - half}:0', at)
    split = left is not None and right is not None and abs(left - right) >= 28
    band = max(12, height // 14)
    bottom = _level(path, f'crop={width}:{band}:0:{height - band}', at)
    above = _level(path, f'crop={width}:{band}:0:{max(0, height - 2 * band)}', at)
    bar_left = _level(path, f'crop={half}:{band}:0:{height - band}', at)
    bar_right = _level(path, f'crop={half}:{band}:{width - half}:{height - band}', at)
    bar = None not in (bottom, above, bar_left, bar_right) and abs(bottom - above) >= 28 and abs(bar_left - bar_right) <= 16
    middle = _level(path, f'crop={width}:{max(16, height // 3)}:0:{height // 3}', at)
    lower_band = _level(path, f'crop={width}:{max(16, height // 5)}:0:{height - max(16, height // 5)}', at)
    lower = (not bar) and middle is not None and lower_band is not None and abs(middle - lower_band) >= 40
    later = min(duration - 0.1, at + 0.24)
    first, second = _column_at(path, at), _column_at(path, later)
    shake = first is not None and second is not None and abs(first - second) >= 0.2
    return {'split': split, 'bar': bar, 'lower': lower, 'shake': shake}

def _arrived(old, now, new):
    return abs(now - new) + 12 < abs(now - old)

def _stayed(old, now, new):
    return abs(now - old) + 12 < abs(now - new)

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
    if None not in left + right and ((_arrived(*left) and _stayed(*right)) or (_arrived(*right) and _stayed(*left))):
        return 'wipe' if _arrived(*left) and _stayed(*right) else 'cut'
    crop_w, crop_h = max(16, width // 3), max(16, height // 3)
    center = [_level(path, f'crop={crop_w}:{crop_h}:{(width - crop_w) // 2}:{(height - crop_h) // 2}', stamp) for stamp in (before, at, after)]
    corner = [_level(path, 'crop=24:24:0:0', stamp) for stamp in (before, at, after)]
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

def picture_of(path, start, end):
    meta = media.probe(path)
    width, height = int(meta['width']), int(meta['height'])
    wide = {'zoom': 1.0, 'zoom_end': None, 'x': 0.5, 'x_end': None, 'y': 0.5, 'y_end': None, 'split': False, 'graphic': False, 'mask': False, 'lower': False}
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
    screen = _screen(path, stamp, width, height)
    mask = _window(path, stamp, width, height)
    lower = False if mask else _lower_strip(path, stamp, width, height)
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
        'vignette': shade > 0,
        'shade': shade,
        'blur': softness,
        'glow': 0.0 if softness else _bloom(path, stamp, width, height),
        'screen': screen,
    }

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

def annotate_pictures(path, shots):
    for shot in list(shots or [])[:6]:
        try:
            shot['picture'] = picture_of(path, float(shot['start']), float(shot['end']))
        except Exception:
            shot['picture'] = None
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
