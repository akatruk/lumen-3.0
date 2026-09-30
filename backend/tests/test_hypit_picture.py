"""Style-match renders call Hypit's capture. The fixture never contacts a network."""
import inspect
import json
import shutil
from pathlib import Path

import pytest

from backend.hypit_picture import engine_for
from backend.media import ffmpeg, probe, render, run
from backend.schemas import Analysis
from backend.worker import render_job

T = {'en': 'Synthetic fixture, not AI analysis', 'zh': '合成测试素材，非 AI 分析'}


def test_chrome_path_uses_the_explicit_browser(monkeypatch, tmp_path):
    browser = tmp_path / 'chrome'
    browser.write_text('')
    monkeypatch.setenv('HYPIT_CHROME', str(browser))
    from backend.hypit_picture import _chrome
    assert _chrome() == str(browser)


def test_style_match_selects_the_hypit_engine():
    assert engine_for({'style_match': True}) == 'hypit'
    assert engine_for({'style_match': False}) is None
    assert engine_for(None) is None
    source = inspect.getsource(render_job)
    assert 'engine_for' in source and 'picture_engine' in source


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg required')
def test_style_match_render_invokes_hypit_capture(tmp_path, monkeypatch):
    src = tmp_path / 'source.mp4'
    ffmpeg(
        '-f', 'lavfi', '-i', 'color=c=red:s=160x240:d=2:r=30',
        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', src,
    )
    root = tmp_path / 'hypit-root'
    cli = root / 'node_modules' / 'tsx' / 'dist'
    cli.mkdir(parents=True)
    (cli / 'cli.mjs').write_text('')
    monkeypatch.setenv('HYPIT_ROOT', str(root))
    seen = {}

    def fake_spawn(argv, env):
        job = json.loads(Path(argv[-1]).read_text())
        seen['argv'] = argv
        seen['html'] = (Path(job['directory']) / 'index.html').read_text()
        seen['root'] = env['HYPIT_ROOT']
        frames = job['frameCount']
        ffmpeg(
            '-f', 'lavfi', '-i', f'color=c=blue:s={job["width"]}x{job["height"]}:d={frames / 30:.3f}:r=30',
            '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', Path(job['directory']) / 'visual.mp4',
        )

    monkeypatch.setattr('backend.hypit_picture.spawn', fake_spawn)
    analysis = Analysis(
        summary=T, strongest_moment=T, audience=T,
        scores=[{'category': 'clarity', 'value': 50, 'reason': T}],
        scenes=[{'start': 0, 'end': 2, 'title': T, 'observation': T, 'role': 'context'}],
        transcript=[], recommendations=[], uncertainties=[],
    )
    card = {
        'kind': 'number', 'start': 0, 'end': 1,
        'title': {'en': 'Shareholders', 'zh': '三名股东'},
        'primary': {'en': '3', 'zh': '3'},
        'source': {'en': 'Narration', 'zh': '口播'},
    }
    edit = {
        'clips': [
            {'start': 0, 'end': 1, 'text': '口播', 'card': card, 'transition': 'wipe-down'},
            {'start': 1, 'end': 2, 'transition': 'diagbl', 'zoom': 1, 'zoom_end': 1.4, 'y': 0.4,
             'grade': {'contrast': 1.08, 'gamma': 0.95, 'bs': 0.04}, 'shadow': True, 'shade': 0.5, 'card': {
                'kind': 'bar_chart', 'start': 0.1, 'end': 0.9, 'animation': 'none',
                'title': {'en': 'Foreign share', 'zh': '外资比例'},
                'primary': {'en': '49%', 'zh': '49%'},
                'source': {'en': 'Narration', 'zh': '旁白'},
                'items': [
                    {'label': {'en': 'Foreign share', 'zh': '外资比例'}, 'value': 49},
                    {'label': {'en': 'Full', 'zh': '全部'}, 'value': 100},
                ],
            }},
        ],
        'captions': [
            {'start': 0.2, 'end': 1.4, 'original': '三名股东开会', 'en': 'Three shareholders meet', 'zh': '三名股东开会'},
            {'start': 1.0, 'end': 1.8, 'original': '管理逻辑', 'en': 'Governance logic also differs and keeps a paragraph across the face of the speaker', 'zh': '管理逻辑也不同，中国强调法人代表，泰国更看重的是董事权限'},
        ],
        'subtitles': True,
        'voice_cleanup': True,
        'presentation_share': 100,
    }
    result = render(src, tmp_path, probe(src), analysis, [], 'zh', 'original', manual=edit, picture_engine='hypit')
    assert seen['argv'][2].endswith('hypit_render.mjs')
    assert seen['root'] == str(root)
    html = seen['html']
    assert 'data-composition-id="lumen"' in html
    assert 'data-hypit-start-frame=' in html
    assert 'data-hypit-source-fps=' in html
    assert 'data-start="0.000"' in html and 'data-end="' in html and 'data-media-start="0.000"' in html
    assert 'data-has-audio="false"' in html
    assert '三名股东开会' in html
    assert '口播' not in html and 'Shareholders' not in html and '>3<' not in html
    assert 'Governance logic also differs' not in html
    assert '股东结构' not in html and '董事权限' not in html
    assert 'hf-board' in html and '外资比例' in html and '49%' in html
    assert 'class="hf-plate"' in html and 'hf-board hf-plate' not in html
    assert '<text' not in html and 'render:Video' not in html and '<?svml' not in html
    svml = (tmp_path / 'hypit' / 'main.svml').read_text()
    assert 'during="program"' in svml and '三名股东开会' in svml and '<render:Video id="final"' in svml
    assert (tmp_path / 'hypit' / 'recipes.svs').is_file() and (tmp_path / 'hypit' / 'build.svrun').is_file()
    assert 'data-card-motion="100"' in html
    assert '(el.classList.contains(\'hf-board\') ? 28 : 16) * motion' in html
    assert (tmp_path / 'animation-share.txt').read_text() == '100'
    from backend.hypit_picture import composition
    quiet = tmp_path / 'motion-zero'
    quiet.mkdir()
    composition(src, quiet, {**edit, 'card_motion': 0}, 160, 240, 'zh')
    gone = (quiet / 'index.html').read_text()
    assert 'data-card-motion="0"' in gone and '外资比例' not in gone and '三名股东开会' in gone
    mid_dir = tmp_path / 'motion-mid'
    mid_dir.mkdir()
    composition(src, mid_dir, {**edit, 'card_motion': 10}, 160, 240, 'zh')
    mid = (mid_dir / 'index.html').read_text()
    assert 'data-card-motion="10"' in mid and 'data-card-motion="100"' not in mid

    import re

    def covered(page):
        return sum(
            int(end) - int(start)
            for start, end in re.findall(
                r'class="hf-(?:plate|board|lower|window|mini|chip)\b[^"]*"[^>]*data-hypit-start-frame="(\d+)" data-hypit-end-frame="(\d+)"',
                page,
            )
        )

    total = int(re.search(r'data-hypit-frame-count="(\d+)"', html).group(1))
    horizon = max(1, int(round(total * 0.1)))
    graphic_ends = [
        int(end)
        for _start, end in re.findall(
            r'class="hf-(?:plate|board|lower|window|mini|chip)\b[^"]*"[^>]*data-hypit-start-frame="(\d+)" data-hypit-end-frame="(\d+)"',
            mid,
        )
    ]
    assert covered(html) > covered(mid)
    assert graphic_ends and max(graphic_ends) <= horizon + 1
    assert 0 < covered(mid) <= horizon + 3
    assert 'boardOn ? 0.78' not in html and 'marginY' in html
    assert 'data-hf-avatar="1"' in html and 'hf-board-figure' in html
    assert not list(tmp_path.glob('*.ass'))
    cleanup = json.loads((tmp_path / 'hypit' / 'voice-cleanup.json').read_text())
    assert cleanup['control'] == 'voice_cleanup' and cleanup['stem'] == 'host'
    assert (tmp_path / 'hypit' / 'host-cleaned.wav').is_file()
    assert not list((tmp_path / 'hypit').glob('piece-*.mp4'))
    picture = (tmp_path / 'hypit' / 'picture.txt').read_text()
    assert 'concat=n=2:v=1:a=0' in picture and 'file ' not in picture
    cut = float((json.loads(run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(tmp_path / 'hypit' / 'cut.mp4')],
        30,
    )[0])['format'] or {}).get('duration') or 0)
    assert abs(cut - 2) < 0.08
    assert result['metadata']['has_audio']
    assert abs(result['metadata']['duration'] - 2) < 0.6
    streams = json.loads(run(
        ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,duration', '-of', 'json', str(tmp_path / 'result.mp4')],
        30,
    )[0])['streams']
    video = float(next(item['duration'] for item in streams if item['codec_type'] == 'video'))
    audio = float(next(item['duration'] for item in streams if item['codec_type'] == 'audio'))
    assert abs(video - audio) < 0.2


