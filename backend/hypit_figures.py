"""Draw every figure for one spoken line into one clip. The next project gets a new set."""
import glob
import json
import os
import subprocess
import sys

BG = (9, 9, 11, 255)
CREAM = (244, 241, 232, 255)
INK = (22, 54, 44, 255)
MINT = (125, 255, 195, 255)
PURPLE = (122, 92, 255, 255)
GOLD = (226, 194, 122, 255)
SCENE = (48, 86, 140, 255)
SEAL = (176, 48, 48, 255)
FPS = 30
_FONTS = {}


def _font(size, text=''):
    size = int(size)
    cyrillic = any('\u0400' <= char <= '\u04FF' for char in str(text or ''))
    key = (size, 'cyr' if cyrillic else 'cjk')
    cached = _FONTS.get(key)
    if cached is not None:
        return cached
    if cyrillic:
        candidates = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf',
            '/usr/share/fonts/noto/NotoSans-Bold.ttf',
            '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
            '/System/Library/Fonts/Supplemental/Arial.ttf',
            '/Library/Fonts/Arial Bold.ttf',
        ]
    else:
        candidates = [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc',
            '/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            '/System/Library/Fonts/STHeiti Medium.ttc',
        ]
    from PIL import ImageFont
    font = None
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            font = ImageFont.truetype(path, size, index=2)
        except OSError:
            font = ImageFont.truetype(path, size)
        break
    if font is None:
        font = ImageFont.load_default()
    _FONTS[key] = font
    return font


def _ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _reveal(index, total, step, count):
    """Arrival of one step. The last step reaches the end of the phrase, not the first second."""
    count = max(1, int(count))
    progress = 1.0 if total <= 1 else index / (total - 1)
    start = 0.0 if step <= 0 else step / count
    length = 0.85 / count
    if progress <= start:
        return 0.0
    return _ease(min(1.0, (progress - start) / length))


def _travel(t, duration):
    """Visible by half a second, still moving at the end of the phrase."""
    duration = max(1.0, float(duration))
    t = max(0.0, min(duration, float(t)))
    if duration <= 0.5:
        return _ease(t / duration)
    if t <= 0.5:
        return 0.35 * (t / 0.5)
    rest = (t - 0.5) / (duration - 0.5)
    return 0.35 + 0.65 * _ease(min(1.0, rest))


