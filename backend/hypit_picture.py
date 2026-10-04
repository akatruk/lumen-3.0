"""Style-match pictures are one Hypit build of one prompt.

Hypit is Apache License 2.0 with additional conditions. Lumen does not vendor
that source. The prompt names the percent and the spoken words. ``hypit build``
returns one video. Lumen does not cut the footage into scenes or set a
parameter on each frame.
"""
import json
import logging
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

from .media import ffmpeg, run

log = logging.getLogger('lumen.hypit')
FPS = 30
SCRIPT = Path(__file__).resolve().parent / 'hypit_render.mjs'
_LEAK = re.compile(
    r'(?i)(api[_-]?key|secret|token|password|authorization|bearer)\s*[:=]\s*\S+'
    r'|sk-[A-Za-z0-9]{8,}|BEGIN [A-Z ]*PRIVATE KEY'
)


def engine_for(context):
    """Every picture is one Hypit build. A missing reference does not pick another renderer."""
    del context
    return 'hypit'


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


def _software_chrome(work, chrome):
    """Launch SwiftShader without the flags that blank the screenshot.

    Hardware ANGLE/EGL closed the target on this host. Explicit software mode
    still appends ``--disable-gpu-compositing``, and a wrapper that added
    ``--disable-gpu`` made ``Page.captureScreenshot`` return "Unable to capture
    screenshot" at frame 92 of the card composition, with empty Chrome stderr.
    Those two flags leave ``fromSurface`` with nothing to copy. SwiftShader
    stays; both flags are removed before Chrome starts.
    """
    wrapper = Path(work) / 'chrome-software'
    wrapper.write_text(
        '#!/usr/bin/env python3\n'
        'import os, sys\n'
        f'chrome = {chrome!r}\n'
        'skip = {"--disable-gpu", "--disable-gpu-compositing"}\n'
        'args = [arg for arg in sys.argv[1:] if arg not in skip]\n'
        'os.execv(chrome, [chrome, *args])\n'
    )
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(wrapper)


def _runtime_profile(work):
    """Local picture and alignment only. A hosted key is not part of this prompt."""
    chrome = _chrome()
    # This host has no GPU. Hardware ANGLE/EGL closed the target. Software
    # SwiftShader is selected, and the wrapper drops ``--disable-gpu`` and
    # ``--disable-gpu-compositing``, which blank Page.captureScreenshot.
    # One browser is already the whole capture. The default decoded set is
    # 1 GiB and the pending PNG pipe is 256 MiB; this machine has 3.9 GiB,
    # and that capture reached the 2.7 GiB worker cap. Keep one second of
    # source frames and a short PNG queue so the snapshot copy still has memory.
    picture = {
        'use': '@hypit/provider-hyperframes-local',
        'config': {
            'workers': 1,
            'defaultConcurrency': 1,
            'browserGpu': 'software',
            'maxDecodedSourceBytes': 64 * 1024 * 1024,
            'maxPendingFrameBytes': 32 * 1024 * 1024,
        },
    }
    if chrome:
        picture['config']['chromePath'] = _software_chrome(work, chrome)
    profile = {
        'format': 'hypit.runtime-local@1',
        'dataRoot': '.hypit/runtimes/local',
        'endpoints': {
            'media.local': {'use': '@hypit/provider-media-local'},
            'hyperframes.local': picture,
            'whisperx.local': {
                'use': '@hypit/provider-whisperx-local',
                'config': {'alignmentLanguages': ['zh', 'en', 'ru']},
            },
        },
    }
    path = Path(work) / 'hypit.runtime.json'
    path.write_text(json.dumps(profile))
    return path


def _alignment_ready():
    """The local aligner is already answering. A second install is not required."""
    import urllib.request
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=2) as response:
            body = json.loads(response.read().decode())
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return isinstance(body, dict) and body.get('ok') is True and body.get('protocol') == 'hypit.whisperx-service@1'


def deliver(work):
    """Build the one prompt and write visual.mp4. The source is not spliced."""
    work = Path(work)
    binary = _root() / 'bin' / 'hypit.mjs'
    if not binary.is_file():
        raise RuntimeError('hypit_unavailable')
    node = os.environ.get('HYPIT_NODE') or 'node'
    env = os.environ.copy()
    env['HYPIT_ROOT'] = str(_root())
    from .config import settings
    home = Path(settings.data_dir) / 'hypit-home'
    home.mkdir(parents=True, exist_ok=True)
    env['HOME'] = str(home)
    env['XDG_CACHE_HOME'] = str(home / '.cache')
    scratch = home / 'tmp'
    scratch.mkdir(parents=True, exist_ok=True)
    env['TMPDIR'] = str(scratch)
    uv_bin = home / '.local' / 'bin'
    if uv_bin.is_dir():
        env['PATH'] = str(uv_bin) + os.pathsep + env.get('PATH', '')

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
    if not _alignment_ready():
        cli(['programs', 'up', '--runtime', 'hypit.runtime.json', '--max-wait-ms', '600000'])
    completed = cli(['build', 'build.svrun', '--follow', '--json'])
    build_id = _build_payload(completed.stdout)['build']['id']
    visual = work / 'visual.mp4'
    cli(['get', build_id, '--output', 'final.video', '--to', str(visual)])
    if not visual.is_file() or visual.stat().st_size < 32:
        raise RuntimeError('hypit_unavailable')
    return visual


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

