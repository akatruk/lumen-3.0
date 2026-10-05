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
    assert 'analyze the style of both reference video and reference video 2, make edit to\nsrc video 2. focus on adding the appropriate visuals to make it more\nillustrative. make ilustration 100% from all time video' in prompt
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
    assert (tmp_path / 'hypit' / 'src video 2').read_bytes() == (tmp_path / 'hypit' / 'source.mp4').read_bytes()
    assert 'concat=' not in seen['picture'] and 'trim=' not in seen['picture']
    assert seen['picture'].count('[0:v]') == 1
    assert not list((tmp_path / 'hypit').glob('part-*.mp4'))
    assert (tmp_path / 'animation-share.txt').read_text() == '100'
    from backend.hypit_prompt import author_source
    quiet = author_source({**edit, 'card_motion': 0}, 160, 240)
    assert 'make ilustration 0% from all time video' in quiet and 'make ilustration 50% from all time video' not in quiet
    mid = author_source({**edit, 'card_motion': 10}, 160, 240)
    assert 'make ilustration 10% from all time video' in mid and 'Будет добавлена анимация' not in mid
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


def test_spoken_words_become_a_matching_picture():
    from backend.presentation_graphics import speech_visuals, visual_kind
    assert visual_kind('利润一直在增长') == 'up'
    assert visual_kind('风险在下降') == 'down'
    assert visual_kind('外资比例 49%') == 'figure'
    assert visual_kind('首先注册公司') == 'steps'
    assert visual_kind('三个月内截止') == 'deadline'
    assert visual_kind('口播') == ''
    beats = speech_visuals({'captions': [
        {'start': 1, 'end': 3, 'zh': '利润一直在增长', 'original': '利润一直在增长'},
        {'start': 4, 'end': 6, 'zh': '风险在下降', 'original': '风险在下降'},
    ]})
    assert [beat['kind'] for beat in beats] == ['up', 'down']
    compared = speech_visuals({'captions': [
        {'start': 47, 'end': 56, 'zh': '管理逻辑也不同，中国强调法人代表，泰国更看重的是董事权限', 'original': '管理逻辑也不同，中国强调法人代表，泰国更看重的是董事权限'},
        {'start': 26, 'end': 34, 'zh': '外资比例一般是不超过49%', 'original': '外资比例一般是不超过49%'},
    ]})
    assert compared[0]['kind'] == 'compare'
    assert compared[0]['left'] == '法人代表' and compared[0]['right'] == '董事权限'
    assert compared[1]['kind'] == 'figure' and compared[1]['figure'] == '49%' and compared[1]['title'] == '外资比例'
    captions = [
        {'start': 47, 'end': 56, 'zh': '管理逻辑也不同，中国强调法人代表，泰国更看重的是董事权限', 'original': '管理逻辑也不同，中国强调法人代表，泰国更看重的是董事权限'},
        {'start': 26, 'end': 34, 'zh': '外资比例一般是不超过49%', 'original': '外资比例一般是不超过49%'},
    ]
    english = speech_visuals({'effects_language': 'en', 'captions': captions})
    assert english[0]['left'] == 'Legal representative' and english[0]['right'] == 'Director authority'
    assert english[1]['title'] == 'Foreign share' and english[1]['figure'] == '49%'
    russian = speech_visuals({'effects_language': 'ru', 'captions': captions})
    assert russian[0]['left'] == 'Законный представитель' and russian[0]['right'] == 'Полномочия директора'
    assert russian[0]['line'] == 'Законный представитель · Полномочия директора'
    assert russian[1]['line'] == 'Доля иностранного капитала не выше 49%'
    from backend.hypit_prompt import picture_prompt
    voiced_captions = [dict(captions[1], ru='Доля иностранного капитала обычно не выше 49%.')]
    filmed = picture_prompt({'clips': [{'start': 0, 'end': 20}], 'host_language': 'ru', 'subtitle_language': 'ru', 'subtitles': True, 'captions': voiced_captions})
    assert filmed == 'analyze the style of both reference video and reference video 2, make edit to\nsrc video 2. focus on adding the appropriate visuals to make it more\nillustrative. make ilustration 50% from all time video'
    assert 'Речь ведущего' not in filmed and 'Будет добавлена анимация' not in filmed
    followed = speech_visuals({'host_language': 'ru', 'captions': captions})
    assert followed[0]['left'] == 'Законный представитель'
    assert russian[1]['title'] == 'Доля иностранного капитала'

