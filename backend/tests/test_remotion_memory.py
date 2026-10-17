"""Remotion stays inside the worker cgroup and a failed render publishes nothing."""
import os
import stat

import pytest

from backend.db import project
from backend.tests.test_studio import client, create, seed_plan


def test_remotion_command_bounds_concurrency_and_caches():
    from backend.director_v3 import (
        MEDIA_CACHE_BYTES,
        OFFTHREAD_CACHE_BYTES,
        OFFTHREAD_VIDEO_THREADS,
        REMOTION_CONCURRENCY,
        remotion_render_command,
    )
    from pathlib import Path
    command = remotion_render_command(
        'remotion', Path('out.mp4'), 85.5, 'speaker.mp4', {'language': 'zh-CN'}, Path('public'),
    )
    assert f'--concurrency={REMOTION_CONCURRENCY}' in command
    assert REMOTION_CONCURRENCY == '1'
    assert f'--offthreadvideo-video-threads={OFFTHREAD_VIDEO_THREADS}' in command
    assert OFFTHREAD_VIDEO_THREADS == '1'
    assert f'--offthreadvideo-cache-size-in-bytes={OFFTHREAD_CACHE_BYTES}' in command
    assert int(OFFTHREAD_CACHE_BYTES) == 256 * 1024 * 1024
    assert f'--media-cache-size-in-bytes={MEDIA_CACHE_BYTES}' in command
    assert int(MEDIA_CACHE_BYTES) == 128 * 1024 * 1024
    assert '--disallow-parallel-encoding' in command
    assert '--enable-multiprocess-on-linux' not in command


def _fake_motion(tmp_path, script: str):
    root = tmp_path / 'motion'
    (root / 'src').mkdir(parents=True)
    (root / 'src' / 'index.ts').write_text('export {}', encoding='utf-8')
    binary = root / 'node_modules' / '.bin' / 'remotion'
    binary.parent.mkdir(parents=True)
    binary.write_text(script, encoding='utf-8')
    binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
    return root


def test_failed_render_kills_children_and_drops_partial(tmp_path, monkeypatch):
    from backend import director_v3
    script = """#!/bin/sh
dest=$4
dir=$(dirname "$dest")
echo $$ > "$dir/parent.pid"
sleep 60 &
echo $! > "$dir/child.pid"
exec sleep 60
"""
    root = _fake_motion(tmp_path, script)
    monkeypatch.setattr(director_v3, 'motion_root', lambda: root)
    monkeypatch.setattr(director_v3, '_render_timeout', lambda _seconds: 1)
    dest = tmp_path / 'renders' / 'result.mp4'
    with pytest.raises(ValueError, match='director_v3_render_failed'):
        director_v3.render_assembly(dest, seconds=85.5, speaker='speaker.mp4', visual_plan=None)
    parent = int((dest.parent / 'parent.pid').read_text())
    child = int((dest.parent / 'child.pid').read_text())
    assert not _alive(parent)
    assert not _alive(child)
    assert not dest.exists()
    assert not (dest.parent / '.remotion-tmp').exists()


def test_successful_render_keeps_the_file_and_clears_temp(tmp_path, monkeypatch):
    from backend import director_v3
    script = """#!/bin/sh
dest=$4
dd if=/dev/zero of="$dest" bs=1000 count=200 >/dev/null 2>&1
mkdir -p "$TMPDIR/leftover"
echo x > "$TMPDIR/leftover/blob"
exit 0
"""
    root = _fake_motion(tmp_path, script)
    monkeypatch.setattr(director_v3, 'motion_root', lambda: root)
    dest = tmp_path / 'renders' / 'result.mp4'
    digest = director_v3.render_assembly(dest, seconds=20, speaker='speaker.mp4', visual_plan=None)
    assert dest.is_file() and dest.stat().st_size == 200_000
    assert len(digest) == 64
    assert not (dest.parent / '.remotion-tmp').exists()


def test_render_failure_does_not_mark_the_project_complete(client, monkeypatch):
    from backend import director_v3
    from backend.config import settings
    pid = create(client).json()['id']
    seed_plan(pid)
    monkeypatch.setattr(director_v3, 'PROJECT_ID', pid)

    def boom(*_args, **_kwargs):
        raise ValueError('director_v3_render_failed')

    monkeypatch.setattr(director_v3, 'render_assembly', boom)
    with pytest.raises(ValueError, match='director_v3_render_failed'):
        director_v3.run_job(project(pid), {'composition': 'DirectorV3Preview', 'duration_seconds': 20})
    saved = project(pid)
    assert saved['status'] != 'complete'
    assert list((settings.data_dir / pid).rglob('result.mp4')) == []


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True
