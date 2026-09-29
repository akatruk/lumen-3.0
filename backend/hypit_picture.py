"""Style-match pictures rendered by Hypit's HyperFrames capture.

Hypit is Apache License 2.0 with additional conditions. Lumen does not vendor
that source. A style-match render writes a HyperFrames HTML programme and runs
``provider-hyperframes-local`` from ``HYPIT_ROOT`` (default ``/opt/hypit``).
The capture composites frames in Chrome and encodes them with ffmpeg. Lumen
still owns the edit, the voice, and the music bed.
"""
import html
import json
import logging
import os
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from .media import ffmpeg, run

log = logging.getLogger('lumen.hypit')
FPS = 30
FADE = 6
SCRIPT = Path(__file__).resolve().parent / 'hypit_render.mjs'
_LEAK = re.compile(
    r'(?i)(api[_-]?key|secret|token|password|authorization|bearer)\s*[:=]\s*\S+'
    r'|sk-[A-Za-z0-9]{8,}|BEGIN [A-Z ]*PRIVATE KEY'
)


def engine_for(context):
    """Style-match pictures use Hypit. Other renders keep the existing assembler."""
    if (context or {}).get('style_match'):
        return 'hypit'
    return None


def _root():
    return Path(os.environ.get('HYPIT_ROOT') or '/opt/hypit')


def command(job_path):
    """tsx's package bin is a shell shim. Node must run the JavaScript CLI."""
    root = _root()
    cli = root / 'node_modules' / 'tsx' / 'dist' / 'cli.mjs'
    node = os.environ.get('HYPIT_NODE') or 'node'
    return [node, str(cli), str(SCRIPT), str(job_path)], root, cli


def redact_capture(text):
    """Keep a short capture note. Drop credentials; the command line is never included."""
    if not text:
        return ''
    cleaned = _LEAK.sub('[redacted]', str(text)[-4000:])
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    return '\n'.join(lines[-30:])[:2000]


def _note_failure(exc, detail):
    exc.hypit_detail = redact_capture(detail) or type(exc).__name__
    return exc


def capture_note(exc):
    """Text for the worker log. Browser responses stay on the stable error code."""
    parts = []
    seen = set()
    current = exc
    while current is not None and id(current) not in seen and len(parts) < 5:
        seen.add(id(current))
        detail = getattr(current, 'hypit_detail', '')
        if detail:
            parts.append(detail)
        elif not isinstance(current, (subprocess.CalledProcessError, subprocess.TimeoutExpired)):
            text = str(current)
            if text and text != 'hypit_unavailable':
                parts.append(redact_capture(f'{type(current).__name__}: {text}')[:500])
        current = current.__cause__
    return ' | '.join(dict.fromkeys(parts))[:2000]


def spawn(argv, env):
    """Run capture with its own pipes so a worker terminal cannot drop or kill it.

    Node writes the diagnosable cause to those pipes. The parent's stdout stays
    blocking, and the command line is not kept on the exception.
    """
    work = str(Path(argv[-1]).resolve().parent)
    try:
        subprocess.run(
            argv, check=True, env=env, timeout=45 * 60, cwd=work,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors='replace',
        )
    except subprocess.CalledProcessError as exc:
        output = (exc.stderr or '').strip() or (exc.stdout or '').strip()
        raise _note_failure(exc, f'exit {exc.returncode}: {output}' if output else f'exit {exc.returncode}') from None
    except subprocess.TimeoutExpired as exc:
        raise _note_failure(exc, 'capture timed out') from None
    except OSError as exc:
        raise _note_failure(exc, f'{type(exc).__name__}: {exc.strerror or "capture could not start"}') from None


def _caption_line(caption, language):
    if str(language).startswith('zh'):
        text = caption.get('zh') or caption.get('original') or caption.get('en') or ''
    else:
        text = caption.get('en') or caption.get('original') or caption.get('zh') or ''
    text = ' '.join(str(text).split())
    if not text or text == '口播' or text.isdigit() or len(text) > 18:
        return ''
    return text


# Higher rank wins when one sentence names several facts. A headcount is a phrase, never a lone digit.
_GRAPHIC_RULES = (
    (90, ('董事', 'director'), ('董事权限', ''), ('Director authority', '')),
    (80, ('法人', 'legal representative'), ('法人代表', ''), ('Legal representative', '')),
    (70, ('实缴', 'paid-in', 'paid in'), ('实缴资本', ''), ('Paid-in capital', '')),
    (60, ('出资', 'capital schedule'), ('出资节奏', ''), ('Capital schedule', '')),
    (55, ('看的是结构', 'focuses on structure'), ('看结构', ''), ('Structure', '')),
    (50, ('股东结构', 'shareholder structure'), ('股东结构', ''), ('Shareholder structure', '')),
    (40, ('注册资本', 'registered capital'), ('注册资本', '认缴制'), ('Registered capital', 'Subscribed')),
    (35, ('股东', 'shareholder'), ('股东结构', ''), ('Shareholder structure', '')),
    (30, ('认缴', 'subscribed'), ('认缴制', ''), ('Subscribed capital', '')),
    (20, ('注册公司', 'registering', 'registration'), ('注册公司', ''), ('Company setup', '')),
)


def _graphic_copy(caption, _language):
    """One designed title from an owned sentence. A percent stays on the figure plate."""
    blob = ' '.join(str(caption.get(key) or '') for key in ('zh', 'original', 'en'))
    if not blob.strip() or '口播' in blob or re.search(r'\d+(?:\.\d+)?\s*%', blob):
        return None
    folded = blob.lower()
    best = None
    for rank, needles, zh, en in _GRAPHIC_RULES:
        if any(needle.lower() in folded for needle in needles) and (best is None or rank > best[0]):
            best = (rank, zh, en)
    if best is None:
        return None
    zh_title, _zh_sub = best[1]
    en_title, en_sub = best[2]
    # The reference sets a large Chinese line over a short English line.
    title = (zh_title or en_title).strip()
    kicker = (en_title if en_title and en_title != title else en_sub).strip()
    if not title or title.isdigit() or title == '口播':
        return None
    if kicker in {title, '口播'} or kicker.isdigit():
        kicker = ''
    return title, kicker