def test_a_lower_third_shows_its_title_once_and_yields_when_a_plate_is_up():
    from backend.hypit_picture import _lower_html, _side_cards

    block = _lower_html('注册公司', 'Company setup', 'Many business owners', 1, 10, 40)
    assert block.count('注册公司') == 1
    assert 'Company setup' in block and 'Many business owners' not in block
    assert 'hf-chapter' not in block and 'hf-lower-title' not in block
    captions = [{'start': 0.2, 'end': 2.0, 'zh': '外资比例 49%', 'en': 'Foreign share 49%', 'original': '外资比例 49%'}]
    blocked = _side_cards([{'start': 0, 'end': 3}], [(0.0, 3.0)], captions, 'zh', 90, None, [(0, 90)])
    assert blocked == []


def test_a_host_moment_keeps_a_corner_title():
    from backend.hypit_picture import _host_chips, _piece_vf, _side_cards

    style = {
        'frames': [{'at': 0.0, 'kind': 'host'}, {'at': 0.5, 'kind': 'stage'}, {'at': 0.8, 'kind': 'plate'}, {'at': 1.0, 'kind': 'host'}],
        'stage': {'fill': '282a44', 'ink': 'ffffff'},
    }
    clips = [{'start': 0, 'end': 2}]
    ranges = [(0.0, 2.0)]
    captions = [{'start': 0.1, 'end': 1.2, 'zh': '三名股东开会', 'en': 'Three shareholders meet', 'original': '三名股东开会'}]
    cards = _side_cards(clips, ranges, captions, 'en', 60, style)
    chips = _host_chips(clips, ranges, captions, 'en', 60, style)
    assert cards == []
    assert len(chips) == 1
    assert 'hf-lower' in chips[0] and chips[0].count('股东结构') == 1
    assert 'hf-chapter' not in chips[0] and 'hf-lower-title' not in chips[0]
    assert 'data-hf-avatar' not in chips[0]
    look, rate = _piece_vf({
        'zoom': 1, 'zoom_end': 1.35, 'x': 0.5, 'y': 0.62, 'speed': 1,
        'grade': {'contrast': 1.1, 'brightness': 0.02, 'saturation': 0.9, 'gamma': 1.0, 'bs': 0.05},
        'shadow': True, 'shade': 0.4, 'key_side': 'left', 'key_amount': 0.2,
    }, 1080, 1920, 2)
    assert rate == 1
    assert 'zoompan=' in look
    assert 'eq=contrast=1.1000' in look
    assert 'vignette=angle=0.400' in look
    assert "geq=lum='lum(X,Y)+" in look
    plain, _plain_rate = _piece_vf({'zoom': 1, 'x': 0.5, 'y': 0.5, 'speed': 1}, 1080, 1920, 1)
    assert 'eq=' not in plain and 'vignette=' not in plain and 'zoompan=' not in plain
    pushed, _pushed_rate = _piece_vf({
        'zoom': 1, 'zoom_end': 1.26, 'x': 0.5, 'y': 0.5, 'x_end': 0.5, 'y_end': 0.5, 'speed': 1,
    }, 720, 1280, 63)
    assert 'zoompan=' not in pushed and 'scale=iw*2' not in pushed