def _step_labels(parts):
    labels = [' '.join(str(part).split()) for part in parts if str(part).strip()]
    if len(labels) >= 2:
        return labels
    if not labels:
        return []
    words = labels[0].split()
    if len(words) < 2:
        return [labels[0]]
    mid = max(1, len(words) // 2)
    left, right = ' '.join(words[:mid]), ' '.join(words[mid:])
    return [left or labels[0], right or labels[0]]


def _step_start(step, count, duration):
    """The first two cards arrive before half a second. Later cards follow across the phrase."""
    duration = max(1.0, float(duration))
    count = max(1, int(count))
    if step <= 0 or count == 1:
        return 0.0
    early = min(0.22, duration * 0.15)
    if step == 1:
        return early
    last = min(duration * 0.75, max(1.5, duration - 0.6))
    first = min(1.2, last)
    later_count = count - 2
    if later_count <= 1:
        return min(last, max(1.25, duration * 0.42))
    return first + (last - first) * ((step - 2) / (later_count - 1))


def _percent(number):
    text = str(number or '')
    if not text.endswith('%'):
        return None
    try:
        return max(0.0, min(1.0, float(text[:-1]) / 100.0))
    except ValueError:
        return None


def scene_state(shot, t):
    """What one phrase shows at t seconds. Labels stay spoken words or step counts."""
    duration = max(1.0, float(shot.get('span') or 1))
    t = max(0.0, min(duration, float(t)))
    steps = _step_labels(shot.get('parts') or [])
    number = str(shot.get('number') or '')
    visible = []
    for index, label in enumerate(steps):
        if t + 1e-6 >= _step_start(index, len(steps), duration):
            visible.append(label)
    if number:
        figure = number
        ticks = [number]
        dest = _percent(number)
    else:
        # A step count is not a spoken number. The big digit stays empty.
        figure = ''
        ticks = []
        dest = None
    fragment_s = float(shot.get('fragment_s') or min(5.0, duration))
    fragment_s = max(0.2, min(5.0, fragment_s))
    return {
        'travel': _travel(t, duration),
        'arrow': shot.get('arrow') or 'across',
        'ticks': ticks,
        'dest': dest,
        'columns': (steps[0], steps[1] if len(steps) > 1 else steps[0]) if steps else ('', ''),
        'figure': figure,
        'steps': visible,
        'link': _travel(t, duration) if len(visible) >= 2 else 0.0,
        'fragment': (shot.get('motif') or 'path') if t <= fragment_s + 0.2 else None,
        'fragment_label': shot.get('fragment_label') or '',
        'fragment_p': min(1.0, t / fragment_s) if fragment_s else 1.0,
        'format': shot.get('format') or shot.get('kind') or 'type',
    }


def _words(text):
    return str(text or '').split()


def _text_width(draw, text, font):
    if not text:
        return 0
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _wrap(text, limit=10):
    """Break only on spaces. A word longer than the limit stays on its own line."""
    words = _words(text)
    if not words:
        return []
    lines = []
    current = []
    for word in words:
        trial = ' '.join(current + [word])
        if current and len(trial) > max(1, int(limit)):
            lines.append(' '.join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(' '.join(current))
    return lines


def _pack(draw, words, font, width):
    lines = []
    current = []
    for word in words:
        trial = ' '.join(current + [word])
        if current and _text_width(draw, trial, font) > width:
            lines.append(' '.join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(' '.join(current))
    return lines


def _center(draw, text, box, fill, size, fit_chars=4):
    """Shrink, then grow the box, then wrap. A line never contains part of a word."""
    del fit_chars
    words = _words(text)
    if not words:
        return
    x0, y0, x1, y1 = [int(round(float(v))) for v in box]
    pad_x, pad_y = 12, 6
    inner_w = max(8, (x1 - x0) - pad_x * 2)
    inner_h = max(8, (y1 - y0) - pad_y * 2)
    size = max(12, int(size))
    font = _font(size, text)
    lines = _pack(draw, words, font, inner_w)

    def _overflow():
        widest = max(_text_width(draw, word, font) for word in words)
        line_h = max(1, int(round(size * 1.2)))
        block = line_h * len(lines)
        return widest > inner_w or block > inner_h

    while size > 12 and _overflow():
        size -= 2
        font = _font(size, text)
        lines = _pack(draw, words, font, inner_w)
    widest = max(_text_width(draw, word, font) for word in words)
    if widest > inner_w:
        grow = widest - inner_w + 8
        x0 -= grow // 2
        x1 += grow - grow // 2
        inner_w = widest + 8
        lines = _pack(draw, words, font, inner_w)
    line_h = max(1, int(round(size * 1.2)))
    block = line_h * len(lines)
    if block + pad_y * 2 > (y1 - y0):
        grow = block + pad_y * 2 - (y1 - y0)
        y0 -= grow // 2
        y1 += grow - grow // 2
    y = y0 + max(pad_y, ((y1 - y0) - block) / 2)
    for line in lines:
        if any(piece not in words for piece in line.split()):
            raise RuntimeError('mid-word wrap')
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        draw.text((x0 + (x1 - x0 - tw) / 2, y - bbox[1]), line, font=font, fill=fill)
        y += line_h


def _arrow(draw, x0, y0, x1, y1, amount):
    if amount <= 0.02:
        return
    x = x0 + (x1 - x0) * amount
    y = y0 + (y1 - y0) * amount
    draw.line((x0, y0, x, y), fill=GOLD, width=6)
    dx, dy = x1 - x0, y1 - y0
    length = max(1.0, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    tip = 16
    draw.polygon([
        (x + ux * tip, y + uy * tip),
        (x - ux * 4 + px * 9, y - uy * 4 + py * 9),
        (x - ux * 4 - px * 9, y - uy * 4 - py * 9),
    ], fill=MINT)


def _card(base, box, fill, outline):
    from PIL import ImageDraw
    x0, y0, x1, y1 = [int(v) for v in box]
    if x1 - x0 < 24 or y1 - y0 < 24:
        return base
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle((x0 + 4, y0 + 6, x1 + 4, y1 + 6), radius=14, fill=(0, 0, 0, 70))
    draw.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=fill, outline=outline, width=3)
    return base


def _blank(width, height):
    from PIL import Image
    return Image.new('RGBA', (width, height), BG)


def _region(width, height, box):
    x0, y0, x1, y1 = box
    return (int(width * x0), int(height * y0), int(width * x1), int(height * y1))


def _fragment(draw, box, state):
    motif = state['fragment']
    if not motif:
        return
    x0, y0, x1, y1 = box
    progress = state['fragment_p']
    draw.rounded_rectangle((x0, y0, x1, y1), radius=16, fill=SCENE)
    label = state['fragment_label']
    if motif == 'documents':
        shift = int(22 * progress)
        draw.rounded_rectangle((x0 + 18, y0 + 28, x1 - 36, y1 - 18), radius=6, fill=CREAM)
        draw.rounded_rectangle((x0 + 18 + shift, y0 + 16, x1 - 36 + shift // 2, y1 - 30), radius=6, fill=(255, 250, 240, 255), outline=GOLD, width=2)
    elif motif == 'stamp':
        draw.rounded_rectangle((x0 + 16, y0 + 22, x1 - 16, y1 - 14), radius=6, fill=CREAM)
        radius = max(16, (y1 - y0) // 5)
        cx = (x0 + x1) // 2
        cy = y0 + 20 + int((y1 - y0 - 36) * progress)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=SEAL, width=5)
    elif motif == 'doorway':
        draw.rectangle((x0 + 18, y0 + 16, x1 - 18, y1 - 12), outline=GOLD, width=4)
        door = int((x1 - x0 - 44) * (1 - 0.7 * progress))
        draw.rectangle((x0 + 22, y0 + 20, x0 + 22 + max(12, door), y1 - 16), fill=(24, 48, 86, 255))
    else:
        _arrow(draw, x0 + 16, y1 - 28, x1 - 20, y0 + 24, max(0.2, progress))
    if label:
        _center(draw, label, (x0 + 8, y1 - 36, x1 - 8, y1 - 4), CREAM, 18)


def _scale(draw, box, state):
    x0, y0, x1, y1 = box
    mid = (y0 + y1) // 2
    draw.rounded_rectangle((x0, mid - 14, x1, mid + 14), radius=12, fill=(8, 32, 28, 255), outline=MINT, width=3)
    dest = 1.0 if state['dest'] is None else state['dest']
    fill = max(0.04, state['travel'] * dest)
    end = x0 + int((x1 - x0) * fill)
    if end > x0 + 8:
        draw.rounded_rectangle((x0 + 4, mid - 10, end, mid + 10), radius=8, fill=MINT)
    ticks = state['ticks'] or []
    span = max(1, len(ticks))
    for index, label in enumerate(ticks):
        if state['dest'] is not None:
            at = x0 + int((x1 - x0) * state['dest'])
        else:
            at = x0 + int((x1 - x0) * ((index + 1) / span))
        draw.line((at, mid - 18, at, mid + 16), fill=GOLD, width=3)
        font = _font(18, label)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        draw.text((at - tw / 2, mid + 18 - bbox[1]), label, font=font, fill=CREAM)


def _moving_arrow(draw, box, state):
    x0, y0, x1, y1 = box
    way = state['arrow']
    amount = state['travel']
    if way == 'down':
        _arrow(draw, (x0 + x1) / 2, y0 + 8, (x0 + x1) / 2, y1 - 8, amount)
    elif way == 'up':
        _arrow(draw, (x0 + x1) / 2, y1 - 8, (x0 + x1) / 2, y0 + 8, amount)
    else:
        _arrow(draw, x0 + 8, (y0 + y1) / 2, x1 - 8, (y0 + y1) / 2, amount)


def _line(state):
    steps = [label for label in (state.get('steps') or []) if str(label).strip()]
    if steps:
        return steps[0]
    return state.get('fragment_label') or ''


def _title_card(base, draw, box, text, size):
    _card(base, box, (18, 24, 32, 255), MINT)
    _center(draw, text, box, CREAM, size)
    return base


def _paint_type(base, state, width, height):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(base)
    steps = state['steps'] or [_line(state)]
    _title_card(base, draw, _region(width, height, (0.08, 0.14, 0.72, 0.36)), steps[0], int(width * 0.07))
    _moving_arrow(draw, _region(width, height, (0.14, 0.40, 0.70, 0.54)), state)
    if len(steps) > 1:
        _title_card(base, draw, _region(width, height, (0.22, 0.58, 0.92, 0.78)), steps[1], int(width * 0.06))
    _scale(draw, _region(width, height, (0.1, 0.84, 0.9, 0.93)), state)
    return base


def _paint_number(base, state, width, height):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(base)
    if state['figure']:
        _center(draw, state['figure'], _region(width, height, (0.08, 0.1, 0.7, 0.42)), MINT, int(width * 0.22))
    _title_card(base, draw, _region(width, height, (0.1, 0.46, 0.9, 0.66)), _line(state), int(width * 0.06))
    _scale(draw, _region(width, height, (0.1, 0.74, 0.9, 0.86)), state)
    return base


def _paint_flow(base, state, width, height):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(base)
    steps = state['steps'] or [_line(state)]
    count = max(1, len(steps))
    top, bottom = int(height * 0.12), int(height * 0.72)
    x = int(width * 0.18)
    span = max(1, bottom - top)
    for index, label in enumerate(steps):
        y = top + int(span * (index + 0.5) / count)
        if index:
            draw.line((x, top + int(span * (index - 0.5) / count), x, y), fill=GOLD, width=4)
        draw.ellipse((x - 14, y - 14, x + 14, y + 14), fill=MINT)
        _center(draw, label, (x + 28, y - 36, int(width * 0.9), y + 36), CREAM, 28)
    _scale(draw, _region(width, height, (0.1, 0.82, 0.9, 0.92)), state)
    return base


def _paint_object(base, state, width, height):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(base)
    _moving_arrow(draw, _region(width, height, (0.12, 0.18, 0.72, 0.38)), state)
    _title_card(base, draw, _region(width, height, (0.1, 0.44, 0.9, 0.66)), _line(state), int(width * 0.07))
    _scale(draw, _region(width, height, (0.1, 0.76, 0.9, 0.88)), state)
    return base


def _paint_split(base, state, width, height):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(base)
    mid = width // 2
    left = (24, int(height * 0.18), mid - 28, int(height * 0.62))
    right = (mid + 28, int(height * 0.28), width - 24, int(height * 0.74))
    _title_card(base, draw, left, state['columns'][0], 28)
    _fragment(draw, right, state)
    _moving_arrow(draw, (mid - 36, int(height * 0.4), mid + 36, int(height * 0.52)), state)
    _scale(draw, _region(width, height, (0.1, 0.84, 0.9, 0.93)), state)
    return base


def _paint_timeline(base, state, width, height):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(base)
    steps = state['steps'] or [_line(state)]
    y = int(height * 0.36)
    x0, x1 = int(width * 0.08), int(width * 0.92)
    draw.line((x0, y, x0 + int((x1 - x0) * max(0.08, state['travel'])), y), fill=GOLD, width=6)
    count = max(1, len(steps))
    for index, label in enumerate(steps):
        at = x0 + int((x1 - x0) * (index + 0.5) / count)
        draw.ellipse((at - 12, y - 12, at + 12, y + 12), fill=MINT)
        _center(draw, label, (at - 80, y + 24, at + 80, y + 130), CREAM, 22)
    _scale(draw, _region(width, height, (0.1, 0.82, 0.9, 0.92)), state)
    return base


def _paint_minimal(base, state, width, height):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(base)
    _title_card(base, draw, _region(width, height, (0.1, 0.22, 0.78, 0.46)), _line(state), int(width * 0.07))
    _moving_arrow(draw, _region(width, height, (0.16, 0.52, 0.7, 0.66)), state)
    _scale(draw, _region(width, height, (0.1, 0.76, 0.9, 0.88)), state)
    return base


def _paint_question(base, state, width, height):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(base)
    box = _region(width, height, (0.08, 0.14, 0.78, 0.4))
    _title_card(base, draw, box, _line(state), int(width * 0.07))
    y = box[3] + 28
    end = box[0] + int((box[2] - box[0]) * max(0.15, state['travel']))
    draw.line((box[0], y, end, y), fill=GOLD, width=6)
    _scale(draw, _region(width, height, (0.1, 0.72, 0.9, 0.84)), state)
    return base


def _paint_montage(base, state, width, height):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(base)
    steps = state['steps'] or [_line(state)]
    slots = ((0.06, 0.1, 0.7, 0.3), (0.24, 0.34, 0.94, 0.54), (0.08, 0.58, 0.72, 0.78))
    shown = 1 + min(2, int(state['travel'] * 2.99))
    for label, slot in zip(steps, slots[:shown]):
        _title_card(base, draw, _region(width, height, slot), label, int(width * 0.055))
    if shown >= 2:
        _moving_arrow(draw, _region(width, height, (0.55, 0.28, 0.78, 0.4)), state)
    return base


def _paint(base, state, width, height):
    kind = state.get('format') or 'type'
    painter = {
        'number': _paint_number,
        'flow': _paint_flow,
        'object': _paint_object,
        'split': _paint_split,
        'timeline': _paint_timeline,
        'minimal': _paint_minimal,
        'question': _paint_question,
        'montage': _paint_montage,
    }.get(kind, _paint_type)
    return painter(base, state, width, height)


def frame_at(shot, width, height, t):
    base = _blank(width, height)
    return _paint(base, scene_state(shot, t), width, height)


def _save(folder, name, frames):
    stills = os.path.join(folder, name + '-frames')
    os.makedirs(stills, exist_ok=True)
    for index, frame in enumerate(frames):
        frame.convert('RGB').save(os.path.join(stills, f'{index:04d}.png'))
    dest = os.path.join(folder, name)
    subprocess.check_call([
        'ffmpeg', '-nostdin', '-y', '-framerate', str(FPS), '-i', os.path.join(stills, '%04d.png'),
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', dest,
    ], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for path in glob.glob(os.path.join(stills, '*.png')):
        os.remove(path)
    os.rmdir(stills)


def _frames(shot, width, height):
    seconds = max(1.0, float(shot['span']))
    total = max(8, int(round(seconds * FPS)))
    frames = []
    for index in range(total):
        t = 0.0 if total <= 1 else seconds * index / (total - 1)
        frames.append(frame_at(shot, width, height, t))
    return frames


def _ensure_tools():
    import shutil
    cjk = (
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc',
        '/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc',
    )
    sans = (
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf',
        '/usr/share/fonts/noto/NotoSans-Bold.ttf',
    )
    if shutil.which('ffmpeg') is None or not any(os.path.isfile(path) for path in cjk + sans):
        env = os.environ.copy()
        env['DEBIAN_FRONTEND'] = 'noninteractive'
        subprocess.check_call(['apt-get', 'update', '-qq'], env=env, stdin=subprocess.DEVNULL)
        subprocess.check_call(
            ['apt-get', 'install', '-y', '-qq', 'ffmpeg', 'fonts-noto-cjk', 'fonts-dejavu-core'],
            env=env, stdin=subprocess.DEVNULL,
        )
    try:
        import PIL  # noqa: F401
    except ImportError:
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '-q', '--break-system-packages', 'pillow'],
            stdin=subprocess.DEVNULL,
        )


def render(folder):
    plan_path = os.path.join(folder, 'motion', 'plan.json')
    if not os.path.isfile(plan_path):
        return
    plan = json.load(open(plan_path, encoding='utf-8'))
    if not plan.get('shots'):
        return
    _ensure_tools()
    width = int(plan.get('width') or 720)
    height = int(plan.get('height') or 1280)
    out = os.path.join(folder, 'motion')
    os.makedirs(out, exist_ok=True)
    for shot in plan.get('shots') or []:
        if shot.get('format') == 'speaker' or not shot.get('file'):
            continue
        _save(out, shot['file'], _frames(shot, width, height))


def _assert_whole_words():
    phrase = 'Planning a relocation'
    words = _words(phrase)
    lines = _wrap(phrase, 8) + _wrap(phrase, 4)
    bad = {'Plannin', 'relocat'}
    pieces = [piece for line in lines for piece in line.split()]
    if bad.intersection(pieces) or any(piece not in words for piece in pieces):
        raise RuntimeError('mid-word wrap')
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print('whole-words ok')
        return
    draw = ImageDraw.Draw(Image.new('RGB', (240, 120), 'white'))
    packed = _pack(draw, words, _font(36, phrase), 48)
    pieces = [piece for line in packed for piece in line.split()]
    if bad.intersection(pieces) or any(piece not in words for piece in pieces):
        raise RuntimeError('mid-word wrap')
    print('whole-words ok')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        _assert_whole_words()
    else:
        render(sys.argv[1] if len(sys.argv) > 1 else '.')