def _card_motion(manual):
    """How far the cards animate. A missing value keeps the full designed motion."""
    if not isinstance(manual, dict) or 'card_motion' not in manual:
        return 100
    try:
        return max(0, min(100, int(manual.get('card_motion') or 0)))
    except (TypeError, ValueError):
        return 100

def _cyrillic_face(work):
    """Copy the installed Cyrillic face next to the author source.

    The open catalog ships Noto Sans as a Latin subset. The Cyrillic file is
    already in the local Hypit install, so the bottom line can draw Russian
    without a hosted key.
    """
    found = sorted(_root().glob(
        'node_modules/.pnpm/@fontsource-variable+noto-sans@*/'
        'node_modules/@fontsource-variable/noto-sans/files/noto-sans-cyrillic-wght-normal.woff2'
    ))
    if not found:
        return None
    dest = Path(work) / 'fonts'
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(found[-1], dest / 'noto-sans-cyrillic.woff2')
    return './fonts/noto-sans-cyrillic.woff2'


def _piece_duration(path):
    out, _ = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(path)], 30)
    try:
        return float((json.loads(out or '{}').get('format') or {}).get('duration') or 0)
    except (TypeError, ValueError):
        return 0.0


def _video_program_seconds(path):
    """Seconds Hypit keeps for span-authority=video: the video frame count at 30fps.

    The container can be longer than the picture (audio, or -shortest dropping
    the last frames). A window written against that longer number ends outside
    ProgramSpace.
    """
    out, _ = run([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=nb_frames,duration', '-of', 'json', str(path),
    ], 30)
    try:
        stream = (json.loads(out or '{}').get('streams') or [{}])[0]
    except (TypeError, ValueError):
        return 0.0
    try:
        frames = int(stream.get('nb_frames') or 0)
    except (TypeError, ValueError):
        frames = 0
    if frames > 0:
        return frames / FPS
    try:
        return float(stream.get('duration') or 0)
    except (TypeError, ValueError):
        return 0.0


def stage_prompt_inputs(source, work):
    """Copy the project's uploads to the names in the working Hypit request.

    ``reference_source`` is ``reference video``. Each ``references/*/source``
    follows as ``reference video 2`` and so on. The picture Hypit films, already
    written as ``source.mp4``, is also ``src video 2``.
    """
    project = Path(source).resolve().parent
    work = Path(work)
    reference = project / 'reference_source'
    if reference.is_file() and reference.stat().st_size >= 32:
        shutil.copyfile(reference, work / 'reference video')
    numbered = []
    folder = project / 'references'
    if folder.is_dir():
        numbered = [
            path for path in sorted(folder.glob('*/source'))
            if path.is_file() and path.stat().st_size >= 32
        ]
    start = 2 if (work / 'reference video').is_file() else 1
    for offset, path in enumerate(numbered):
        index = start + offset
        name = 'reference video' if index == 1 else f'reference video {index}'
        shutil.copyfile(path, work / name)
    footage = work / 'source.mp4'
    if footage.is_file():
        shutil.copyfile(footage, work / 'src video 2')


def render_picture(source, folder, manual, width, height, metadata, asset_paths=None, language='en', board=None, voiceover=False):
    """Hand the constructor prompt to Hypit. The page of cards is not filmed."""
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
    saved = dict(manual)
    manual = dict(manual)
    manual['clips'] = shaped
    from .style_match import reference_video
    from .style_vision import read_style
    reference = reference_video(Path(source).resolve().parent)
    try:
        style = read_style(reference) if reference else None
    except Exception:
        style = None
    from .hypit_prompt import author_source, reference_shots, write_author
    shots = reference_shots(source)
    duration = _picture_cut(source, work, clips, width, height)[1]
    if 'card_motion' in manual:
        (Path(folder) / 'animation-share.txt').write_text(str(_card_motion(manual)))
    face = None
    try:
        face = _cyrillic_face(work)
    except OSError:
        face = None
    if metadata.get('has_audio'):
        ffmpeg(
            '-i', work / 'cut.mp4', '-i', str(source),
            '-map', '0:v:0', '-map', '1:a:0',
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest',
            '-movflags', '+faststart', work / 'source.mp4', timeout=600,
        )
    else:
        shutil.copyfile(work / 'cut.mp4', work / 'source.mp4')
    stage_prompt_inputs(source, work)
    program = _video_program_seconds(work / 'source.mp4')
    if program <= 0:
        program = duration
    write_author(work, author_source(
        saved, width, height, board, language, voiceover=voiceover, reference=shots, style=style,
        duration=program, cyrillic_font=face,
    ))
    page = work / 'index.html'
    if page.is_file():
        page.unlink()
    try:
        deliver(work)
    except RuntimeError:
        log.warning('hypit build failed')
        raise
    finally:
        if page.is_file():
            page.unlink()
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