def test_the_sliders_write_one_animation_prompt():
    from backend.manual import Edit
    from backend.presentation_graphics import animation_brief, plan

    edit = Edit.model_validate({
        'clips': [{'start': 0, 'end': 60}],
        'card_motion': 20,
        'animation_depth': 40,
        'animation_motion': 60,
        'animation_density': 80,
    })
    brief = animation_brief(edit)
    assert 'Будет добавлена анимация на 20% длины ролика — это 12 секунд на каждую минуту.' in brief
    assert 'Ведущий в кружке' in brief and 'Интенсивность 40%' in brief
    assert 'Движение 60%' in brief and 'Плотность 80% слоёв' in brief
    assert 'стрелка вверх' in brief and 'крупная цифра' in brief
    assert 'площад' not in brief
    full = animation_brief(Edit.model_validate({'clips': [{'start': 0, 'end': 60}]}))
    assert '100% длины ролика' in full and '60 секунд на каждую минуту' in full
    assert 'Интенсивность 100%' in full
    assert plan(edit).animation_prompt == brief
    with pytest.raises(Exception):
        Edit.model_validate({'clips': [{'start': 0, 'end': 20}], 'animation_intensity': 7})
    with pytest.raises(Exception):
        Edit.model_validate({'clips': [{'start': 0, 'end': 20}], 'animation_intensity': 0})
    from backend.hypit_picture import _card_motion

    assert _card_motion({}) == 100
    assert _card_motion({'presentation_share': 0}) == 100
    assert _card_motion({'card_motion': 0}) == 0
    assert _card_motion({'card_motion': 40}) == 40


def test_create_video_without_captions_still_films_the_short_request():
    """An empty picture used to leave the request unreferenced, so Hypit dropped it."""
    from backend.hypit_prompt import author_source

    bare = {
        'clips': [{'start': 0, 'end': 63.466667, 'approved': True}],
        'captions': [],
    }
    full = author_source({**bare, 'card_motion': 100}, 720, 1280, duration=63.466667)
    half = author_source({**bare, 'card_motion': 50}, 720, 1280, duration=63.466667)
    quiet = author_source({**bare, 'card_motion': 0}, 720, 1280, duration=63.466667)
    request = (
        'analyze the style of both reference video and reference video 2, make edit to\n'
        'src video 2. focus on adding the appropriate visuals to make it more\n'
        'illustrative. make ilustration 100% from all time video'
    )
    assert request in full and 'prompt={request}' in full and 'seedance:ReferenceVideo' in full
    prologue, body = full.split('<script', 1)
    assert '<import as="seedance" from="@hypit/seedance@1"/>' in prologue
    assert '<import' not in body and 'prompt={request}' in body
    assert 'comment={request}' not in full and 'comment:Sticker' not in full
    assert 'source={edited.video}' in full and 'src="./src video 2"' in full
    assert 'src="./reference video"' in full and 'src="./reference video 2"' in full
    assert 'Будет добавлена анимация' not in full and 'без склейки из кусков' not in full
    assert 'make ilustration 50% from all time video' in half and 'prompt={request}' in half
    assert 'duration="30"' in half and 'comment={request}' not in half
    assert 'make ilustration 0% from all time video' in quiet and 'seedance:ReferenceVideo' not in quiet
    assert 'comment:Sticker' not in quiet and 'source={footage}' in quiet


def test_card_motion_changes_the_svml_window():
    """40% and 80% name different seconds, and Hypit gets those windows."""
    from backend.hypit_prompt import author_source

    base = {
        'clips': [{'start': 0, 'end': 120, 'approved': True}],
        'captions': [
            {'start': 2, 'end': 8, 'zh': '利润一直在增长', 'original': '利润一直在增长'},
            {'start': 30, 'end': 40, 'zh': '风险在下降', 'original': '风险在下降'},
        ],
    }
    low = author_source({**base, 'card_motion': 40}, 720, 1280, duration=120)
    high = author_source({**base, 'card_motion': 80}, 720, 1280, duration=120)
    assert 'make ilustration 40% from all time video' in low
    assert 'make ilustration 80% from all time video' in high
    assert 'Будет добавлена анимация' not in low and 'Будет добавлена анимация' not in high
    assert 'at="0s" for="24s"' in low and 'at="60s" for="24s"' in low
    assert 'at="0s" for="48s"' in high and 'at="60s" for="48s"' in high
    assert 'for="48s"' not in low and 'for="24s"' not in high
    assert 'source={spoken-line.track}' in low and 'source={spoken-line.track}' in high
    assert 'source={thought-cards.track}' in high
    assert 'at="30s" for="10s"' in high and '风险在下降' in high
    assert 'at="30s"' not in low
    assert '利润一直在增长' in low and ' || ' in low
    assert 'caption-fine:Track' in low and 'index.html' not in low
    quiet = author_source({**base, 'card_motion': 0}, 720, 1280, duration=120)
    assert 'make ilustration 0% from all time video' in quiet and 'for="' not in quiet
    assert 'comment:Sticker' not in quiet and 'source={performance.visual}' in quiet
    russian = {
        'clips': [{'start': 0, 'end': 120, 'approved': True}],
        'captions': [{'start': 1, 'end': 5, 'original': 'Прибыль растёт', 'ru': 'Прибыль растёт'}],
    }
    low_ru = author_source({**russian, 'card_motion': 40}, 720, 1280, duration=120)
    high_ru = author_source({**russian, 'card_motion': 80}, 720, 1280, duration=120)
    assert 'at="0s" for="24s"' in low_ru and 'at="0s" for="48s"' in high_ru
    assert 'Прибыль растёт' in low_ru and 'language="ru"' in low_ru
    assert 'comment:Sticker' not in low_ru


