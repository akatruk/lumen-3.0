"""Style-match renders call Hypit's capture. The fixture never contacts a network."""
import inspect
import json
import os
import re
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


def test_vertical_hypit_frame_is_a_full_phone_picture():
    from backend.media import picture_frame
    assert picture_frame({'width': 464, 'height': 848}, 'original', 'hypit') == (1080, 1920)
    assert picture_frame({'width': 464, 'height': 848}, 'original') == (464, 848)


def test_gpu_flag_films_on_the_remote_runtime(tmp_path, monkeypatch):
    """The web capture leaves this machine only when the worker flag is set."""
    monkeypatch.setenv('LUMEN_HYPIT_GPU', '1')
    seen = {}

    def film(work):
        seen['work'] = Path(work)
        visual = Path(work) / 'visual.mp4'
        visual.write_bytes(b'x' * 64)
        return visual

    monkeypatch.setattr('backend.hypit_gpu.film', film)
    from backend.hypit_picture import deliver
    out = deliver(tmp_path)
    assert seen['work'] == tmp_path
    assert out == tmp_path / 'visual.mp4'
    assert out.stat().st_size == 64


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
    assert picture['config']['processTimeoutMs'] == 3 * 60 * 60 * 1000


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
    assert 'Доля анимации — 60%' in prompt
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
    assert 'Доля анимации — 0%' in quiet and 'seedance' not in quiet and '三名股东开会' in quiet
    mid = author_source({**edit, 'card_motion': 10}, 160, 240)
    assert 'Доля анимации — 10%' in mid and 'Будет добавлена анимация' not in mid
    assert "THE USER'S ORIGINAL VIDEO IS THE VIDEO." in mid and 'PATTERN INTERRUPTS' in mid
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


def test_the_hand_prompt_uses_the_sliders_and_ignores_a_stored_brief():
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
    sentence = picture_prompt(edit.model_dump())
    assert sentence == illustration_request(edit.model_dump())
    assert 'Доля анимации — 20%' in sentence
    assert 'Движение — 60%' in sentence
    assert 'Визуальная плотность — 80%' in sentence
    assert 'make ilustration' not in sentence
    stored = plan(edit)
    assert stored.presentation_prompt == illustration_request(edit)
    assert stored.animation_prompt == ''
    assert stored.presentation == []
    with pytest.raises(Exception):
        Edit.model_validate({'clips': [{'start': 0, 'end': 20}], 'animation_intensity': 7})