def _spoken_figure(caption):
    """A number the speaker actually says. Years and lone headcounts stay off the board."""
    blob = ' '.join(str(caption.get(key) or '') for key in ('zh', 'original', 'en'))
    blob = ' '.join(blob.split())
    if not blob or '口播' in blob:
        return None
    percent = re.search(r'(\d+(?:\.\d+)?)\s*[%％]', blob)
    if percent:
        return percent.group(1) + '%', '', _figure_label(blob, percent.group(0))
    found = re.search(r'(\d+(?:\.\d+)?(?:\s*[-–~至到]\s*\d+(?:\.\d+)?)?)\s*(万|千|亿)?', blob)
    if not found:
        return None
    figure = re.sub(r'\s+', '', found.group(0))
    if re.fullmatch(r'\d{4}', figure) or (figure.isdigit() and len(figure) <= 2):
        return None
    unit = next((token for token in ('泰铢', '人民币', '美元', '元', '每月', '每天', '月', '天') if token in blob), '')
    return figure, unit, _figure_label(blob, found.group(0))


def _figure_label(blob, figure):
    label = blob.replace(figure, ' ')
    label = re.sub(r'[%％]|泰铢|人民币|美元|大约|左右|约', ' ', label)
    label = ' '.join(label.split())
    if re.search(r'[\u4e00-\u9fff]', label):
        label = re.sub(r'[A-Za-z].*', '', label).strip(' ，,。.')
        return label[:12]
    words = label.split()
    return ' '.join(words[:4])[:28]


def _short_line(caption, language, limit=26):
    if str(language).startswith('zh'):
        text = caption.get('zh') or caption.get('original') or caption.get('en') or ''
    else:
        text = caption.get('en') or caption.get('original') or caption.get('zh') or ''
    text = ' '.join(str(text).split())
    if not text or text == '口播' or text.isdigit() or len(text) <= 1:
        return ''
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0].strip(' ，,。.')
    return cut or text[:limit].strip()


def _support_line(title, kicker, spoken):
    """One extra line. The title is never repeated under itself."""
    for line in (kicker, spoken):
        text = ' '.join(str(line or '').split())
        if text and text != title:
            return text
    return ''


def _lower_html(title, kicker, spoken, chapter, a, b):
    support = _support_line(title, kicker, spoken)
    support_html = f'<div class="hf-lower-kicker">{html.escape(support)}</div>' if support else ''
    number = f'<b>{int(chapter):02d}</b>' if chapter else ''
    return (
        f'<aside class="hf-lower" data-hypit-start-frame="{a}" data-hypit-end-frame="{b}" '
        f'data-hf-fade-in="6" data-hf-fade-out="6">'
        f'<div class="hf-lower-head">{number}<span>{html.escape(title)}</span></div>'
        f'<i class="hf-lower-bar"></i>{support_html}</aside>'
    )


def _board_html(title, figure, unit, note, chapter, a, b):
    unit_html = f'<div class="hf-board-unit">{html.escape(unit)}</div>' if unit else ''
    label = title or _support_line('', note, '') or ''
    note_html = f'<div class="hf-board-note">{html.escape(note)}</div>' if note and note not in {title, label, ''} else ''
    number = f'<div class="hf-board-index">{int(chapter):02d}</div>' if chapter else ''
    return (
        f'<aside class="hf-board" data-hf-avatar="1" data-hypit-start-frame="{a}" data-hypit-end-frame="{b}" '
        f'data-hf-fade-in="6" data-hf-fade-out="6">'
        f'{number}'
        f'<div class="hf-board-label">{html.escape(label)}</div>'
        f'<i class="hf-board-rule"></i>'
        f'<div class="hf-board-figure">{html.escape(figure)}</div>'
        f'{unit_html}{note_html}</aside>'
    )


def _occupied(a, b, taken):
    return any(a < end and start < b for start, end in taken)


def _spans(layers):
    spans = []
    for layer in layers or []:
        found = re.search(r'data-hypit-start-frame="(\d+)" data-hypit-end-frame="(\d+)"', layer)
        if found:
            spans.append((int(found.group(1)), int(found.group(2))))
    return spans


def _clause(caption, language):
    """The first spoken phrase, short enough for a lower third. Nothing is added."""
    text = _short_line(caption, language, 22)
    for sep in ('，', ',', '。', '？', '?', '！', '!'):
        if sep in text:
            text = text.split(sep)[0].strip()
            break
    if re.search(r'[\u4e00-\u9fff]', text):
        return text[:12]
    return ' '.join(text.split()[:5])[:28]


def _caption_spans(caption, clips, ranges):
    spans = []
    for clip, (out_a, out_b) in zip(clips, ranges):
        src_a = float(clip['start'])
        src_b = float(clip['end'])
        start = max(float(caption['start']), src_a)
        end = min(float(caption['end']), src_b)
        if end <= start or src_b <= src_a or out_b <= out_a:
            continue
        scale = (out_b - out_a) / (src_b - src_a)
        spans.append((out_a + (start - src_a) * scale, out_a + (end - src_a) * scale))
    return spans


def _pace(clip, length, room=None):
    """The same speed the assembler uses, including a ramp and a source-end clamp."""
    from .timeline import playback

    speed, end, average = playback(clip, length, room)
    shaped = dict(clip)
    shaped.setdefault('zoom', 1)
    shaped.setdefault('x', 0.5)
    shaped.setdefault('y', 0.5)
    shaped['speed'] = speed
    shaped['speed_end'] = None if abs(end - speed) <= 0.04 else end
    return shaped, average


def _piece_vf(clip, width, height, length, room=None):
    """Measured move, grade, light, and pace, then a full frame for the capture.

    The filter is the one the assembler already trusts. A second speed change
    here would pull the mouth off the words.
    """
    from .timeline import motion_filter

    shaped, average = _pace(clip, length, room)
    chain = motion_filter(shaped, int(width), int(height), length)
    fill = (
        f'scale={int(width)}:{int(height)}:force_original_aspect_ratio=increase,'
        f'crop={int(width)}:{int(height)},fps={FPS},format=yuv420p'
    )
    return chain + fill, average


def _span(clip, available):
    """Source take and output length for one approved range. No file is written."""
    start = max(0.0, float(clip['start']))
    length = max(0.08, float(clip['end']) - float(clip['start']))
    room = (available - start) / length if available > start else 1
    _shaped, average = _pace(clip, length, room)
    return start, length, length * average, average


