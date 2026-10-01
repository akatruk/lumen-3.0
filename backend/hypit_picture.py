"""Style-match pictures are one Hypit build of one prompt.

Hypit is Apache License 2.0 with additional conditions. Lumen does not vendor
that source. The prompt names the percent and the spoken words. ``hypit build``
returns one video. Lumen does not cut the footage into scenes or set a
parameter on each frame.
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


def _chrome():
    chosen = os.environ.get('HYPIT_CHROME')
    if chosen and Path(chosen).is_file():
        return chosen
    for path in (
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
    ):
        if Path(path).is_file():
            return path
    roots = (
        Path('/opt/lumen-rebuild/.cache/hyperframes/chrome'),
        Path.home() / '.cache' / 'hyperframes' / 'chrome',
    )
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob('**/chrome-headless-shell')):
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
    return ''


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


def _build_payload(text):
    """The last Hypit build report. Progress lines may precede the JSON."""
    decoder = json.JSONDecoder()
    found = None
    for index, char in enumerate(text or ''):
        if char != '{':
            continue
        try:
            payload, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get('format') == 'hypit.cli-build@1':
            found = payload
    if not found or not (found.get('build') or {}).get('id'):
        raise RuntimeError('hypit_unavailable')
    work = (found.get('build') or {}).get('work') or {}
    if work.get('outcome') == 'failed' or work.get('state') == 'failed':
        raise RuntimeError('hypit_unavailable')
    return found


def _runtime_profile(work):
    """Local picture and alignment only. A hosted key is not part of this prompt."""
    chrome = _chrome()
    picture = {'use': '@hypit/provider-hyperframes-local', 'config': {'workers': 1, 'defaultConcurrency': 1}}
    if chrome:
        picture['config']['chromePath'] = chrome
    profile = {
        'format': 'hypit.runtime-local@1',
        'dataRoot': '.hypit/runtimes/local',
        'endpoints': {
            'media.local': {'use': '@hypit/provider-media-local'},
            'hyperframes.local': picture,
            'whisperx.local': {'use': '@hypit/provider-whisperx-local'},
        },
    }
    path = Path(work) / 'hypit.runtime.json'
    path.write_text(json.dumps(profile))
    return path


def deliver(work):
    """Build the one prompt and write visual.mp4. The source is not spliced."""
    work = Path(work)
    binary = _root() / 'bin' / 'hypit.mjs'
    if not binary.is_file():
        raise RuntimeError('hypit_unavailable')
    node = os.environ.get('HYPIT_NODE') or 'node'
    env = os.environ.copy()
    env['HYPIT_ROOT'] = str(_root())

    def cli(args):
        try:
            return subprocess.run(
                [node, str(binary), *args, '--workspace', str(work)],
                check=True, cwd=str(work), env=env, timeout=45 * 60,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, errors='replace',
            )
        except subprocess.CalledProcessError as exc:
            output = (exc.stderr or '').strip() or (exc.stdout or '').strip()
            raise _note_failure(RuntimeError('hypit_unavailable'), f'exit {exc.returncode}: {output}' if output else f'exit {exc.returncode}') from None
        except subprocess.TimeoutExpired as exc:
            raise _note_failure(RuntimeError('hypit_unavailable'), 'build timed out') from exc
        except OSError as exc:
            raise _note_failure(RuntimeError('hypit_unavailable'), f'{type(exc).__name__}: {exc.strerror or "build could not start"}') from exc

    _runtime_profile(work)
    cli(['runtime', 'use', 'hypit.runtime.json'])
    completed = cli(['build', 'build.svrun', '--follow', '--json'])
    build_id = _build_payload(completed.stdout)['build']['id']
    visual = work / 'visual.mp4'
    cli(['get', build_id, '--output', 'final.video', '--to', str(visual)])
    if not visual.is_file() or visual.stat().st_size < 32:
        raise RuntimeError('hypit_unavailable')
    return visual


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
    here would pull the mouth off the words. The invented 1.00→1.26 push is
    dropped here so a saved effect pick cannot resample the face.
    """
    from .style_match import _undo_staged_push
    from .timeline import motion_filter

    if isinstance(clip, dict):
        _undo_staged_push(clip)
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
    """The whole source, once. Clips are not trimmed and not joined."""
    del clips
    duration = max(0.1, _piece_duration(source))
    chain = (
        f'scale={int(width)}:{int(height)}:force_original_aspect_ratio=increase,'
        f'crop={int(width)}:{int(height)},fps={FPS},format=yuv420p'
    )
    graph = work / 'picture.txt'
    graph.write_text(f'[0:v]{chain}[v]\n')
    out = work / 'cut.mp4'
    ffmpeg(
        '-i', str(source), '-filter_complex_script', str(graph), '-map', '[v]', '-an',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
        str(out), timeout=600,
    )
    return max(1, int(round(duration * FPS))), duration


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
    return bool(re.search(r'class="(?:hf-plate|hf-board|hf-idea|hf-lower|hf-window|hf-mini|hf-chip)\b', layer))