def test_create_video_without_captions_still_films_the_short_request():
    """The sentence stays in the text value. Local cards film the spoken lines."""
    from backend.hypit_prompt import author_source

    bare = {
        'clips': [{'start': 0, 'end': 63.466667, 'approved': True}],
        'captions': [],
    }
    full = author_source({**bare, 'card_motion': 100}, 720, 1280, duration=63.466667)
    half = author_source({**bare, 'card_motion': 50}, 720, 1280, duration=63.466667)
    quiet = author_source({**bare, 'card_motion': 0}, 720, 1280, duration=63.466667)
    from backend.hypit_prompt import illustration_request
    import html
    request = html.unescape(full.split('id="request">', 1)[1].split('</text:Value>', 1)[0])
    assert illustration_request({**bare, 'card_motion': 100}) == request and 'source={footage}' in full
    assert 'Доля анимации — 100%' in full and 'for="60s"' in full
    assert 'seedance' not in full and 'comment:Sticker' not in full
    assert "THE USER'S ORIGINAL VIDEO IS THE VIDEO." in full and 'PATTERN INTERRUPTS' in full
    assert 'src="./source.mp4" media-type="video/mp4"' in full
    assert 'media-type="video"' not in full
    assert 'Будет добавлена анимация' not in full and 'без склейки из кусков' not in full
    assert 'Субтитры средние' not in full and 'Рост — стрелка вверх' not in full
    half_request = html.unescape(half.split('id="request">', 1)[1].split('</text:Value>', 1)[0])
    assert illustration_request({**bare, 'card_motion': 50}) == half_request and 'source={footage}' in half
    assert 'Доля анимации — 50%' in half and 'for="30s"' in half
    assert 'seedance' not in half and 'comment={request}' not in half
    quiet_request = html.unescape(quiet.split('id="request">', 1)[1].split('</text:Value>', 1)[0])
    assert illustration_request({**bare, 'card_motion': 0}) == quiet_request and 'seedance' not in quiet
    assert 'Доля анимации — 0%' in quiet and 'ColorWash' not in quiet
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
    assert picture_prompt(edit) == illustration_request(edit)
    assert 'make ilustration' not in picture_prompt(edit)
    text = author_source(edit, 720, 1280, duration=63.4)
    start = text.find('id="request">')
    value = text[start + len('id="request">'):text.find('</text:Value>', start)]
    assert value.startswith('Run a FULL END-TO-END LUMEN VIDEO TEST')
    assert 'На графике только эти сказанные фразы' not in value
    assert '注册资本' not in value
    assert 'Доля анимации — 40%' in value
    assert 'for="24s"' in text
    assert 'SPEAKER MUST REMAIN THE PROTAGONIST' in value
    assert '40–60% speaker-visible time' in value
    assert "THE USER'S ORIGINAL VIDEO IS THE VIDEO." in value
    assert 'make ilustration' not in text
    assert 'seedance' not in text and '注册资本' in text
    assert 'src="./motion/1.mp4"' in text
    assert '1.5–4 seconds' in value and 'CURATED MEDIA LIBRARY' in value
    assert 'графика сказанного.' not in value and 'Субтитры средние' not in text
    assert 'Рост — стрелка вверх' not in text
    assert 'Сними один' not in text.split('</text:Value>', 1)[-1]
    assert 'media-track:Item' in text and 'ColorWash' in text
    assert 'hypit.ai' not in text
    assert 'src="./source.mp4"' in text and 'frame-rate="30"' in text
    assert edit['presentation_prompt'] == english


def test_the_hand_sentence_stays_in_the_author_source():
    """The sentence is the text value. Local Hypit films the source and the cards."""
    from backend.hypit_prompt import author_source, illustration_request

    sentence = illustration_request()
    text = author_source({
        'clips': [{'start': 0, 'end': 63.466667, 'approved': True}],
        'captions': [],
    }, 720, 1280, duration=63.466667)
    import html
    request = html.unescape(text.split('id="request">', 1)[1].split('</text:Value>', 1)[0])
    assert request == sentence
    assert 'seedance' not in text and "THE USER'S ORIGINAL VIDEO IS THE VIDEO." in sentence
    assert 'SPEAKER MUST REMAIN THE PROTAGONIST' in sentence
    assert 'make ilustration' not in text
    assert 'Субтитры средние' not in text
    assert 'Рост — стрелка вверх' not in text
    assert "THE USER'S ORIGINAL VIDEO IS THE VIDEO." not in text.split('</text:Value>', 1)[-1]


_CHINA = (
    '再看出资节奏，中国认缴时间弹性很大，泰国则要求实缴部分资本，'
    '银行开户、工作证、签证申请都会盯着资金到位情况'
)


def _density_markup(density, line=_CHINA, captions=None, motion=100, duration=40):
    from backend.hypit_prompt import author_source

    manual = {
        'clips': [{'start': 0, 'end': duration}],
        'captions': captions or [{'start': 1.0, 'end': 18.0, 'zh': line}],
        'card_motion': motion,
        'animation_density': density,
    }
    return author_source(manual, 720, 1280, duration=duration)


def _sticker_bodies(markup):
    return re.findall(r'<comment:Sticker\b[^>]*>(.*?)</comment:Sticker>', markup)


def _motion_parts(markup):
    import html
    import json
    parts = []
    for raw in re.findall(r'<text:Value id="motion-\d+">(.*?)</text:Value>', markup):
        parts.extend(json.loads(html.unescape(raw)))
    return parts


