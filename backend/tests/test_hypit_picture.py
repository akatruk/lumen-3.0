"""Style-match renders call Hypit's capture. The fixture never contacts a network."""
import inspect
import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from backend.hypit_picture import engine_for
from backend.media import ffmpeg, probe, render, run
from backend.schemas import Analysis
from backend.worker import render_job

T = {'en': 'Synthetic fixture, not AI analysis', 'zh': '合成测试素材，非 AI 分析'}


def test_picture_runtime_asks_for_software_gpu(tmp_path, monkeypatch):
    """A GPU-less host must not inherit HyperFrames' hardware default."""
    monkeypatch.delenv('HYPIT_CHROME', raising=False)
    from backend.hypit_picture import _runtime_profile

    path = _runtime_profile(tmp_path)
    picture = json.loads(path.read_text())['endpoints']['hyperframes.local']
    assert picture['config']['browserGpu'] == 'software'
    assert picture['config']['workers'] == 1
    assert picture['config']['defaultConcurrency'] == 1
    assert picture['config']['maxDecodedSourceBytes'] == 64 * 1024 * 1024
    assert picture['config']['maxPendingFrameBytes'] == 32 * 1024 * 1024


def test_software_chrome_strips_blank_screenshot_flags(tmp_path, monkeypatch):
    """SwiftShader stays, and the flags that blank Page.captureScreenshot are dropped."""
    browser = tmp_path / 'chrome-headless-shell'
    seen = tmp_path / 'args.txt'
    browser.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > ' + shlex.quote(str(seen)) + '\n')
    browser.chmod(0o755)
    monkeypatch.setenv('HYPIT_CHROME', str(browser))
    from backend.hypit_picture import _runtime_profile

    path = _runtime_profile(tmp_path)
    picture = json.loads(path.read_text())['endpoints']['hyperframes.local']
    assert picture['config']['browserGpu'] == 'software'
    wrapper = Path(picture['config']['chromePath'])
    assert wrapper.name == 'chrome-software'
    assert os.access(wrapper, os.X_OK)
    assert repr(str(browser)) in wrapper.read_text()
    subprocess.run(
        [str(wrapper), '--no-sandbox', '--disable-gpu', '--disable-gpu-compositing', '--use-angle=swiftshader'],
        check=True,
    )
    args = seen.read_text().splitlines()
    assert args[0:2] == ['--no-sandbox', '--use-angle=swiftshader']
    assert '--disable-gpu' not in args
    assert '--disable-gpu-compositing' not in args


def test_chrome_path_uses_the_explicit_browser(monkeypatch, tmp_path):
    browser = tmp_path / 'chrome'
    browser.write_text('')
    monkeypatch.setenv('HYPIT_CHROME', str(browser))
    from backend.hypit_picture import _chrome
    assert _chrome() == str(browser)


def test_style_match_selects_the_hypit_engine():
    assert engine_for({'style_match': True}) == 'hypit'
    assert engine_for({'style_match': False}) == 'hypit'
    assert engine_for(None) == 'hypit'
    assert engine_for({}) == 'hypit'
    source = inspect.getsource(render_job)
    assert 'picture_engine=engine_for' in source.replace(' ', '')


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

    def fake_deliver(work):
        work = Path(work)
        seen['prompt'] = (work / 'main.svml').read_text()
        seen['picture'] = (work / 'picture.txt').read_text()
        meta = probe(work / 'cut.mp4')
        ffmpeg(
            '-f', 'lavfi', '-i', f'color=c=blue:s={meta["width"]}x{meta["height"]}:d={max(meta["duration"], 0.1):.3f}:r=30',
            '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', work / 'visual.mp4',
        )
        return work / 'visual.mp4'

    monkeypatch.setattr('backend.hypit_picture.deliver', fake_deliver)
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
    prompt = seen['prompt']
    assert '<render:Video id="final"' in prompt and 'src="./source.mp4"' in prompt
    assert 'Анимация 40%  ведущий' in prompt
    assert 'Будет добавлена анимация' not in prompt
    assert '三名股东开会' in prompt and '法人代表' in prompt and '董事权限' in prompt
    assert '口播' not in prompt and 'Shareholders' not in prompt and 'Governance logic also differs' not in prompt
    assert 'film.grade' not in prompt and 'film.vignette' not in prompt
    assert 'data-hypit-start-frame' not in prompt and 'end="' not in prompt
    assert 'площади' not in prompt and 'этот размер' not in prompt
    assert 'карточки выезжают' not in prompt and 'Переходы между фразами' not in prompt
    assert not (tmp_path / 'hypit' / 'index.html').exists()
    assert (tmp_path / 'hypit' / 'recipes.svs').is_file() and (tmp_path / 'hypit' / 'build.svrun').is_file()
    assert (tmp_path / 'hypit' / 'source.mp4').is_file()
    assert not (tmp_path / 'hypit' / 'src video 2').exists()
    assert 'concat=' not in seen['picture'] and 'trim=' not in seen['picture']
    assert seen['picture'].count('[0:v]') == 1
    assert not list((tmp_path / 'hypit').glob('part-*.mp4'))
    assert (tmp_path / 'animation-share.txt').read_text() == '100'
    from backend.hypit_prompt import author_source
    quiet = author_source({**edit, 'card_motion': 0}, 160, 240)
    assert 'Анимация 40%  ведущий' in quiet and 'for="' not in quiet
    mid = author_source({**edit, 'card_motion': 10}, 160, 240)
    assert 'Анимация 40%  ведущий' in mid and 'Будет добавлена анимация' not in mid
    assert not list(tmp_path.glob('*.ass'))
    cleanup = json.loads((tmp_path / 'hypit' / 'voice-cleanup.json').read_text())
    assert cleanup['control'] == 'voice_cleanup' and cleanup['stem'] == 'host'
    assert (tmp_path / 'hypit' / 'host-cleaned.wav').is_file()
    assert result['metadata']['has_audio']
    assert abs(result['metadata']['duration'] - 2) < 0.6
    streams = json.loads(run(
        ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,duration', '-of', 'json', str(tmp_path / 'result.mp4')],
        30,
    )[0])['streams']
    video = float(next(item['duration'] for item in streams if item['codec_type'] == 'video'))
    audio = float(next(item['duration'] for item in streams if item['codec_type'] == 'audio'))
    assert abs(video - audio) < 0.2


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

    def fake_deliver(work):
        work = Path(work)
        meta = probe(work / 'cut.mp4')
        ffmpeg(
            '-f', 'lavfi', '-i', f'color=c=blue:s={meta["width"]}x{meta["height"]}:d={max(meta["duration"], 0.1):.3f}:r=30',
            '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', work / 'visual.mp4',
        )
        return work / 'visual.mp4'

    def fake_raster(source, dest, operations):
        seen['frames'] += 1
        seen['operations'] = operations
        shutil.copyfile(source, dest)

    monkeypatch.setattr('backend.hypit_picture.deliver', fake_deliver)
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