def test_author_clock_matches_the_source_rate():
    """Hypit captures round(duration * clock) at 30fps for the whole program."""
    from backend.hypit_prompt import author_source

    duration = 1901 / 30
    base = {
        'clips': [{'start': 0, 'end': 64, 'approved': True}],
        'captions': [{'start': 1.0, 'end': 8.5, 'zh': '开场', 'original': '开场'}],
    }
    text = author_source({**base, 'card_motion': 40}, 720, 1280, duration=duration)
    assert 'frame-rate="30"' in text
    assert 'at="0s" for="24s"' in text
    short = author_source({**base, 'card_motion': 100}, 720, 1280, duration=2)
    assert 'frame-rate="30"' in short
    assert 'during="program"' in short


def test_partial_minute_window_stays_inside_program_frames():
    """A remainder rounded up used to end one millisecond past the last frame."""
    from backend.hypit_prompt import author_source

    duration = 1901 / 30
    base = {
        'clips': [{'start': 0, 'end': 64, 'approved': True}],
        'captions': [
            {'start': 1.0, 'end': 8.5, 'zh': '开场', 'original': '开场'},
            {'start': 60.0, 'end': 61.8, 'zh': '结构', 'original': '结构'},
        ],
    }
    text = author_source({**base, 'card_motion': 75}, 720, 1280, duration=duration)
    assert 'at="0s" for="45s"' in text
    assert 'at="60s" for="3.366s"' in text
    assert 'for="3.467s"' not in text
    assert 'at="60s" for="1.8s"' in text
    assert 'index.html' not in text
    low = author_source({**base, 'card_motion': 40}, 720, 1280, duration=duration)
    high = author_source({**base, 'card_motion': 80}, 720, 1280, duration=duration)
    assert 'at="0s" for="24s"' in low and 'at="60s" for="3.366s"' in low
    assert 'at="0s" for="48s"' in high and 'at="60s" for="3.366s"' in high
    quiet = author_source({**base, 'card_motion': 0}, 720, 1280, duration=duration)
    assert 'make ilustration 0% from all time video' in quiet and 'for="' not in quiet
    full = author_source({**base, 'card_motion': 100}, 720, 1280, duration=duration)
    assert 'during="program"' in full and 'minute0-' not in full
    assert 'make ilustration 100% from all time video' in full


def _color_clip(path, seconds, color):
    ffmpeg(
        '-f', 'lavfi', '-i', f'color=c={color}:s=64x64:r=30:d={seconds}',
        '-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest',
        '-f', 'mp4', path,
    )


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'), reason='FFmpeg required')
def test_uploaded_videos_keep_the_working_input_names(tmp_path):
    """Seedance names stay, and each staged mp4 is between 2 and 30 seconds."""
    from backend.hypit_picture import stage_prompt_inputs

    project = tmp_path / 'project'
    project.mkdir()
    source = project / 'source'
    _color_clip(source, 4, 'red')
    _color_clip(project / 'reference_source', 8, 'green')
    nested = project / 'references' / '7680801661580741926'
    nested.mkdir(parents=True)
    _color_clip(nested / 'source', 36, 'blue')
    short = project / 'references' / 'short'
    short.mkdir()
    _color_clip(short / 'source', 1, 'yellow')
    kept = {
        path: path.read_bytes()
        for path in (source, project / 'reference_source', nested / 'source', short / 'source')
    }
    work = tmp_path / 'hypit'
    work.mkdir()
    _color_clip(work / 'source.mp4', 40, 'white')
    footage = (work / 'source.mp4').read_bytes()
    stage_prompt_inputs(source, work)
    assert kept[source] == source.read_bytes()
    assert kept[project / 'reference_source'] == (project / 'reference_source').read_bytes()
    assert kept[nested / 'source'] == (nested / 'source').read_bytes()
    assert kept[short / 'source'] == (short / 'source').read_bytes()
    assert (work / 'source.mp4').read_bytes() == footage
    assert (work / 'reference video').read_bytes() == kept[project / 'reference_source']
    for name in ('reference video', 'reference video 2', 'reference video 3', 'src video 2'):
        meta = probe(work / name)
        assert 2 <= meta['duration'] <= 30
        assert meta['codec'] == 'h264'
    assert probe(work / 'reference video')['duration'] == pytest.approx(8, abs=0.3)
    assert probe(work / 'reference video 2')['duration'] == pytest.approx(30, abs=0.5)
    assert probe(work / 'src video 2')['duration'] == pytest.approx(30, abs=0.5)
    assert probe(work / 'reference video 3')['duration'] >= 2