def _picture_cut(source, work, clips, width, height):
    """One continuous picture. Separate scene files leave a gap when joined.

    A crossfade would shorten the picture while the voice stays at the full
    clip length, so the mouth drifts further from the words on every join.
    """
    available = _piece_duration(source)
    chains = []
    labels = []
    lengths = []
    for index, clip in enumerate(clips):
        start, length, take, _average = _span(clip, available)
        _chain, _rate = _piece_vf(clip, width, height, length, (available - start) / length if available > start else 1)
        label = f'v{index}'
        chains.append(
            f'[0:v]trim=start={start:.3f}:duration={take:.3f},setpts=PTS-STARTPTS,{_chain}[{label}]'
        )
        labels.append(f'[{label}]')
        lengths.append(length)
    graph = work / 'picture.txt'
    graph.write_text(';\n'.join(chains) + f';\n{"".join(labels)}concat=n={len(labels)}:v=1:a=0[v]\n')
    out = work / 'cut.mp4'
    ffmpeg(
        '-i', str(source), '-filter_complex_script', str(graph), '-map', '[v]', '-an',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
        str(out), timeout=600,
    )
    ranges = []
    cursor = 0.0
    for length in lengths:
        ranges.append((cursor, cursor + length))
        cursor += length
    return max(1, int(round(cursor * FPS))), ranges


def _headcount(card):
    """A lone headcount such as 3 / 股东 is not a graphic."""
    if not isinstance(card, dict):
        return True
    primary = str((card.get('primary') or {}).get('zh') or (card.get('primary') or {}).get('en') or '').strip()
    title = ''.join(str((card.get('title') or {}).get(key) or '') for key in ('zh', 'en'))
    source = ''.join(str((card.get('source') or {}).get(key) or '') for key in ('zh', 'en'))
    if '%' in primary:
        return False
    if not primary.isdigit() or len(primary) > 2:
        return False
    return '股东' in title or '口播' in source or card.get('kind') == 'number'


def _plate_copy(card, language):
    if _headcount(card):
        return None
    lang = 'zh' if str(language).startswith('zh') else 'en'
    other = 'en' if lang == 'zh' else 'zh'
    title = str((card.get('title') or {}).get(lang) or (card.get('title') or {}).get(other) or '').strip()
    figure = str((card.get('primary') or {}).get(lang) or (card.get('primary') or {}).get(other) or '').strip()
    if not figure or figure in {'口播', '—'}:
        return None
    value = 0.0
    items = card.get('items') or []
    if items and isinstance(items[0], dict):
        try:
            value = float(items[0].get('value') or 0)
        except (TypeError, ValueError):
            value = 0.0
    if not value and figure.endswith('%'):
        try:
            value = float(figure[:-1])
        except ValueError:
            value = 0.0
    return title, figure, max(0.0, min(100.0, value))


def _plates(clips, ranges, language, total):
    layers = []
    for clip, (out_a, out_b) in zip(clips, ranges):
        card = clip.get('card') if isinstance(clip.get('card'), dict) else None
        copied = _plate_copy(card, language) if card else None
        if not copied or out_b <= out_a:
            continue
        title, figure, value = copied
        try:
            src_a, src_b = float(clip['start']), float(clip['end'])
            local_a = float(card.get('start') or 0)
            local_b = float(card.get('end') or (src_b - src_a))
        except (TypeError, ValueError, KeyError):
            continue
        span = src_b - src_a
        if span <= 0:
            continue
        scale = (out_b - out_a) / span
        start = out_a + max(0.0, local_a) * scale
        end = out_a + min(span, local_b) * scale
        if end - start < 0.4:
            start, end = out_a, out_b
        a = max(0, int(round(start * FPS)))
        b = max(a + 1, min(total, int(round(end * FPS))))
        fill = f'{value:.1f}'
        layers.append(
            f'<aside class="hf-plate" data-hf-avatar="1" data-hypit-start-frame="{a}" data-hypit-end-frame="{b}" data-hf-fade-in="5" data-hf-fade-out="5">'
            f'<div class="hf-board-label">{html.escape(title)}</div>'
            f'<i class="hf-board-rule"></i>'
            f'<div class="hf-board-figure">{html.escape(figure)}</div>'
            f'<div class="hf-plate-track"><div class="hf-plate-fill" style="width:{fill}%"></div></div>'
            f'</aside>'
        )
    return layers


def _stage_moment(style, fraction):
    """A reference host frame stays the presenter. A card frame takes the stage."""
    frames = (style or {}).get('frames') or []
    designed = [row for row in frames if row.get('kind') in ('stage', 'plate')]
    if len(designed) < 2:
        return True
    nearest = min(frames, key=lambda row: abs(float(row.get('at') or 0) - fraction))
    return nearest.get('kind') != 'host'


def _apply_style(page, style):
    stage = (style or {}).get('stage') or {}
    card = stage.get('card') if isinstance(stage.get('card'), dict) else None
    if not card:
        return page
    width = max(64.0, min(86.0, float(card['w']) * 100))
    height = max(46.0, min(68.0, float(card['h']) * 100))
    left = (100.0 - width) / 2
    top = (100.0 - height) / 2
    fill = str(stage.get('fill') or '10233f')
    ink = str(stage.get('ink') or 'ffffff')
    page = page.replace('left:7%;width:86%;top:15%;height:70%', f'left:{left:.1f}%;width:{width:.1f}%;top:{top:.1f}%;height:{height:.1f}%')
    page = page.replace('background:#10233f;color:#fff', f'background:#{fill};color:#{ink}')
    avatar = stage.get('avatar') if isinstance(stage.get('avatar'), dict) else {}
    try:
        diameter = max(0.22, min(0.34, float((avatar or {}).get('d') or 0.28)))
    except (TypeError, ValueError):
        diameter = 0.28
    # The measured reference parks the face in a corner. Keep the presenter in the middle of the card.
    ax, ay = 0.5, top / 100 + diameter / 2 + 0.04
    measured = (
        'data-card-left="{left}" data-card-top="{top}" data-card-width="{width}" data-card-height="{height}" '
        'data-avatar-x="{x}" data-avatar-y="{y}" data-avatar-d="{d}"'
    ).format(
        left=f'{left / 100:.3f}', top=f'{top / 100:.3f}', width=f'{width / 100:.3f}', height=f'{height / 100:.3f}',
        x=f'{ax:.3f}', y=f'{ay:.3f}', d=f'{diameter:.3f}',
    )
    defaults = 'data-card-left="0.070" data-card-top="0.150" data-card-width="0.860" data-card-height="0.700" data-avatar-d="0.280"'
    if defaults in page:
        page = page.replace(defaults, measured)
    else:
        page = page.replace('data-composition-id="lumen"', 'data-composition-id="lumen" ' + measured)
    return page