def test_the_hand_prompt_ignores_sliders_and_a_stored_brief():
    from backend.hypit_prompt import illustration_request, picture_prompt, plan
    from backend.manual import Edit

    edit = Edit.model_validate({
        'clips': [{'start': 0, 'end': 60}],
        'card_motion': 20,
        'animation_depth': 40,
        'animation_motion': 60,
        'animation_density': 80,
        'presentation_prompt': 'make ilustration 50% from all time video',
        'animation_prompt': 'Будет добавлена анимация',
    })
    assert picture_prompt(edit.model_dump()) == illustration_request()
    stored = plan(edit)
    assert stored.presentation_prompt == illustration_request()
    assert stored.animation_prompt == ''
    assert stored.presentation == []
    with pytest.raises(Exception):
        Edit.model_validate({'clips': [{'start': 0, 'end': 20}], 'animation_intensity': 7})


def test_create_video_without_captions_still_films_the_short_request():
    """The sentence stays in the local prompt. Hypit films the whole source."""
    from backend.hypit_prompt import author_source

    bare = {
        'clips': [{'start': 0, 'end': 63.466667, 'approved': True}],
        'captions': [],
    }
    full = author_source({**bare, 'card_motion': 100}, 720, 1280, duration=63.466667)
    half = author_source({**bare, 'card_motion': 50}, 720, 1280, duration=63.466667)
    quiet = author_source({**bare, 'card_motion': 0}, 720, 1280, duration=63.466667)
    from backend.hypit_prompt import illustration_request
    request = illustration_request()
    assert request in full and 'source={footage}' in full
    assert 'seedance:ReferenceVideo' not in full and 'prompt={request}' not in full
    assert 'comment={request}' not in full and 'comment:Sticker' not in full
    assert 'src="./source.mp4" media-type="video/mp4"' in full
    assert 'duration="30"' not in full and 'media-type="video"' not in full
    assert 'Будет добавлена анимация' not in full and 'без склейки из кусков' not in full
    assert request in half and 'source={footage}' in half
    assert 'duration="30"' not in half and 'comment={request}' not in half
    assert request in quiet and 'seedance:ReferenceVideo' not in quiet
    assert 'comment:Sticker' not in quiet and 'source={footage}' in quiet


def test_stored_english_prompt_cannot_override_the_filmed_sentence():
    """A manual that still carries the old English sentence is not what Hypit films."""
    from backend.hypit_prompt import author_source, illustration_request, picture_prompt

    english = (
        "analyze the style of both reference video and reference video 2, make edit to\n"
        "src video 2. focus on adding the appropriate visuals to make it more\n"
        "illustrative. make ilustration 50% from all time video"
    )
    edit = {
        'clips': [{'start': 0, 'end': 63.4, 'approved': True}],
        'card_motion': 40,
        'presentation_prompt': english,
        'animation_prompt': english,
        'captions': [
            {'start': 8.5, 'end': 19.5, 'zh': '注册资本', 'original': '注册资本'},
        ],
    }
    assert picture_prompt(edit) == illustration_request()
    assert 'make ilustration' not in picture_prompt(edit)
    text = author_source(edit, 720, 1280, duration=63.4)
    start = text.find('id="request">')
    value = text[start + len('id="request">'):text.find('</text:Value>', start)]
    assert value == illustration_request()
    assert 'Анимация 40%  ведущий' in value
    assert 'Эффекты: color, glow, shadow' in value
    assert 'Переходы: растворение, шторка, круг' in value
    assert 'Музыка −24 дБ' in value
    assert 'make ilustration' not in text
    assert 'Один ролик' not in text.split('</text:Value>', 1)[-1]
    assert 'comment:Sticker' not in text and 'ColorWash' not in text
    assert 'seedance' not in text and 'hypit.ai' not in text
    assert 'src="./source.mp4"' in text and 'frame-rate="30"' in text
    assert edit['presentation_prompt'] == english