def _scene_cards(beat):
    """Labels already spoken. A short phrase stays one card; a split line becomes several."""
    if beat.get('left') and beat.get('right'):
        cards = [beat['title'], beat['left'], beat['right']]
    else:
        line = beat.get('line') or beat['title']
        cards = []
        for part in re.split(r'[，,。；;：:、]', line):
            label = part.strip()[:12]
            if len(label) < 2 or label in cards:
                continue
            cards.append(label)
            if len(cards) == 3:
                break
        if beat.get('figure'):
            cards = [beat['figure'], beat['title'], *cards]
        if not cards:
            cards = [beat['title']]
    seen = []
    for card in cards:
        if card and card not in seen:
            seen.append(card)
    return seen[:3]


def _scene_body(beat, chapter):
    """One composed board. The layout changes; the words stay the ones that were spoken."""
    kind = beat['kind']
    title = html.escape(beat['title'])
    figure = html.escape(beat['figure'] or '')
    line = html.escape((beat.get('line') or beat['title'])[:42])
    cards = [html.escape(card) for card in _scene_cards(beat)]
    layout = 'columns' if kind == 'compare' else ('flow', 'stack', 'columns')[(chapter - 1) % 3]
    mark = ''
    if kind in {'up', 'down'}:
        mark = f'<i class="hf-idea-mark" data-visual-mark="{kind}"></i>'
    elif kind == 'deadline':
        mark = '<i class="hf-idea-track"><i class="hf-idea-fill"></i></i>'
    head = figure or title
    strong = (
        f'<strong class="hf-scene-figure">{figure}</strong>'
        if kind == 'figure' and figure else f'<strong>{head}</strong>'
    )
    extras = [card for card in cards if card not in {head, title}]
    piece = 0

    def tag(node):
        nonlocal piece
        piece += 1
        if node.startswith('<b>'):
            return f'<b data-hf-piece="{piece}">' + node[3:]
        if node.startswith('<div '):
            return node.replace('<div ', f'<div data-hf-piece="{piece}" ', 1)
        if node.startswith('<p '):
            return node.replace('<p ', f'<p data-hf-piece="{piece}" ', 1)
        return node

    if layout == 'stack':
        bits = [tag(f'<b>{mark}{strong}</b>')]
        for extra in (extras or ([title] if title != head else []))[:2]:
            bits.append(tag(f'<b><strong>{extra}</strong></b>'))
        inner = f'<div class="hf-stack">{"".join(bits)}</div>'
    elif layout == 'columns' and len(cards) >= 2:
        inner = f'<div class="hf-scene-row">{"".join(tag(f"<b>{card}</b>") for card in cards[:3])}</div>'
    else:
        row = ''.join(tag(f'<b>{card}</b>') for card in (extras or cards)[:3])
        inner = (
            f'{tag(f"<div class=\"hf-scene-head\">{mark}{strong}</div>")}'
            f'<i class="hf-scene-link" data-hf-piece="{piece + 1}"></i><div class="hf-scene-row">{row}</div>'
        )
        piece += 1
    return layout, f'<i class="hf-scene-shard"></i>{inner}{tag(f"<p class=\"hf-scene-caption\">{line}</p>")}'