def _side_cards(clips, ranges, captions, language, total, style=None, occupied=None):
    """Reference card language, filled with this video's facts. Not the reference picture."""
    layers = []
    seen = set()
    for caption in captions or []:
        if not isinstance(caption, dict):
            continue
        copied = _graphic_copy(caption, language)
        figure = _spoken_figure(caption)
        clause = '' if copied or figure else _clause(caption, language)
        if not copied and not figure and len(clause) < 2:
            continue
        title, sub = copied if copied else (clause, '')
        spans = _caption_spans(caption, clips, ranges)
        if not spans:
            continue
        start, end = spans[0][0], spans[-1][1]
        if not _stage_moment(style, start / max(0.01, total / FPS)):
            continue
        if end - start < 1.6:
            end = min(total / FPS, start + 2.4)
        if end - start < 0.8:
            continue
        key = (title, int(start))
        if key in seen:
            continue
        seen.add(key)
        a = max(0, int(round(start * FPS)))
        b = max(a + 1, min(total, int(round(end * FPS))))
        if occupied is not None and _occupied(a, b, occupied):
            continue
        chapter = len(seen)
        if figure:
            shown, unit, label = figure
            layers.append(_board_html(title or label, shown, unit, sub, chapter, a, b))
        else:
            spoken = _short_line(caption, language)
            layers.append(_lower_html(title, sub, spoken, chapter, a, b))
        if occupied is not None:
            occupied.append((a, b))
    return layers


def _host_chips(clips, ranges, captions, language, total, style, occupied=None):
    """A reference host frame keeps the presenter and a small corner title."""
    layers = []
    seen = set()
    for caption in captions or []:
        if not isinstance(caption, dict):
            continue
        copied = _graphic_copy(caption, language)
        figure = _spoken_figure(caption)
        clause = '' if copied or figure else _clause(caption, language)
        if not copied and not figure and len(clause) < 2:
            continue
        spans = _caption_spans(caption, clips, ranges)
        if not spans:
            continue
        start, end = spans[0][0], spans[-1][1]
        if _stage_moment(style, start / max(0.01, total / FPS)):
            continue
        if end - start < 1.2:
            end = min(total / FPS, start + 2.2)
        if end - start < 0.6:
            continue
        title, sub = copied if copied else (clause, '')
        key = (title, int(start))
        if key in seen:
            continue
        seen.add(key)
        a = max(0, int(round(start * FPS)))
        b = max(a + 1, min(total, int(round(end * FPS))))
        if occupied is not None and _occupied(a, b, occupied):
            continue
        chapter = len(seen)
        if figure:
            shown, unit, label = figure
            layers.append(_board_html(title or label, shown, unit, '', chapter, a, b))
        else:
            spoken = _short_line(caption, language)
            layers.append(_lower_html(title, sub, spoken, chapter, a, b))
        if occupied is not None:
            occupied.append((a, b))
    return layers