def test_every_phrase_keeps_every_figure_and_a_short_fragment():
    """Commas do not drop the arrow, the scale, or the link. The digit is a spoken number or a step count."""
    from backend.hypit_figures import scene_state
    from backend.hypit_prompt import animation_shots, illustration_request

    sentence = illustration_request()
    assert 'PATTERN INTERRUPTS' in sentence
    assert 'Do NOT invent facts.' in sentence
    assert '1.5–4 seconds' in sentence
    assert '40–60% speaker-visible time' in sentence
    assert "THE USER'S ORIGINAL VIDEO IS THE VIDEO." in sentence
    line = '再看出资节奏，中国认缴时间弹性很大，泰国则要求实缴部分资本，银行开户、工作证、签证申请都会盯着资金到位情况'
    shots = animation_shots({
        'captions': [{'start': 1, 'end': 18, 'zh': line}],
        'card_motion': 100,
        'animation_density': 70,
    }, 40)
    shot = shots[0]
    assert shot['format'] == 'type' and shot['kind'] == 'type' and abs(shot['span'] - 17) < 0.05
    assert shot['fragment_s'] == 5 and shot['number'] == ''
    assert shot['motif'] in {'documents', 'path', 'stamp', 'doorway'}
    early = scene_state(shot, 0.5)
    mid = scene_state(shot, 3)
    late = scene_state(shot, 5)
    assert early['format'] == 'type'
    assert scene_state(shot, 1.0)['travel'] < 0.55
    assert late['travel'] > mid['travel'] > early['travel']
    assert late['travel'] < 1
    assert '%' not in early['figure'] and '%' not in ''.join(early['ticks'])
    numbered = animation_shots({
        'captions': [{'start': 1, 'end': 8, 'zh': '外资比例一般是不超过49%'}],
        'card_motion': 100,
    }, 40)[0]
    marked = scene_state(numbered, 0.5)
    assert numbered['format'] == 'number'
    assert numbered['number'] == '49%' and marked['figure'] == '49%' and marked['ticks'] == ['49%']


def test_neighboring_phrases_change_the_scene():
    """The next phrase is not another copy of the same card stack."""
    from backend.hypit_prompt import _SCENE_FORMATS, animation_shots

    shots = animation_shots({
        'captions': [
            {'start': 1, 'end': 6, 'zh': '移居、第二居留权'},
            {'start': 7, 'end': 12, 'zh': '目标和预算'},
            {'start': 13, 'end': 18, 'zh': '文件准备'},
        ],
        'card_motion': 100,
    }, 40)
    formats = [shot['format'] for shot in shots]
    assert len(formats) == 3
    assert all(left != right for left, right in zip(formats, formats[1:]))
    assert set(formats) <= set(_SCENE_FORMATS)


def test_steps_keep_moving_until_the_phrase_ends():
    """The arrow between steps is still traveling at the middle of the phrase."""
    from backend.hypit_figures import _reveal
    assert _reveal(1, 180, 0, 4) > 0
    assert _reveal(1, 180, 3, 4) == 0
    assert _reveal(90, 180, 3, 4) < 1
    assert _reveal(179, 180, 3, 4) == 1


def test_each_spoken_line_in_the_window_gets_its_own_figure():
    """Two phrases become two new clips. The number on the figure is one the host said."""
    from backend.hypit_prompt import author_source
    markup = author_source({
        'clips': [{'start': 0, 'end': 40}],
        'captions': [
            {'start': 1, 'end': 8, 'zh': '外资比例一般是不超过49%'},
            {'start': 10, 'end': 18, 'zh': '至少三名股东'},
        ],
        'card_motion': 100,
    }, 720, 1280, duration=40)
    assert 'src="./motion/1.mp4"' in markup and 'src="./motion/2.mp4"' in markup
    assert '49%' in markup and '三' in markup
    assert 'seedance' not in markup
    assert 'media={motion-1-media.media}' in markup
    assert 'appearance={recipes.media.motion}' in markup


