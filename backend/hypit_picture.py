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
import subprocess
from fractions import Fraction
from pathlib import Path

from .media import ffmpeg, run

log = logging.getLogger('lumen.hypit')
FPS = 30
FADE = 6
SCRIPT = Path(__file__).resolve().parent / 'hypit_render.mjs'


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


def spawn(argv, env):
    work = str(Path(argv[-1]).resolve().parent)
    subprocess.run(argv, check=True, env=env, timeout=45 * 60, cwd=work)


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


def _picture_cut(source, work, clips, width, height, picture_quality=False):
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
    if picture_quality:
        from .hypit_controls import apply_picture
        apply_picture(out, work, 0)
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
            f'<div class="hf-plate-label">{html.escape(title)}</div>'
            f'<div class="hf-plate-value">{html.escape(figure)}</div>'
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
    left = max(4.0, min(30.0, (float(card['x']) - float(card['w']) / 2) * 100))
    top = max(12.0, min(40.0, (float(card['y']) - float(card['h']) / 2) * 100))
    width = max(52.0, min(92.0, float(card['w']) * 100))
    height = max(36.0, min(78.0, float(card['h']) * 100))
    fill = str(stage.get('fill') or '10233f')
    ink = str(stage.get('ink') or 'ffffff')
    page = page.replace('left:7%;right:7%;top:22%;bottom:8%', f'left:{left:.1f}%;top:{top:.1f}%;width:{width:.1f}%;height:{height:.1f}%')
    page = page.replace('background:#10233f;color:#fff', f'background:#{fill};color:#{ink}')
    page = page.replace(
        'data-composition-id="lumen"',
        'data-composition-id="lumen" data-card-left="{left}" data-card-width="{width}"'.format(
            left=f'{left / 100:.3f}', width=f'{width / 100:.3f}',
        ),
    )
    avatar = stage.get('avatar') if isinstance(stage.get('avatar'), dict) else {}
    if avatar:
        page = page.replace(
            'data-composition-id="lumen"',
            'data-composition-id="lumen" data-avatar-x="{x}" data-avatar-y="{y}" data-avatar-d="{d}"'.format(
                x=f'{float(avatar["x"]):.3f}', y=f'{float(avatar["y"]):.3f}', d=f'{float(avatar["d"]):.3f}',
            ),
        )
    return page


def _side_cards(clips, ranges, captions, language, total, style=None):
    """Reference card language, filled with this video's facts. Not the reference picture."""
    layers = []
    seen = set()
    for caption in captions or []:
        if not isinstance(caption, dict):
            continue
        copied = _graphic_copy(caption, language)
        if not copied:
            continue
        title, sub = copied
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
        sub_html = f'<div class="hf-card-sub">{html.escape(sub)}</div>' if sub else ''
        layers.append(
            f'<aside class="hf-card" data-hf-avatar="1" data-hypit-start-frame="{a}" data-hypit-end-frame="{b}" '
            f'data-hf-fade-in="6" data-hf-fade-out="6">'
            f'<div class="hf-card-bar"></div>'
            f'<div class="hf-card-title">{html.escape(title)}</div>'
            f'{sub_html}'
            f'</aside>'
        )
    return layers


def _host_chips(clips, ranges, captions, language, total, style):
    """A reference host frame keeps the presenter and a small corner title."""
    layers = []
    seen = set()
    for caption in captions or []:
        if not isinstance(caption, dict):
            continue
        copied = _graphic_copy(caption, language)
        if not copied:
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
        title, sub = copied
        key = (title, int(start))
        if key in seen:
            continue
        seen.add(key)
        a = max(0, int(round(start * FPS)))
        b = max(a + 1, min(total, int(round(end * FPS))))
        sub_html = f'<div class="hf-card-sub">{html.escape(sub)}</div>' if sub else ''
        layers.append(
            f'<aside class="hf-chip" data-hypit-start-frame="{a}" data-hypit-end-frame="{b}" '
            f'data-hf-fade-in="5" data-hf-fade-out="5">'
            f'<div class="hf-card-title">{html.escape(title)}</div>{sub_html}</aside>'
        )
    return layers