def _window_box(x, y, title, body):
    """A rectangle that stays inside the frame and is wide enough for the words."""
    title, body = title or '', body or ''
    longest = max(len(title), len(body), 4)
    cjk = bool(re.search(r'[\u4e00-\u9fff]', title + body))
    unit = 5.4 if cjk else 2.5
    line = max(4, (longest + 1) // 2)
    width = min(46.0, max(32.0, line * unit + 10))
    left = min(max(4.0, float(x) * 100 - width / 2), 100 - 4 - width)
    per_line = max(1, int((width - 10) / unit))
    rows = max(1, -(-len(title) // per_line))
    if body:
        rows += max(1, -(-len(body) // per_line))
    height = rows * 4.4 + 8
    top = 7.0 if float(y) < 0.5 else 100 - 6 - height
    top = min(max(6.0, top), 100 - 6 - height)
    return left, top, width


def presentation_layers(beats, language, total_frames):
    """Hypit layers whose on-screen time is the prompt percentage."""
    from .presentation_graphics import _words
    layers = []
    for beat in beats or []:
        if not isinstance(beat, dict):
            beat = beat.model_dump()
        start, end = float(beat['start']), float(beat['end'])
        a = max(0, int(round(start * FPS)))
        b = max(a + 1, min(int(total_frames), int(round(end * FPS))))
        title = _words(beat.get('title') or {}, language)
        body = _words(beat.get('body') or {}, language) if beat.get('kind') == 'mini' and beat.get('body') else ''
        kind = 'mini' if body else 'window'
        left, top, width = _window_box(beat.get('x') or 0.72, beat.get('y') or 0.28, title, body)
        cls = 'hf-mini' if kind == 'mini' else 'hf-window'
        inner = (
            f'<div class="hf-card-title">{html.escape(title)}</div>'
            + (f'<div class="hf-card-sub">{html.escape(body)}</div>' if body else '')
        )
        layers.append(
            f'<aside class="{cls}" data-hypit-kind="{kind}" data-hypit-start-frame="{a}" data-hypit-end-frame="{b}" '
            f'data-hf-fade-in="6" data-hf-fade-out="6" '
            f'style="left:{left:.1f}%;top:{top:.1f}%;right:auto;bottom:auto;width:{width:.1f}%">{inner}</aside>'
        )
    return layers


def _card_motion(manual):
    """How far the cards animate. A missing value keeps the full designed motion."""
    if not isinstance(manual, dict) or 'card_motion' not in manual:
        return 100
    try:
        return max(0, min(100, int(manual.get('card_motion') or 0)))
    except (TypeError, ValueError):
        return 100


def _graphic_layer(layer):
    return bool(re.search(r'class="(?:hf-plate|hf-board|hf-lower|hf-window|hf-mini|hf-chip)\b', layer))


def _retimed(layer, start, end):
    layer = re.sub(r'data-hypit-start-frame="\d+"', f'data-hypit-start-frame="{start}"', layer, count=1)
    return re.sub(r'data-hypit-end-frame="\d+"', f'data-hypit-end-frame="{end}"', layer, count=1)


def _even_indexes(count, total):
    if count >= total:
        return list(range(total))
    if count <= 1:
        return [total // 2]
    return [round(i * (total - 1) / (count - 1)) for i in range(count)]


def _limit_graphics(layers, total_frames, share):
    """Keep animated plates on about `share` percent of the picture, spread through it."""
    share = max(0, min(100, int(share)))
    graphic = [layer for layer in layers if _graphic_layer(layer)]
    rest = [layer for layer in layers if layer not in graphic]
    if share >= 100 or not graphic:
        return rest + graphic
    if share <= 0 or total_frames <= 0:
        return rest
    parsed = []
    for layer in graphic:
        found = re.search(r'data-hypit-start-frame="(\d+)" data-hypit-end-frame="(\d+)"', layer)
        if not found:
            continue
        start, end = int(found.group(1)), int(found.group(2))
        if end > start:
            parsed.append((start, end, layer))
    if not parsed:
        return rest
    parsed.sort()
    budget = total_frames * share / 100
    full = sum(end - start for start, end, _layer in parsed)
    if budget >= full:
        return rest + [layer for _start, _end, layer in parsed]
    minimum = max(1, int(round(0.8 * FPS)))
    chosen = parsed
    for count in range(len(parsed), 0, -1):
        indexes = _even_indexes(count, len(parsed))
        picked = [parsed[index] for index in indexes]
        covered = sum(end - start for start, end, _layer in picked)
        scale = budget / covered if covered else 0
        if count == 1 or all((end - start) * scale >= minimum for start, end, _layer in picked):
            chosen = picked
            break
    covered = sum(end - start for start, end, _layer in chosen)
    scale = min(1.0, budget / covered) if covered else 0
    kept = []
    for start, end, layer in chosen:
        length = max(1, int(round((end - start) * scale)))
        stop = min(end, start + length)
        if stop <= start:
            stop = start + 1
        kept.append(layer if stop == end else _retimed(layer, start, stop))
    return rest + kept


def composition(source, work, manual, width, height, language, style=None):
    """HyperFrames HTML. A paragraph, 口播, and a lone headcount digit are not drawn.

    One assembled picture is captured. A tag per clip makes Chrome decode every
    piece at once and the capture never finishes.
    """
    clips = [clip for clip in manual['clips'] if clip.get('approved', True)]
    total, ranges = _picture_cut(source, work, clips, width, height)
    layers = [_video(
        'picture', 'cut.mp4', 0, total, 0, 0.0, Fraction(1, 1), FPS, 1, 0, 0,
    )]
    if manual.get('subtitles'):
        for index, caption in enumerate(manual.get('captions') or []):
            line = _caption_line(caption, language)
            if not line or len(line) > 72:
                continue
            for span_index, (start, end) in enumerate(_caption_spans(caption, clips, ranges)):
                a = max(0, int(round(start * FPS)))
                b = max(a + 1, int(round(end * FPS)))
                layers.append(
                    f'<div class="hf-caption" data-hypit-start-frame="{a}" data-hypit-end-frame="{min(b, total)}" '
                    f'data-hf-fade-in="4" data-hf-fade-out="4">{html.escape(line)}</div>'
                )
                if span_index > 8:
                    break
    plates = _plates(clips, ranges, language, total)
    occupied = _spans(plates)
    graphics = plates + _side_cards(clips, ranges, manual.get('captions') or [], language, total, style, occupied)
    graphics.extend(_host_chips(clips, ranges, manual.get('captions') or [], language, total, style, occupied))
    motion = _card_motion(manual)
    layers.extend(_limit_graphics(graphics, total, motion))
    seconds = f'{total / FPS:.3f}'
    body = '\n    '.join(layers)
    page = f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <style>
    html,body{{margin:0;overflow:hidden;background:#101614}}
    [data-composition-id]{{position:relative;width:{width}px;height:{height}px;overflow:hidden;background:#101614}}
    video,img.hf-still{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0}}
    .hf-caption{{position:absolute;left:8%;right:8%;bottom:3.5%;z-index:7;text-align:center;color:#fff;font:600 {max(16, height // 48)}px/1.2 sans-serif;text-shadow:0 1px 6px #000;opacity:0;max-height:2.5em;overflow:hidden}}
    .hf-card,.hf-plate{{position:absolute;left:7%;width:86%;top:15%;height:70%;z-index:4;box-sizing:border-box;padding:22px 8% 26px;border-radius:28px;background:#10233f;color:#fff;text-align:left;opacity:0;box-shadow:0 18px 48px rgba(0,0,0,.45);display:flex;flex-direction:column;align-items:stretch;justify-content:flex-start;gap:14px;overflow:hidden}}
    .hf-chip{{position:absolute;left:5%;top:7%;width:46%;z-index:5;padding:12px 14px;border-radius:16px;background:#10233f;color:#fff;text-align:left;opacity:0;box-shadow:0 10px 24px rgba(0,0,0,.35)}}
    .hf-lower{{position:absolute;left:6%;right:24%;bottom:16%;z-index:5;color:#fff;text-align:left;opacity:0;text-shadow:0 2px 10px rgba(0,0,0,.55)}}
    .hf-lower-head{{display:flex;align-items:center;gap:10px;font:800 {max(22, height // 36)}px/1.2 "Noto Sans CJK SC",sans-serif}}
    .hf-lower-head b{{flex:none;padding:6px 8px;background:#12315c;border-left:3px solid #7eb6ff;font:700 {max(15, height // 52)}px/1 "Noto Sans CJK SC",sans-serif}}
    .hf-lower-head span{{min-width:0}}
    .hf-lower-bar{{display:block;width:64px;height:4px;margin:8px 0 6px;background:#7eb6ff}}
    .hf-lower-kicker{{font:600 {max(16, height // 48)}px/1.3 "Noto Sans CJK SC",sans-serif;opacity:.92}}
    .hf-board-index{{margin-bottom:10px;padding:6px 8px;background:#12315c;border-left:3px solid #7eb6ff;font:700 {max(15, height // 52)}px/1 "Noto Sans CJK SC",sans-serif}}
    .hf-board{{position:absolute;inset:0;z-index:4;box-sizing:border-box;padding:22% 8% 12% 8%;display:flex;flex-direction:column;align-items:flex-start;justify-content:center;color:#fff;text-align:left;opacity:0;background:radial-gradient(120% 80% at 82% 16%, #16325c 0%, #0b1830 58%, #08101f 100%)}}
    .hf-board-label{{font:600 {max(22, height // 36)}px/1.2 "Noto Sans CJK SC",sans-serif}}
    .hf-board-rule{{display:block;width:68%;height:3px;margin:16px 0 18px;background:rgba(255,255,255,.4)}}
    .hf-board-figure{{font:800 {max(56, height // 12)}px/1 "Noto Sans CJK SC",sans-serif;color:#f2c14b;letter-spacing:-.03em}}
    .hf-board-unit{{margin-top:8px;font:600 {max(16, height // 46)}px/1.2 "Noto Sans CJK SC",sans-serif;opacity:.82}}
    .hf-board-note{{margin-top:16px;max-width:78%;padding:10px 14px;border-radius:8px;background:rgba(255,255,255,.08);font:600 {max(16, height // 48)}px/1.3 "Noto Sans CJK SC",sans-serif}}
    .hf-card-bar{{width:48px;height:6px;border-radius:6px;background:#7eb6ff;margin:8% 0 4px}}
    .hf-card-title{{box-sizing:border-box;width:100%;padding:14px 12px;border-radius:16px;background:rgba(255,255,255,.1);font:700 {max(22, height // 22)}px/1.12 sans-serif}}
    .hf-card-sub{{box-sizing:border-box;width:100%;padding:10px 12px;border-radius:14px;background:rgba(255,255,255,.06);font:600 {max(13, height // 48)}px/1.2 sans-serif;letter-spacing:.04em;opacity:.86}}
    .hf-chip .hf-card-title{{padding:0;background:none;font:700 {max(18, height // 32)}px/1.15 sans-serif}}
    .hf-chip .hf-card-sub{{padding:0;margin-top:4px;background:none;font:600 {max(12, height // 52)}px/1.2 sans-serif}}
    .hf-window,.hf-mini{{position:absolute;z-index:6;box-sizing:border-box;width:auto;max-width:46%;padding:14px 16px;border-radius:18px;background:#10233f;color:#fff;text-align:left;opacity:0;box-shadow:0 14px 32px rgba(0,0,0,.4);display:flex;flex-direction:column;justify-content:center;gap:6px;overflow:visible}}
    .hf-window .hf-card-title,.hf-mini .hf-card-title{{width:auto;padding:0;border-radius:0;background:none;font:700 {max(15, min(22, height // 52))}px/1.28 sans-serif;overflow-wrap:break-word}}
    .hf-window .hf-card-sub,.hf-mini .hf-card-sub{{width:auto;padding:0;border-radius:0;background:none;letter-spacing:0;font:600 {max(13, min(16, height // 64))}px/1.3 sans-serif;overflow-wrap:break-word;opacity:.9}}
    .hf-plate-label{{font:600 {max(14, height // 46)}px/1.2 sans-serif;letter-spacing:.06em;opacity:.78}}
    .hf-plate-value{{font:700 {max(36, height // 12)}px/1 sans-serif;margin-top:8px}}
    .hf-plate-track{{width:72%;height:10px;margin-top:18px;border-radius:10px;background:rgba(255,255,255,.22);overflow:hidden}}
    .hf-plate-fill{{height:100%;border-radius:10px;background:#d5f5c4}}
  </style>
</head>
<body>
  <div data-composition-id="lumen" data-card-motion="{motion}" data-card-left="0.070" data-card-top="0.150" data-card-width="0.860" data-card-height="0.700" data-avatar-d="0.280" data-start="0" data-no-timeline data-width="{width}" data-height="{height}" data-duration="{seconds}" data-fps="{FPS}/1" data-hypit-frame-count="{total}">
    {body}
  </div>
  <script>
    const fps = {FPS};
    const layers = [...document.querySelectorAll('[data-hypit-start-frame]')];
    const apply = (time) => {{
      const frame = Math.max(0, Math.round(Number(time || 0) * fps));
      const stage = document.querySelector('[data-composition-id]');
      const motion = Math.max(0, Math.min(100, Number((stage && stage.getAttribute('data-card-motion')) || 100))) / 100;
      for (const el of layers) {{
        const start = Number(el.getAttribute('data-hypit-start-frame'));
        const end = Number(el.getAttribute('data-hypit-end-frame'));
        const fadeIn = Number(el.getAttribute('data-hf-fade-in') || 0);
        const fadeOut = Number(el.getAttribute('data-hf-fade-out') || 0);
        let opacity = 0;
        const card = el.classList.contains('hf-board') || el.classList.contains('hf-lower') || el.classList.contains('hf-card') || el.classList.contains('hf-plate') || el.classList.contains('hf-window') || el.classList.contains('hf-mini') || el.classList.contains('hf-chip');
        if (frame >= start && frame < end) {{
          if (card && motion <= 0) opacity = 1;
          else {{
            const amount = card ? motion : 1;
            const innFrames = fadeIn * amount;
            const outFrames = fadeOut * amount;
            const inn = innFrames > 0 ? Math.min(1, (frame - start + 1) / innFrames) : 1;
            const out = outFrames > 0 ? Math.min(1, (end - frame) / outFrames) : 1;
            opacity = Math.min(inn, out);
          }}
        }}
        el.style.opacity = String(opacity);
        if (card) {{
          const lift = Math.round((el.classList.contains('hf-board') ? 28 : 16) * motion);
          el.style.transform = 'translateY(' + Math.round((1 - opacity) * lift) + 'px)';
          const figure = el.querySelector('.hf-board-figure');
          if (figure) figure.style.transform = 'scale(' + (1 - 0.1 * motion * (1 - opacity)).toFixed(3) + ')';
        }}
      }}
      const video = document.getElementById('picture');
      const frameBox = video && video.parentElement;
      const covers = (el) => frame >= Number(el.getAttribute('data-hypit-start-frame')) && frame < Number(el.getAttribute('data-hypit-end-frame'));
      const plateOn = layers.some((el) => el.classList.contains('hf-plate') && covers(el));
      const boardOn = !plateOn && layers.some((el) => el.classList.contains('hf-board') && covers(el));
      const avatar = plateOn || boardOn;
      const root = video && video.parentElement;
        if (video && frameBox) {{
          const frameW = frameBox.clientWidth;
          const frameH = frameBox.clientHeight;
          const cardLeft = Number(root.getAttribute('data-card-left') || 0.07);
          const cardTop = Number(root.getAttribute('data-card-top') || 0.15);
          const cardWidth = Number(root.getAttribute('data-card-width') || 0.86);
          const cardHeight = Number(root.getAttribute('data-card-height') || 0.70);
          const ad = Number(root.getAttribute('data-avatar-d') || (boardOn ? 0.22 : 0.28));
          const box = Math.round(frameW * (ad > 0.12 ? ad : 0.28));
          const half = box / 2;
          const marginX = Math.round(frameW * 0.04);
          const marginY = Math.round(frameH * 0.04);
          let cx = frameW * (cardLeft + cardWidth / 2);
          let cy = frameH * cardTop + box * 0.42;
          if (boardOn && !plateOn) {{
            cx = frameW * 0.78;
            cy = frameH * 0.18;
          }}
          cx = Math.max(marginX + half, Math.min(frameW - marginX - half, cx));
          cy = Math.max(marginY + half, Math.min(frameH - marginY - half, cy));
          for (const el of layers) {{
            if (!el.classList.contains('hf-plate')) continue;
            el.style.inset = 'auto';
            el.style.left = (cardLeft * 100) + '%';
            el.style.top = (cardTop * 100) + '%';
            el.style.width = (cardWidth * 100) + '%';
            el.style.height = (cardHeight * 100) + '%';
            el.style.right = 'auto';
            el.style.bottom = 'auto';
            el.style.paddingTop = Math.max(18, Math.round(cy + half - frameH * cardTop + 18)) + 'px';
            el.style.paddingLeft = '8%';
            el.style.paddingRight = '8%';
            el.style.alignItems = 'stretch';
            el.style.textAlign = 'left';
          }}
        if (avatar) {{
          video.style.width = box + 'px';
          video.style.height = box + 'px';
          video.style.left = Math.round(cx - half) + 'px';
          video.style.top = Math.round(cy - half) + 'px';
          video.style.right = 'auto';
          video.style.bottom = 'auto';
          video.style.objectFit = 'cover';
          video.style.objectPosition = 'center 30%';
          video.style.borderRadius = '50%';
          video.style.zIndex = '6';
          video.style.boxShadow = '0 0 0 5px #fff';
        }} else {{
          video.style.width = '100%';
          video.style.height = '100%';
          video.style.top = '0';
          video.style.right = '0';
          video.style.left = '0';
          video.style.bottom = '0';
          video.style.borderRadius = '0';
          video.style.zIndex = '1';
          video.style.boxShadow = 'none';
        }}
      }}
    }};
    apply(0);
    window.addEventListener('hf-seek', (event) => apply(event.detail && event.detail.time));
  </script>
</body>
</html>
'''
    page = _apply_style(page, style)
    prompt = manual.get('presentation_prompt') or ''
    if prompt:
        page = page.replace(
            'data-composition-id="lumen"',
            'data-composition-id="lumen" data-hypit-prompt="' + html.escape(prompt, quote=True) + '"',
            1,
        )
    (work / 'index.html').write_text(page)
    return total


def _video(ident, src, start, end, origin, media_start, rate, src_num, src_den, fade_in, fade_out):
    # data-start/data-end are this clip on the timeline. Without them Hypit treats
    # every tag as the whole file and extracts that file once per clip.
    return (
        f'<video id="{ident}" src="{src}" muted playsinline preload="none" data-has-audio="false" '
        f'data-start="{start / FPS:.3f}" data-end="{end / FPS:.3f}" data-media-start="{media_start:.3f}" '
        f'data-hypit-start-frame="{start}" data-hypit-end-frame="{end}" '
        f'data-hypit-source-frame="{origin}/1" data-hypit-source-rate="{rate.numerator}/{rate.denominator}" '
        f'data-hypit-source-fps="{src_num}/{src_den}" '
        f'data-hf-fade-in="{fade_in}" data-hf-fade-out="{fade_out}"></video>'
    )


def _piece_duration(path):
    out, _ = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(path)], 30)
    try:
        return float((json.loads(out or '{}').get('format') or {}).get('duration') or 0)
    except (TypeError, ValueError):
        return 0.0


def _host_audio(source, folder, clips):
    """One speech stem for the whole picture. Scene files leave a gap at each join."""
    available = _piece_duration(source)
    chains = []
    labels = []
    for index, clip in enumerate(clips):
        start, length, take, average = _span(clip, available)
        tempo = f',atempo={average:.4f}' if abs(average - 1) > 0.04 else ''
        label = f'a{index}'
        chains.append(
            f'[0:a]atrim=start={start:.3f}:duration={take:.3f},asetpts=PTS-STARTPTS{tempo},'
            f'atrim=duration={length:.3f},aformat=sample_fmts=s16:sample_rates=48000:channel_layouts=stereo[{label}]'
        )
        labels.append(f'[{label}]')
    graph = folder / 'speech.txt'
    graph.write_text(';\n'.join(chains) + f';\n{"".join(labels)}concat=n={len(labels)}:v=0:a=1[a]\n')
    mixed = folder / 'hypit-audio.wav'
    ffmpeg(
        '-i', str(source), '-filter_complex_script', str(graph), '-map', '[a]',
        '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', str(mixed), timeout=600,
    )
    return mixed


def render_picture(source, folder, manual, width, height, metadata, asset_paths=None, language='en'):
    """Composite the approved clips. Raises hypit_unavailable when capture cannot run."""
    clips = [dict(clip) for clip in manual['clips'] if clip.get('approved', True)]
    if not clips:
        raise RuntimeError('hypit_unavailable')
    work = Path(folder) / 'hypit'
    work.mkdir(parents=True, exist_ok=True)
    from .media import _art_file, _licensed_still, _reference_clip
    shaped = []
    for clip in clips:
        item = dict(clip)
        broll = item.get('external_broll') or {}
        found = (asset_paths or {}).get(broll.get('asset_id')) if broll.get('asset_id') else None
        if broll.get('asset_id') and not found:
            raise ValueError('asset_not_found')
        if found:
            item['_hypit_broll'] = found
        insert = _reference_clip(source, item.get('picture_insert'))
        if insert:
            item['_hypit_insert'] = insert
        still = _licensed_still(item, asset_paths) or _art_file(source, item.get('art'))
        if still and not item.get('cutout') and not item.get('mask'):
            item['_hypit_still'] = still
        shaped.append(item)
    manual = dict(manual)
    manual['clips'] = shaped
    from .style_match import reference_video
    from .style_vision import read_style
    reference = reference_video(Path(source).resolve().parent)
    try:
        style = read_style(reference) if reference else None
    except Exception:
        style = None
    frame_count = composition(source, work, manual, width, height, language, style)
    if 'card_motion' in manual:
        (Path(folder) / 'animation-share.txt').write_text(str(_card_motion(manual)))
    job = {
        'directory': str(work),
        'width': int(width),
        'height': int(height),
        'fpsNum': FPS,
        'fpsDen': 1,
        'frameCount': frame_count,
    }
    job_path = work / 'job.json'
    job_path.write_text(json.dumps(job))
    argv, root, tsx = command(job_path)
    if not tsx.is_file() or not SCRIPT.is_file():
        raise RuntimeError('hypit_unavailable')
    env = os.environ.copy()
    env['HYPIT_ROOT'] = str(root)
    try:
        spawn(argv, env)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        log.warning('hypit capture failed: %s', capture_note(exc) or type(exc).__name__)
        raise RuntimeError('hypit_unavailable') from exc
    visual = work / 'visual.mp4'
    if not visual.is_file() or visual.stat().st_size < 32:
        raise RuntimeError('hypit_unavailable')
    assembled = Path(folder) / 'assembled.mp4'
    if metadata.get('has_audio'):
        audio = _host_audio(source, work, clips)
        if manual.get('voice_cleanup'):
            from .hypit_controls import clean_host
            audio = clean_host(audio, work)
        ffmpeg('-i', visual, '-i', audio, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', assembled, timeout=600)
    else:
        ffmpeg('-i', visual, '-c', 'copy', '-movflags', '+faststart', assembled, timeout=600)
    return assembled


def _presentation_page(width, height, seconds, frames, layers, prompt):
    body = '\n    '.join(layers)
    escaped = html.escape(prompt or '', quote=True)
    return f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <style>
    html,body{{margin:0;overflow:hidden;background:#101614}}
    [data-composition-id]{{position:relative;width:{width}px;height:{height}px;overflow:hidden;background:#101614;perspective:900px}}
    video{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
    .hf-window,.hf-mini{{position:absolute;z-index:4;box-sizing:border-box;max-width:46%;padding:14px 16px;border-radius:18px;background:#10233f;color:#fff;opacity:0;box-shadow:0 14px 32px rgba(0,0,0,.4);overflow:visible}}
    .hf-card-title{{font:700 {max(15, min(22, int(height) // 52))}px/1.28 sans-serif;overflow-wrap:break-word}}
    .hf-card-sub{{margin-top:6px;font:600 {max(13, min(16, int(height) // 64))}px/1.3 sans-serif;opacity:.9;overflow-wrap:break-word}}
  </style>
</head>
<body>
  <div data-composition-id="lumen" data-hypit-prompt="{escaped}" data-start="0" data-no-timeline data-width="{width}" data-height="{height}" data-duration="{seconds}" data-fps="{FPS}/1" data-hypit-frame-count="{frames}">
    <video id="picture" src="cut.mp4" muted playsinline data-has-audio="false" data-start="0.000" data-end="{seconds}" data-media-start="0.000" data-hypit-start-frame="0" data-hypit-end-frame="{frames}" data-hypit-source-frame="0/1" data-hypit-source-rate="1/1" data-hypit-source-fps="{FPS}/1"></video>
    {body}
  </div>
  <script>
    const fps = {FPS};
    const layers = [...document.querySelectorAll('[data-hypit-kind]')];
    const apply = (time) => {{
      const frame = Math.max(0, Math.round(Number(time || 0) * fps));
      for (const el of layers) {{
        const start = Number(el.getAttribute('data-hypit-start-frame'));
        const end = Number(el.getAttribute('data-hypit-end-frame'));
        const fadeIn = Number(el.getAttribute('data-hf-fade-in') || 0);
        const fadeOut = Number(el.getAttribute('data-hf-fade-out') || 0);
        let opacity = 0;
        if (frame >= start && frame < end) {{
          const inn = fadeIn ? Math.min(1, (frame - start + 1) / fadeIn) : 1;
          const out = fadeOut ? Math.min(1, (end - frame) / fadeOut) : 1;
          opacity = Math.min(inn, out);
        }}
        el.style.opacity = String(opacity);
        el.style.transform = 'translateY(' + Math.round((1 - opacity) * 16) + 'px)';
      }}
    }};
    apply(0);
    window.addEventListener('hf-seek', (event) => apply(event.detail && event.detail.time));
  </script>
</body>
</html>
'''


def apply_presentation(video, folder, manual, width, height, language):
    """Run the slider prompt through Hypit. The share is the graphics coverage."""
    beats = manual.get('presentation') or []
    prompt = manual.get('presentation_prompt') or ''
    if int(manual.get('presentation_share') or 0) <= 0 or not beats:
        return video
    work = Path(folder) / 'hypit-presentation'
    # A second capture in this folder must not die on Hypit's worker-0 mkdir.
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    cut = work / 'cut.mp4'
    ffmpeg('-y', '-i', str(video), '-an', '-c:v', 'copy', str(cut), timeout=600)
    duration = _piece_duration(cut) or _piece_duration(video)
    frames = max(1, int(round(duration * FPS)))
    seconds = f'{frames / FPS:.3f}'
    page = _presentation_page(width, height, seconds, frames, presentation_layers(beats, language, frames), prompt)
    (work / 'index.html').write_text(page)
    job = {
        'directory': str(work),
        'width': int(width),
        'height': int(height),
        'fpsNum': FPS,
        'fpsDen': 1,
        'frameCount': frames,
    }
    job_path = work / 'job.json'
    job_path.write_text(json.dumps(job))
    argv, root, tsx = command(job_path)
    if not tsx.is_file() or not SCRIPT.is_file():
        raise RuntimeError('hypit_unavailable')
    env = os.environ.copy()
    env['HYPIT_ROOT'] = str(root)
    try:
        spawn(argv, env)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        log.warning('hypit presentation capture failed: %s', capture_note(exc) or type(exc).__name__)
        raise RuntimeError('hypit_unavailable') from exc
    visual = work / 'visual.mp4'
    if not visual.is_file() or visual.stat().st_size < 32:
        raise RuntimeError('hypit_unavailable')
    presented = Path(folder) / 'presented.mp4'
    ffmpeg(
        '-y', '-i', str(visual), '-i', str(video), '-map', '0:v:0', '-map', '1:a:0?',
        '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart', str(presented),
        timeout=600,
    )
    return presented