def test_hypit_controls_name_cleanup_quality_and_leave_generation_closed():
    from backend.hypit_controls import controls_for, picture_program, run_generate

    assert controls_for({'voice_cleanup': True, 'picture_quality': True}) == ['voice_cleanup', 'picture_quality']
    assert controls_for({}) == []
    program = picture_program()
    assert program[0]['kind'] == 'denoise' and program[0]['method'] == 'nlm-ycrcb'
    assert program[0]['lumaStrength'] == 2 and program[0]['chromaStrength'] == 10
    assert program[0]['saturationRecovery'] == 1.02
    assert program[1]['kind'] == 'sharpen' and program[2] == {'kind': 'encode', 'format': 'png'}
    with pytest.raises(RuntimeError, match='hypit_generation_unavailable'):
        run_generate()


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg required')
def test_picture_quality_is_not_part_of_the_render(tmp_path, monkeypatch):
    src = tmp_path / 'source.mp4'
    ffmpeg(
        '-f', 'lavfi', '-i', 'color=c=red:s=160x240:d=1:r=30',
        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', src,
    )
    root = tmp_path / 'hypit-root'
    cli = root / 'node_modules' / 'tsx' / 'dist'
    cli.mkdir(parents=True)
    (cli / 'cli.mjs').write_text('')
    monkeypatch.setenv('HYPIT_ROOT', str(root))
    seen = {'frames': 0, 'operations': None}

    def fake_spawn(argv, env):
        job = json.loads(Path(argv[-1]).read_text())
        frames = job['frameCount']
        ffmpeg(
            '-f', 'lavfi', '-i', f'color=c=blue:s={job["width"]}x{job["height"]}:d={frames / 30:.3f}:r=30',
            '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', Path(job['directory']) / 'visual.mp4',
        )

    def fake_raster(source, dest, operations):
        seen['frames'] += 1
        seen['operations'] = operations
        shutil.copyfile(source, dest)

    monkeypatch.setattr('backend.hypit_picture.spawn', fake_spawn)
    monkeypatch.setattr('backend.hypit_controls.invoke_raster', fake_raster)
    analysis = Analysis(
        summary=T, strongest_moment=T, audience=T,
        scores=[{'category': 'clarity', 'value': 50, 'reason': T}],
        scenes=[{'start': 0, 'end': 1, 'title': T, 'observation': T, 'role': 'context'}],
        transcript=[], recommendations=[], uncertainties=[],
    )
    edit = {'clips': [{'start': 0, 'end': 1}], 'captions': [], 'picture_quality': True, 'voice_cleanup': False}
    before = probe(src)['duration']
    result = render(src, tmp_path, probe(src), analysis, [], 'en', 'original', manual=edit, picture_engine='hypit')
    assert seen['frames'] == 0
    assert not (tmp_path / 'hypit' / 'quality-000.json').exists()
    assert abs(result['metadata']['duration'] - before) < 0.35
    assert not (tmp_path / 'hypit' / 'voice-cleanup.json').exists()


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg required')
def test_picture_quality_keeps_the_speech_on_an_assembled_piece(tmp_path, monkeypatch):
    piece = tmp_path / 'piece.mp4'
    ffmpeg(
        '-f', 'lavfi', '-i', 'color=c=green:s=160x240:d=1:r=30',
        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', piece,
    )

    def fake_raster(source, dest, operations):
        shutil.copyfile(source, dest)

    monkeypatch.setattr('backend.hypit_controls.invoke_raster', fake_raster)
    from backend.hypit_controls import apply_picture
    apply_picture(piece, tmp_path, 0)
    streams = json.loads(run(
        ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'json', str(piece)],
        30,
    )[0])['streams']
    assert {item['codec_type'] for item in streams} == {'video', 'audio'}


