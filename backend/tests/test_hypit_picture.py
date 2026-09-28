"""Style-match renders call Hypit's capture. The fixture never contacts a network."""
import inspect
import json
import shutil
from pathlib import Path

import pytest

from backend.hypit_picture import engine_for
from backend.media import ffmpeg, probe, render
from backend.schemas import Analysis
from backend.worker import render_job

T = {'en': 'Synthetic fixture, not AI analysis', 'zh': '合成测试素材，非 AI 分析'}


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
    (root / 'node_modules' / '.bin').mkdir(parents=True)
    (root / 'node_modules' / '.bin' / 'tsx').write_text('')
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
            {'start': 1, 'end': 2, 'transition': 'diagbl'},
        ],
        'captions': [{'start': 0.2, 'end': 1.4, 'original': '三名股东开会', 'en': 'Three shareholders meet', 'zh': '三名股东开会'}],
        'subtitles': True,
        'voice_cleanup': True,
    }
    result = render(src, tmp_path, probe(src), analysis, [], 'zh', 'original', manual=edit, picture_engine='hypit')
    assert seen['argv'][2].endswith('hypit_render.mjs')
    assert seen['root'] == str(root)
    html = seen['html']
    assert 'data-composition-id="lumen"' in html
    assert 'data-hypit-start-frame=' in html
    assert 'data-hypit-source-fps=' in html
    assert '三名股东开会' in html
    assert '口播' not in html and 'Shareholders' not in html and '>3<' not in html
    assert not list(tmp_path.glob('*.ass'))
    assert (tmp_path / 'host-voice.mp4').is_file()
    assert result['metadata']['has_audio']
    assert abs(result['metadata']['duration'] - 2) < 0.6