def _speech_ideas(clips, ranges, captions, total, occupied=None):
    """Full-frame pictures of spoken phrases. A plate that already holds the moment stays."""
    from .presentation_graphics import speech_visuals

    layers = []
    chapter = 0
    for beat in speech_visuals({'captions': captions or []}):
        start, end = float(beat['start']), float(beat['end'])
        spans = _caption_spans({'start': start, 'end': end}, clips, ranges)
        if not spans:
            continue
        out_start, out_end = spans[0][0], spans[-1][1]
        if out_end - out_start < 0.45:
            continue
        a = max(0, int(round(out_start * FPS)))
        b = max(a + 1, min(total, int(round(out_end * FPS))))
        chapter += 1
        kind = beat['kind']
        layout, body = _scene_body(beat, chapter)
        layers.append(
            f'<aside class="hf-idea hf-scene" data-visual="{kind}" data-scene="{layout}" data-hf-avatar="1" '
            f'data-hypit-start-frame="{a}" data-hypit-end-frame="{b}" '
            f'data-hf-fade-in="3" data-hf-fade-out="6">{body}</aside>'
        )
        if occupied is not None:
            occupied.append((a, b))
    return layers


def _tile_ideas(layers, total):
    """At full presence the previous picture holds until the next spoken one."""
    parsed = []
    for layer in layers:
        found = re.search(r'data-hypit-start-frame="(\d+)" data-hypit-end-frame="(\d+)"', layer)
        if not found:
            continue
        parsed.append((int(found.group(1)), int(found.group(2)), layer))
    if not parsed:
        return layers
    parsed.sort(key=lambda item: item[0])
    tiled = []
    for index, (start, end, layer) in enumerate(parsed):
        begin = 0 if index == 0 else start
        stop = parsed[index + 1][0] if index + 1 < len(parsed) else total
        stop = max(begin + 1, min(total, stop))
        tiled.append(_retimed(layer, begin, stop) if (begin, stop) != (start, end) else layer)
    return tiled


def _retimed(layer, start, end):
    layer = re.sub(r'data-hypit-start-frame="\d+"', f'data-hypit-start-frame="{start}"', layer, count=1)
    return re.sub(r'data-hypit-end-frame="\d+"', f'data-hypit-end-frame="{end}"', layer, count=1)