def test_the_sliders_write_one_animation_prompt():
    from backend.manual import Edit
    from backend.presentation_graphics import animation_brief, plan

    edit = Edit.model_validate({
        'clips': [{'start': 0, 'end': 20}],
        'card_motion': 40,
        'animation_depth': 80,
        'animation_motion': 20,
        'animation_density': 60,
    })
    brief = animation_brief(edit)
    assert 'Охват 40%' in brief and 'Глубина 80%' in brief
    assert 'Движение 20%' in brief and 'Плотность 60%' in brief
    assert 'виньетки' in brief and 'титра' in brief
    assert plan(edit).animation_prompt == brief
    with pytest.raises(Exception):
        Edit.model_validate({'clips': [{'start': 0, 'end': 20}], 'animation_depth': 7})
    import re
    from backend.hypit_picture import _card_motion, _limit_graphics

    def plate(start, end, name):
        return (
            f'<aside class="hf-plate" data-hypit-start-frame="{start}" data-hypit-end-frame="{end}" '
            f'data-hf-fade-in="6" data-hf-fade-out="6">{name}</aside>'
        )

    layers = [plate(0, 300, 'a'), plate(300, 600, 'b'), plate(600, 900, 'c')]
    caption = '<div class="hf-caption" data-hypit-start-frame="0" data-hypit-end-frame="90">Hello</div>'
    assert _card_motion({}) == 100
    assert _card_motion({'presentation_share': 0}) == 100
    assert _card_motion({'card_motion': 0}) == 0
    assert _card_motion({'card_motion': 40}) == 40
    assert _limit_graphics(layers, 900, 0) == []
    assert _limit_graphics([caption, *layers], 900, 0) == [caption]
    assert _limit_graphics(layers, 900, 100) == layers

    def covered(rows):
        return sum(int(b) - int(a) for a, b in re.findall(r'data-hypit-start-frame="(\d+)" data-hypit-end-frame="(\d+)"', ''.join(rows)))

    half = _limit_graphics(layers, 900, 50)
    assert covered(half) == pytest.approx(450, abs=3)
    assert len(half) == 2
    assert 'data-hypit-start-frame="0"' in half[0]
    assert 'data-hypit-start-frame="600"' not in ''.join(half)
    assert all(int(end) <= 450 for end in re.findall(r'data-hypit-end-frame="(\d+)"', ''.join(half)))
    eighty = _limit_graphics(layers, 900, 80)
    assert covered(eighty) == pytest.approx(720, abs=3)
    assert 'data-hypit-start-frame="600"' in eighty[-1]
    thin = _limit_graphics(layers, 900, 5)
    assert covered(thin) == pytest.approx(45, abs=3)
    assert len(thin) == 1
    sparse = _limit_graphics(layers, 900, 100, 50)
    assert len(sparse) == 2
    assert _limit_graphics(layers, 900, 100, 0) == []


def test_presenter_is_centered_on_the_card():
    from backend.hypit_picture import _apply_style
    page = '<style>.hf-card,.hf-plate{left:7%;width:86%;top:15%;height:70%;background:#10233f;color:#fff}</style><div data-composition-id="lumen">'
    style = {'stage': {
        'card': {'x': 0.28, 'y': 0.30, 'w': 0.84, 'h': 0.57},
        'avatar': {'x': 0.28, 'y': 0.195, 'd': 0.273},
        'fill': '282a44', 'ink': 'ffffff',
    }}
    out = _apply_style(page, style)
    assert 'left:8.0%;width:84.0%;top:21.5%;height:57.0%' in out
    assert 'data-avatar-x="0.500"' in out
    assert 'data-avatar-y="0.392"' in out
    assert 'data-card-left="0.080"' in out