def composition(source, work, manual, width, height, language, style=None):
    """HyperFrames HTML. A paragraph, 口播, and a lone headcount digit are not drawn.

    One assembled picture is captured. A tag per clip makes Chrome decode every
    piece at once and the capture never finishes.
    """
    clips = [clip for clip in manual['clips'] if clip.get('approved', True)]
    total, ranges = _picture_cut(source, work, clips, width, height, bool(manual.get('picture_quality')))
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
    layers.extend(_plates(clips, ranges, language, total))
    layers.extend(_side_cards(clips, ranges, manual.get('captions') or [], language, total, style))
    layers.extend(_host_chips(clips, ranges, manual.get('captions') or [], language, total, style))
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
    .hf-card,.hf-plate{{position:absolute;left:7%;right:7%;top:22%;bottom:8%;z-index:4;box-sizing:border-box;padding:22px 18px 26px;border-radius:28px;background:#10233f;color:#fff;text-align:left;opacity:0;box-shadow:0 18px 48px rgba(0,0,0,.45);display:flex;flex-direction:column;align-items:stretch;justify-content:flex-start;gap:14px;overflow:hidden}}
    .hf-chip{{position:absolute;left:5%;top:7%;width:46%;z-index:5;padding:12px 14px;border-radius:16px;background:#10233f;color:#fff;text-align:left;opacity:0;box-shadow:0 10px 24px rgba(0,0,0,.35)}}
    .hf-card-bar{{width:48px;height:6px;border-radius:6px;background:#7eb6ff;margin:8% 0 4px}}
    .hf-card-title{{box-sizing:border-box;width:100%;padding:14px 12px;border-radius:16px;background:rgba(255,255,255,.1);font:700 {max(22, height // 22)}px/1.12 sans-serif}}
    .hf-card-sub{{box-sizing:border-box;width:100%;padding:10px 12px;border-radius:14px;background:rgba(255,255,255,.06);font:600 {max(13, height // 48)}px/1.2 sans-serif;letter-spacing:.04em;opacity:.86}}
    .hf-chip .hf-card-title{{padding:0;background:none;font:700 {max(18, height // 32)}px/1.15 sans-serif}}
    .hf-chip .hf-card-sub{{padding:0;margin-top:4px;background:none;font:600 {max(12, height // 52)}px/1.2 sans-serif}}
    .hf-plate-label{{font:600 {max(14, height // 46)}px/1.2 sans-serif;letter-spacing:.06em;opacity:.78}}
    .hf-plate-value{{font:700 {max(36, height // 12)}px/1 sans-serif;margin-top:8px}}
    .hf-plate-track{{width:72%;height:10px;margin-top:18px;border-radius:10px;background:rgba(255,255,255,.22);overflow:hidden}}
    .hf-plate-fill{{height:100%;border-radius:10px;background:#d5f5c4}}
  </style>
</head>
<body>
  <div data-composition-id="lumen" data-start="0" data-no-timeline data-width="{width}" data-height="{height}" data-duration="{seconds}" data-fps="{FPS}/1" data-hypit-frame-count="{total}">
    {body}
  </div>
  <script>
    const fps = {FPS};
    const layers = [...document.querySelectorAll('[data-hypit-start-frame]')];
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
        if (el.classList.contains('hf-card') || el.classList.contains('hf-plate')) {{
          el.style.transform = 'translateY(' + Math.round((1 - opacity) * 36) + 'px)';
        }}
      }}
      const video = document.getElementById('picture');
      const frameBox = video && video.parentElement;
      const avatar = layers.some((el) => el.hasAttribute('data-hf-avatar') && Number(el.style.opacity) > 0.45);
      const root = video && video.parentElement;
      const ax = root ? Number(root.getAttribute('data-avatar-x') || 0.78) : 0.78;
      const ay = root ? Number(root.getAttribute('data-avatar-y') || 0.12) : 0.12;
      const ad = root ? Number(root.getAttribute('data-avatar-d') || 0.30) : 0.30;
        if (video && frameBox) {{
          const cardLeft = Number(root.getAttribute('data-card-left') || 0.07);
          const cardWidth = Number(root.getAttribute('data-card-width') || 0.86);
          const copyInset = Math.max(0, Math.min(0.42, (ax + ad / 2) - cardLeft));
          const pad = avatar && ax < 0.55 ? Math.round(copyInset / Math.max(0.2, cardWidth) * 100) : 6;
          for (const el of layers) {{
            if (el.classList.contains('hf-card') || el.classList.contains('hf-plate')) el.style.paddingLeft = pad + '%';
          }}
        if (avatar) {{
          const box = Math.round(frameBox.clientWidth * (ad > 0.12 ? ad : 0.30));
          video.style.width = box + 'px';
          video.style.height = box + 'px';
          video.style.left = Math.round(frameBox.clientWidth * ax - box / 2) + 'px';
          video.style.top = Math.round(frameBox.clientHeight * ay - box / 2) + 'px';
          video.style.right = 'auto';
          video.style.bottom = 'auto';
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
    (work / 'index.html').write_text(_apply_style(page, style))
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
        log.warning('hypit capture failed: %s', exc)
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