def test_density_films_more_spoken_clause_cards():
    """A higher density films more clauses of the same line. Seventy is past the old cap of three."""
    low = _density_markup(20)
    high = _density_markup(70)
    packed = _density_markup(100)
    low_bodies = _motion_parts(low)
    high_bodies = _motion_parts(high)
    packed_bodies = _motion_parts(packed)
    assert low_bodies == ['再看出资节奏']
    assert len(high_bodies) > len(low_bodies)
    assert len(high_bodies) > 3
    assert high_bodies[:2] == ['中国认缴时间弹性很大', '泰国则要求实缴部分资本']
    assert '再看出资节奏' in high_bodies and '银行开户' in high_bodies
    assert '工作证' not in high_bodies and '签证申请都会盯着资金到位情况' not in high_bodies
    assert len(packed_bodies) > len(high_bodies)
    assert len(packed_bodies) == 6
    assert 'Визуальная плотность — 20%' in low
    assert 'Визуальная плотность — 70%' in high
    assert 'seedance' not in high and 'PATTERN INTERRUPTS' in high
    assert 'Сними один' not in high.split('</text:Value>', 1)[-1]
    assert '↑' not in ''.join(high_bodies) and '↓' not in ''.join(high_bodies)
    assert 'src="./motion/1.mp4"' in high and 'media-track:Item' in high
    short = _motion_parts(_density_markup(70, '注册资本认缴，股东责任分开'))
    assert len(short) == 2
    repeated = _motion_parts(_density_markup(70, '银行开户单独办，银行开户单独办，签证随后办理'))
    assert repeated == ['银行开户单独办', '签证随后办理']


def test_graphic_window_keeps_the_late_phrase_off_the_cards():
    """Animation 60% films the first 36s of the minute. The later phrase stays the host."""
    line = '管理逻辑也不同，中国强调法人代表，泰国更看重的是董事权限，很多法律文件只认董事签字不看公章。'
    markup = _density_markup(70, captions=[
        {'start': 1.0, 'end': 18.0, 'zh': _CHINA},
        {'start': 47.0, 'end': 56.5, 'zh': line},
    ], motion=60, duration=63.4)
    bodies = _motion_parts(markup)
    assert len(bodies) > 3
    assert not any('管理逻辑' in body for body in bodies)
    assert 'for="36s"' in markup
    assert "THE USER'S ORIGINAL VIDEO IS THE VIDEO." in markup
    assert 'stack-order: 48' in markup


def test_two_cinematic_cards_land_on_host_only_lines_before_the_source_card():
    """The closing host-only line keeps the source card. The two lines before it get the same dark card."""
    markup = _density_markup(70, captions=[
        {'start': 39.0, 'end': 44.5, 'zh': '很多人所说的直通泳池，是中间有一段公共的距离的'},
        {'start': 44.5, 'end': 50.5, 'zh': '这种的话，其实我觉得直通泳池反而不是个优点'},
        {'start': 50.5, 'end': 58.5, 'zh': '而且你也不能这种直接跳进泳池'},
        {'start': 96.0, 'end': 103.0, 'zh': '其中的话亚马逊它有一个弱点，就是它没有地下层，没有地下停车库'},
        {'start': 103.0, 'end': 110.0, 'zh': '所以它相对杜斯特来说它会更潮湿一点。但是这个杜斯特它有地下停车库'},
        {'start': 110.0, 'end': 118.0, 'zh': '这是直通泳池非常重要的一点，所以这也是它在市场上放租放卖比较少的原因，因为很多人都惜售'},
    ], motion=60, duration=162.2)
    bodies = _sticker_bodies(markup)
    assert '就是它没有地下层，没有地下停车库' in ''.join(bodies) or '其中的话亚马逊它有一个弱点，就是它没有地下层，没有地下停车库' in bodies
    assert any('地下停车库' in body and '潮湿' in body for body in bodies)
    assert not any('惜售' in body for body in bodies)
    assert 'scene-style' in markup and 'comment.scene' in markup
    assert "THE USER'S ORIGINAL VIDEO IS THE VIDEO." in markup
    assert 'seedance' not in markup
    assert '#7DFFC3' in markup
    assert 'seedance' not in markup and 'PATTERN INTERRUPTS' in markup
    assert markup.split('id="request">', 1)[1].startswith('Run a FULL END-TO-END LUMEN VIDEO TEST')
    assert 'Сними один' not in markup.split('</text:Value>', 1)[-1]
