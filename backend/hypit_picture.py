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
    root = _root()
    tsx = root / 'node_modules' / '.bin' / 'tsx'
    node = os.environ.get('HYPIT_NODE') or 'node'
    return [node, str(tsx), str(SCRIPT), str(job_path)], root, tsx


def spawn(argv, env):
    subprocess.run(argv, check=True, env=env, timeout=45 * 60)


def _fps(path):
    out, _ = run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'json', str(path)], 30)
    rate = ((json.loads(out or '{}').get('streams') or [{}])[0]).get('r_frame_rate') or '30/1'
    num, den = (rate.split('/') + ['1'])[:2]
    num, den = int(num), int(den)
    if num <= 0 or den <= 0:
        return 30, 1
    return num, den


def _link(work, name, path):
    dest = work / name
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    dest.symlink_to(Path(path).resolve())
    return name


def _rate(speed, src_num, src_den, slot_frames, duration):
    source_frames = Fraction(speed) * Fraction(duration) * Fraction(src_num, src_den)
    rate = source_frames / Fraction(max(1, slot_frames))
    rate = rate.limit_denominator(100000)
    if rate <= 0:
        rate = Fraction(1, 1)
    return rate


def _caption_line(caption, language):
    if str(language).startswith('zh'):
        text = caption.get('zh') or caption.get('original') or caption.get('en') or ''
    else:
        text = caption.get('en') or caption.get('original') or caption.get('zh') or ''
    text = ' '.join(str(text).split())
    if not text or text == '口播' or text.isdigit():
        return ''
    return text


def _caption_spans(caption, clips):
    cursor = 0.0
    spans = []
    for clip in clips:
        length = float(clip['end']) - float(clip['start'])
        start = max(float(caption['start']), float(clip['start']))
        end = min(float(caption['end']), float(clip['end']))
        if end > start:
            spans.append((cursor + (start - float(clip['start'])), cursor + (end - float(clip['start']))))
        cursor += length
    return spans


def composition(source, work, manual, width, height, language):
    """HyperFrames HTML. Cards, 口播 labels, and lone number plates are not drawn."""
    clips = [clip for clip in manual['clips'] if clip.get('approved', True)]
    src_num, src_den = _fps(source)
    source_name = _link(work, 'source.mp4', source)
    layers = []
    cursor = 0
    total = 0
    for index, clip in enumerate(clips):
        duration = float(clip['end']) - float(clip['start'])
        frames = max(1, int(round(duration * FPS)))
        fade_in, fade_out = (0, 0)
        if frames >= FADE * 3:
            fade_in = FADE if index else 0
            fade_out = FADE if index < len(clips) - 1 else 0
        start = max(0, cursor - fade_in)
        end = cursor + frames
        slot = end - start
        speed = min(2.0, max(0.5, float(clip.get('speed') or 1)))
        origin = int(round(float(clip['start']) * src_num / src_den))
        rate = _rate(speed, src_num, src_den, slot, duration)
        layers.append(_video(
            f'clip-{index:03d}', source_name, start, end, origin, rate, src_num, src_den, fade_in, fade_out,
        ))
        _overlay_media(layers, work, source, clip, index, cursor, frames)
        total = end
        cursor += frames
    if manual.get('subtitles'):
        for index, caption in enumerate(manual.get('captions') or []):
            line = _caption_line(caption, language)
            if not line:
                continue
            for span_index, (start, end) in enumerate(_caption_spans(caption, clips)):
                a = max(0, int(round(start * FPS)))
                b = max(a + 1, int(round(end * FPS)))
                layers.append(
                    f'<div class="hf-caption" data-hypit-start-frame="{a}" data-hypit-end-frame="{min(b, total)}" '
                    f'data-hf-fade-in="4" data-hf-fade-out="4">{html.escape(line)}</div>'
                )
                if span_index > 8:
                    break
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
    .hf-caption{{position:absolute;left:8%;right:8%;bottom:12%;z-index:4;text-align:center;color:#fff;font:600 {max(22, height // 28)}px/1.25 sans-serif;text-shadow:0 2px 10px #000;opacity:0}}
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
      }}
    }};
    apply(0);
    window.addEventListener('hf-seek', (event) => apply(event.detail && event.detail.time));
  </script>