def _limit_graphics(layers, total_frames, share, density=100):
    """Keep full-size graphics for the first share% of frames.

    10% of a 60 second picture is about 6 seconds. 100% returns the designed
    layers with their original timing. Density only drops layers; it does not
    scale a card.
    """
    share = max(0, min(100, int(share)))
    density = max(0, min(100, int(density)))
    graphic = [layer for layer in layers if _graphic_layer(layer)]
    rest = [layer for layer in layers if layer not in graphic]
    if (share >= 100 and density >= 100) or not graphic:
        return rest + graphic
    if share <= 0 or density <= 0 or total_frames <= 0:
        return rest
    horizon = total_frames if share >= 100 else max(1, int(round(total_frames * share / 100)))
    parsed = []
    for layer in graphic:
        found = re.search(r'data-hypit-start-frame="(\d+)" data-hypit-end-frame="(\d+)"', layer)
        if not found:
            continue
        start, end = int(found.group(1)), int(found.group(2))
        if end <= start or start >= horizon:
            continue
        stop = min(end, horizon)
        if stop <= start:
            continue
        parsed.append((start, stop, layer if stop == end else _retimed(layer, start, stop)))
    if not parsed:
        return rest
    if density < 100 and len(parsed) > 1:
        keep = max(1, int(round(len(parsed) * density / 100)))
        if keep < len(parsed):
            if keep == 1:
                picks = [len(parsed) // 2]
            else:
                picks = [round(i * (len(parsed) - 1) / (keep - 1)) for i in range(keep)]
            parsed = [parsed[index] for index in picks]
    return rest + [layer for _start, _end, layer in parsed]


def _broll_layers(inserts):
    """Short windows. The host file is not cut to make room for them."""
    layers = []
    for index, item in enumerate(list(inserts or [])[:2]):
        if not isinstance(item, dict) or not item.get('src'):
            continue
        try:
            start, end = float(item.get('start') or 0), float(item.get('end') or 0)
        except (TypeError, ValueError):
            continue
        a = max(0, int(round(start * FPS)))
        b = max(a + 1, int(round(end * FPS)))
        tag = _video(f'broll-{index}', item['src'], a, b, 0, 0.0, Fraction(1, 1), FPS, 1, 4, 4)
        layers.append(tag.replace('<video ', '<video class="hf-broll" ', 1))
        credit = html.escape(str(item.get('credit') or '')[:48])
        if credit:
            layers.append(
                f'<p class="hf-broll-credit" data-hypit-start-frame="{a}" data-hypit-end-frame="{b}" '
                f'data-hf-fade-in="4" data-hf-fade-out="4">{credit}</p>'
            )
    return layers


def composition(source, work, manual, width, height, language, style=None):
    """HyperFrames HTML. A paragraph, 口播, and a lone headcount digit are not drawn.

    One assembled picture is captured. A tag per clip makes Chrome decode every
    piece at once and the capture never finishes.
    """
    clips = [clip for clip in manual['clips'] if clip.get('approved', True)]
    total, duration = _picture_cut(source, work, clips, width, height)
    # One timeline for the whole file. Caption times stay where they were spoken.
    clips = [{'start': 0.0, 'end': duration, 'approved': True}]
    ranges = [(0.0, duration)]
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
    ideas = _speech_ideas(clips, ranges, manual.get('captions') or [], total, None)
    from .presentation_graphics import animation_brief, animation_levels
    levels = animation_levels(manual)
    if levels['coverage'] >= 100 and ideas:
        ideas = _tile_ideas(ideas, total)
    occupied = _spans(plates) + _spans(ideas)
    graphics = plates + _side_cards(clips, ranges, manual.get('captions') or [], language, total, style, occupied)
    graphics.extend(_host_chips(clips, ranges, manual.get('captions') or [], language, total, style, occupied))
    graphics.extend(ideas)
    filmed = max(5, min(100, int(levels['depth'] or levels['intensity'])))
    layers.extend(_limit_graphics(graphics, total, levels['coverage'], levels['density']))
    if levels['motion'] >= 80:
        horizon = total / FPS if levels['coverage'] >= 100 else total / FPS * levels['coverage'] / 100
        inserts = []
        for item in manual.get('_thematic_broll') or []:
            if not isinstance(item, dict):
                continue
            try:
                start = float(item.get('start') or 0)
            except (TypeError, ValueError):
                continue
            if start < horizon:
                inserts.append(item)
        layers.extend(_broll_layers(inserts))
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
    .hf-idea{{position:absolute;inset:0;z-index:4;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;padding:14% 12% 24%;color:#fff;text-align:center;opacity:0;background:radial-gradient(120% 80% at 50% 12%, #16325c 0%, #0b1830 58%, #08101f 100%)}}
    .hf-scene{{align-items:stretch;justify-content:flex-start;text-align:left;gap:0;padding:6% 6% 22%;background:#07080c;overflow:hidden}}
    .hf-scene-shard{{position:absolute;right:-8%;top:8%;width:46%;height:28%;background:#141820;transform:rotate(8deg);border-radius:18px;opacity:.9}}
    .hf-scene-head,.hf-scene-row b,.hf-stack b{{box-sizing:border-box;min-height:108px;border-radius:18px;border:1px solid rgba(255,255,255,.16);background:linear-gradient(180deg,#23262e,#101218);color:#fff;padding:18px 16px;box-shadow:0 18px 40px rgba(0,0,0,.45);overflow-wrap:anywhere}}
    .hf-scene-head{{display:flex;flex-direction:column;align-items:flex-start;justify-content:center;gap:10px;background:linear-gradient(160deg,#3a3420,#16140e)}}
    .hf-scene-head strong,.hf-stack strong,.hf-scene-row b{{font:800 {max(26, height // 24)}px/1.25 "Noto Sans CJK SC",sans-serif}}
    .hf-scene-head .hf-scene-figure,.hf-stack .hf-scene-figure{{font:800 {max(120, height // 7)}px/0.9 "Noto Sans CJK SC",sans-serif;color:#f2c14b;letter-spacing:-.04em}}
    .hf-scene-link{{display:block;height:64px;margin:0 18%;background:linear-gradient(#1f8f52,#0c3d22);clip-path:polygon(10% 0,90% 0,100% 100%,0 100%);transform-origin:top center}}
    .hf-scene-row{{display:flex;gap:12px}}
    .hf-scene-row b{{flex:1}}
    .hf-scene-row b:nth-child(1){{background:linear-gradient(160deg,#6a3494,#2a1244)}}
    .hf-scene-row b:nth-child(2){{background:linear-gradient(160deg,#1fa971,#0c5c40)}}
    .hf-scene-row b:nth-child(3){{background:linear-gradient(160deg,#8a6a22,#3d2e0c)}}
    .hf-stack{{display:flex;flex-direction:column;gap:14px;width:58%;margin-left:auto}}
    .hf-stack b:first-child{{background:linear-gradient(160deg,#6a3494,#2a1244)}}
    .hf-stack b:nth-child(2){{background:linear-gradient(160deg,#1fa971,#0c5c40)}}
    .hf-scene-caption{{position:absolute;left:7%;right:7%;bottom:3%;z-index:8;margin:0;text-align:left;font:700 {max(18, height // 36)}px/1.3 "Noto Sans CJK SC",sans-serif;overflow-wrap:anywhere;text-shadow:0 2px 8px #000}}
    .hf-broll{{position:absolute;left:8%;top:64%;width:40%;height:12%;z-index:5;object-fit:cover;border-radius:16px;box-shadow:0 0 0 3px #fff;opacity:0}}
    .hf-broll-credit{{position:absolute;left:8%;top:74%;width:40%;z-index:6;margin:0;color:#fff;font:600 11px/1.2 sans-serif;text-shadow:0 1px 4px #000;opacity:0;overflow:hidden;white-space:nowrap}}
    .hf-idea-mark{{width:0;height:0;border-left:46px solid transparent;border-right:46px solid transparent;border-bottom:78px solid #f2c14b}}
    .hf-idea-title{{max-width:78%;font:800 {max(28, height // 18)}px/1.2 "Noto Sans CJK SC",sans-serif}}
    .hf-idea-figure{{font:800 {max(72, height // 8)}px/1 "Noto Sans CJK SC",sans-serif;color:#f2c14b;letter-spacing:-.04em}}
    .hf-idea-step{{font:800 {max(64, height // 10)}px/1 "Noto Sans CJK SC",sans-serif;color:#7eb6ff}}
    .hf-idea-split{{display:flex;gap:18px;width:84%}}
    .hf-idea-split b{{flex:1;padding:18px 12px;border-radius:16px;background:rgba(255,255,255,.08);font:800 {max(22, height // 28)}px/1.25 "Noto Sans CJK SC",sans-serif}}
    .hf-idea-caption{{font:600 {max(16, height // 48)}px/1.2 "Noto Sans CJK SC",sans-serif;opacity:.72}}
    .hf-idea-track{{display:block;width:68%;height:10px;border-radius:10px;background:rgba(255,255,255,.22);overflow:hidden}}
    .hf-idea-fill{{display:block;width:0;height:100%;background:#f2c14b}}
    .hf-window .hf-card-title,.hf-mini .hf-card-title{{width:auto;padding:0;border-radius:0;background:none;font:700 {max(15, min(22, height // 52))}px/1.28 sans-serif;overflow-wrap:break-word}}
    .hf-window .hf-card-sub,.hf-mini .hf-card-sub{{width:auto;padding:0;border-radius:0;background:none;letter-spacing:0;font:600 {max(13, min(16, height // 64))}px/1.3 sans-serif;overflow-wrap:break-word;opacity:.9}}
    .hf-plate-label{{font:600 {max(14, height // 46)}px/1.2 sans-serif;letter-spacing:.06em;opacity:.78}}
    .hf-plate-value{{font:700 {max(36, height // 12)}px/1 sans-serif;margin-top:8px}}
    .hf-plate-track{{width:72%;height:10px;margin-top:18px;border-radius:10px;background:rgba(255,255,255,.22);overflow:hidden}}
    .hf-plate-fill{{height:100%;border-radius:10px;background:#d5f5c4}}
  </style>
</head>
<body>
  <div data-composition-id="lumen" data-card-motion="{levels['coverage']}" data-animation-intensity="{filmed}" data-animation-motion="{levels['motion']}" data-animation-density="{levels['density']}" data-card-left="0.070" data-card-top="0.150" data-card-width="0.860" data-card-height="0.700" data-avatar-d="0.280" data-start="0" data-no-timeline data-width="{width}" data-height="{height}" data-duration="{seconds}" data-fps="{FPS}/1" data-hypit-frame-count="{total}">
    {body}
  </div>
  <script>
    const fps = {FPS};
    const layers = [...document.querySelectorAll('[data-hypit-start-frame]')];
    const apply = (time) => {{
      const frame = Math.max(0, Math.round(Number(time || 0) * fps));
      const stage = document.querySelector('[data-composition-id]');
      const intensity = Math.max(5, Math.min(100, Number((stage && stage.getAttribute('data-animation-intensity')) || 100))) / 100;
      const motion = Math.max(0, Math.min(100, Number((stage && stage.getAttribute('data-animation-motion')) || 100))) / 100;
      for (const el of layers) {{
        const start = Number(el.getAttribute('data-hypit-start-frame'));
        const end = Number(el.getAttribute('data-hypit-end-frame'));
        const fadeIn = Number(el.getAttribute('data-hf-fade-in') || 0);
        const fadeOut = Number(el.getAttribute('data-hf-fade-out') || 0);
        let opacity = 0;
        const card = el.classList.contains('hf-board') || el.classList.contains('hf-idea') || el.classList.contains('hf-lower') || el.classList.contains('hf-card') || el.classList.contains('hf-plate') || el.classList.contains('hf-window') || el.classList.contains('hf-mini') || el.classList.contains('hf-chip');
        if (frame >= start && frame < end) {{
          const innFrames = card ? fadeIn * intensity : fadeIn;
          const outFrames = card ? fadeOut * intensity : fadeOut;
          const inn = innFrames > 0 ? Math.min(1, (frame - start + 1) / innFrames) : 1;
          const out = outFrames > 0 ? Math.min(1, (end - frame) / outFrames) : 1;
          opacity = Math.min(inn, out);
        }}
        el.style.opacity = String(opacity);
        const mark = el.querySelector('[data-visual-mark]');
        const fill = el.querySelector('.hf-idea-fill');
        if ((mark || fill) && frame >= start && frame < end) {{
          const span = Math.max(1, end - start);
          const travel = 36 * intensity * (Math.max(5, Math.min(100, Number((stage && stage.getAttribute('data-animation-motion')) || 100))) / 100);
          const along = (frame - start) / span;
          const dir = el.getAttribute('data-visual');
          if (mark && dir === 'up') mark.style.transform = 'translateY(' + Math.round((1 - along) * travel) + '%)';
          if (mark && dir === 'down') mark.style.transform = 'translateY(' + Math.round(along * travel) + '%) rotate(180deg)';
          if (fill) fill.style.width = Math.round(along * 100) + '%';
        }}
        if (card && el.classList.contains('hf-scene') && frame >= start && frame < end) {{
          const pieces = [...el.querySelectorAll('[data-hf-piece]')];
          const step = Math.round(16 * motion);
          const enter = Math.max(6, Math.round((8 + 14 * motion) * Math.max(0.45, intensity)));
          pieces.forEach((piece, index) => {{
            const delay = index * step;
            const arrived = Math.max(0, Math.min(1, (frame - start - delay + 1) / enter));
            const travel = Math.round((1 - arrived) * (index % 2 ? 180 : -200) * motion);
            const drift = Math.round(Math.sin((frame - start) / 20) * 18 * motion * arrived);
            const scale = motion < 0.02 ? 1 : (0.86 + 0.14 * arrived);
            piece.style.opacity = String(arrived);
            piece.style.transform = 'translate(' + travel + 'px,' + drift + 'px) scale(' + scale + ')';
          }});
          const link = el.querySelector('.hf-scene-link');
          if (link) link.style.transform = 'scaleY(' + (motion < 0.02 ? 1 : Math.max(0, Math.min(1, (frame - start - Math.max(step, 1)) / 28))) + ')';
        }} else if (card) {{
          const lift = Math.round((el.classList.contains('hf-board') ? 28 : 16) * intensity);
          const shift = Math.round((1 - opacity) * lift);
          el.style.transformOrigin = '50% 40%';
          el.style.transform = 'translateY(' + shift + 'px)';
        }}
      }}
      const video = document.getElementById('picture');
      const frameBox = video && video.parentElement;
      const covers = (el) => frame >= Number(el.getAttribute('data-hypit-start-frame')) && frame < Number(el.getAttribute('data-hypit-end-frame'));
      const plateOn = layers.some((el) => el.classList.contains('hf-plate') && covers(el));
      const boardOn = !plateOn && layers.some((el) => el.classList.contains('hf-board') && covers(el));
          const idea = layers.find((el) => el.classList.contains('hf-idea') && covers(el));
          const ideaOn = !!idea;
          const scene = idea && idea.getAttribute('data-scene');
      const avatar = plateOn || boardOn || ideaOn;
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
          if (scene === 'stack') {{
            cx = frameW * 0.24;
            cy = frameH * 0.36;
          }} else if (ideaOn && !plateOn) {{
            cx = scene === 'columns' ? frameW * 0.5 : frameW * 0.78;
            cy = frameH * 0.62;
          }} else if (boardOn && !plateOn) {{
            cx = frameW * 0.78;
            cy = frameH * 0.18;
          }}
          cx = Math.max(marginX + half, Math.min(frameW - marginX - half, cx));
          cy = Math.max(marginY + half, Math.min(frameH - marginY - half, cy));
          const captionTop = frameH * 0.80;
          cy = Math.min(cy, captionTop - half - 12);
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
        const hostStart = idea ? Number(idea.getAttribute('data-hypit-start-frame')) : frame;
        const hostIn = ideaOn ? Math.max(0, Math.min(1, (frame - hostStart + 1) / Math.max(8, Math.round(22 * Math.max(motion, 0.05))))) : 1;
        const hostSlide = Math.round((1 - hostIn) * frameW * 0.22 * motion);
        const hostSway = ideaOn ? Math.round(Math.sin(frame / 18) * 12 * hostIn * motion) : 0;
        if (avatar && scene === 'stack') {{
          const portraitW = Math.round(frameW * 0.34);
          const portraitH = Math.round(frameH * 0.28);
          video.style.width = portraitW + 'px';
          video.style.height = portraitH + 'px';
          video.style.left = Math.round(frameW * 0.06 - hostSlide) + 'px';
          video.style.top = Math.round(frameH * 0.2 + hostSway) + 'px';
          video.style.right = 'auto';
          video.style.bottom = 'auto';
          video.style.objectFit = 'cover';
          video.style.objectPosition = 'center 30%';
          video.style.borderRadius = '18px';
          video.style.zIndex = '6';
          video.style.boxShadow = '0 0 0 4px #fff';
        }} else if (avatar) {{
          video.style.width = box + 'px';
          video.style.height = box + 'px';
          video.style.left = Math.round(cx - half + hostSlide) + 'px';
          video.style.top = Math.round(cy - half + hostSway) + 'px';
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
    from .hypit_prompt import _look_line
    prompt = animation_brief(manual) + _look_line()
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
    """The source soundtrack, whole. It is not rebuilt from clip pieces."""
    del clips
    mixed = folder / 'hypit-audio.wav'
    ffmpeg(
        '-i', str(source), '-vn', '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2',
        str(mixed), timeout=600,
    )
    return mixed


def render_picture(source, folder, manual, width, height, metadata, asset_paths=None, language='en', board=None, voiceover=False):
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
    from .presentation_graphics import animation_levels
    if animation_levels(manual)['motion'] >= 80 and '_thematic_broll' not in manual:
        from .thematic_broll import attach
        manual['_thematic_broll'] = attach(manual, work)
    frame_count = composition(source, work, manual, width, height, language, style)
    if 'card_motion' in manual:
        (Path(folder) / 'animation-share.txt').write_text(str(_card_motion(manual)))
    from .hypit_prompt import author_source, write_author
    write_author(work, author_source(manual, width, height, board, language, voiceover=voiceover))
    shutil.copyfile(work / 'cut.mp4', work / 'source.mp4')
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
        audio = source
        if manual.get('voice_cleanup'):
            from .hypit_controls import clean_host
            audio = clean_host(audio, work)
        ffmpeg('-i', visual, '-i', audio, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', assembled, timeout=600)
    else:
        ffmpeg('-i', visual, '-c', 'copy', '-movflags', '+faststart', assembled, timeout=600)
    return assembled


def _presentation_page(width, height, seconds, frames, layers, prompt):
    body = '\n    '.join(layers)
    if '<?svml' in (prompt or '') or '<text:' in (prompt or ''):
        prompt = ''
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
    if '<?svml' in prompt or '<text:' in prompt:
        prompt = ''
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