</body>
</html>
'''
    (work / 'index.html').write_text(page)
    return total


def _video(ident, src, start, end, origin, rate, src_num, src_den, fade_in, fade_out):
    return (
        f'<video id="{ident}" src="{src}" muted playsinline '
        f'data-hypit-start-frame="{start}" data-hypit-end-frame="{end}" '
        f'data-hypit-source-frame="{origin}/1" data-hypit-source-rate="{rate.numerator}/{rate.denominator}" '
        f'data-hypit-source-fps="{src_num}/{src_den}" '
        f'data-hf-fade-in="{fade_in}" data-hf-fade-out="{fade_out}"></video>'
    )


def _overlay_media(layers, work, source, clip, index, cursor, frames):
    broll = clip.get('external_broll') or {}
    path = clip.get('_hypit_broll')
    if path:
        name = _link(work, f'broll-{index:03d}.mp4', path)
        local = max(0.0, float(broll.get('start') or 0))
        local_end = min(frames / FPS, float(broll.get('end') or frames / FPS))
        if local_end - local >= 0.08:
            src_num, src_den = _fps(path)
            origin = int(round(float(broll.get('source_start') or 0) * src_num / src_den))
            start = cursor + int(round(local * FPS))
            end = cursor + max(int(round(local * FPS)) + 1, int(round(local_end * FPS)))
            duration = (end - start) / FPS
            rate = _rate(1, src_num, src_den, end - start, duration)
            layers.append(_video(f'broll-{index:03d}', name, start, end, origin, rate, src_num, src_den, 4, 4))
    insert = clip.get('_hypit_insert')
    if insert:
        path, at, local_start, local_end, _available = insert
        name = _link(work, f'insert-{index:03d}.mp4', path)
        src_num, src_den = _fps(path)
        origin = int(round(float(at) * src_num / src_den))
        start = cursor + int(round(float(local_start) * FPS))
        end = cursor + max(int(round(float(local_start) * FPS)) + 1, int(round(float(local_end) * FPS)))
        end = min(end, cursor + frames)
        if end > start:
            duration = (end - start) / FPS
            rate = _rate(1, src_num, src_den, end - start, duration)
            layers.append(_video(f'insert-{index:03d}', name, start, end, origin, rate, src_num, src_den, 4, 4))
    still = clip.get('_hypit_still')
    if still:
        suffix = Path(still).suffix.lower() or '.png'
        if suffix not in {'.png', '.jpg', '.jpeg', '.webp'}:
            suffix = '.png'
        name = _link(work, f'still-{index:03d}{suffix}', still)
        layers.append(
            f'<img class="hf-still" src="{name}" data-hypit-start-frame="{cursor}" data-hypit-end-frame="{cursor + frames}" '
            f'data-hf-fade-in="4" data-hf-fade-out="4"/>'
        )


def _host_audio(source, folder, clips):
    pieces = []
    for index, clip in enumerate(clips):
        start = float(clip['start'])
        length = float(clip['end']) - start
        speed = min(2.0, max(0.5, float(clip.get('speed') or 1)))
        piece = folder / f'hypit-a-{index:03d}.wav'
        take = length * speed
        args = ['-ss', f'{start:.3f}', '-t', f'{take:.3f}', '-i', source, '-vn', '-ac', '2', '-ar', '48000']
        if abs(speed - 1) > 0.04:
            args += ['-af', f'atempo={speed:.4f}']
        args += ['-t', f'{length:.3f}', piece]
        ffmpeg(*args, timeout=180)
        pieces.append(piece)
    if len(pieces) == 1:
        return pieces[0]
    listing = folder / 'hypit-audio.txt'
    listing.write_text(''.join(f"file '{path.name}'\n" for path in pieces))
    mixed = folder / 'hypit-audio.wav'
    ffmpeg('-f', 'concat', '-safe', '1', '-i', listing, '-c', 'copy', mixed, timeout=180)
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
    frame_count = composition(source, work, manual, width, height, language)
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
        ffmpeg('-i', visual, '-i', audio, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', assembled, timeout=600)
    else:
        ffmpeg('-i', visual, '-c', 'copy', '-movflags', '+faststart', assembled, timeout=600)
    return assembled
