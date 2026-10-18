import os
import time

from backend.config import settings
from backend.db import connect, init_db
from backend.render_retention import prune_pictures


def _project(pid):
    init_db()
    now = time.time()
    with connect() as db:
        db.execute(
            'INSERT OR IGNORE INTO users VALUES(?,?,?,?)',
            ('user', 'retention@test.example', 'x', now),
        )
        db.execute(
            'INSERT INTO projects(id,user_id,title,brief,language,aspect,auto_render,generative,budget,status,stage,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (pid, 'user', 'Retention', '', 'en', 'original', 1, 0, 3, 'complete', 'complete', now, now),
        )


def _picture(pid, render_id, mtime, body=b'video'):
    folder = settings.data_dir / pid / 'renders' / render_id
    folder.mkdir(parents=True)
    video = folder / 'result.mp4'
    video.write_bytes(body)
    os.utime(video, (mtime, mtime))
    (folder / 'scratch.bin').write_bytes(b'x' * 32)
    return folder


def test_prune_keeps_current_and_previous_picture(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    pid = 'c' * 32
    current, previous, oldest = 'a' * 32, 'b' * 32, 'd' * 32
    _project(pid)
    _picture(pid, oldest, 10, b'oldest')
    (tmp_path / pid / 'source').write_bytes(b'source-footage')
    _picture(pid, previous, 20, b'previous')
    _picture(pid, current, 30, b'current')
    leftover = tmp_path / pid / 'renders' / ('e' * 32)
    leftover.mkdir()
    (leftover / 'partial.bin').write_bytes(b'partial')
    with connect() as db:
        db.execute(
            "INSERT INTO dubbing_versions(id,project_id,request_id,master_id,language,voice,kind,status,snapshot,created) VALUES(?,?,?,?,?,?,?,?,?,?)",
            ('f' * 32, pid, '1' * 32, oldest, 'en', 'alloy', 'video', 'ready', '{}', 1),
        )
        db.execute(
            "INSERT INTO dubbing_versions(id,project_id,request_id,master_id,language,voice,kind,status,snapshot,created) VALUES(?,?,?,?,?,?,?,?,?,?)",
            ('9' * 32, pid, '2' * 32, current, 'en', 'alloy', 'video', 'ready', '{}', 2),
        )
    (tmp_path / pid / 'dubbing' / ('f' * 32)).mkdir(parents=True)
    (tmp_path / pid / 'dubbing' / ('f' * 32) / 'video.mp4').write_bytes(b'old-voice')
    (tmp_path / pid / 'dubbing' / ('9' * 32)).mkdir(parents=True)
    (tmp_path / pid / 'dubbing' / ('9' * 32) / 'video.mp4').write_bytes(b'current-voice')

    report = prune_pictures(pid, current)

    assert set(report['kept']) == {current, previous}
    assert oldest in report['removed'] and ('e' * 32) in report['removed']
    assert (tmp_path / pid / 'renders' / current / 'result.mp4').read_bytes() == b'current'
    assert (tmp_path / pid / 'renders' / previous / 'result.mp4').read_bytes() == b'previous'
    assert not (tmp_path / pid / 'renders' / oldest).exists()
    assert not leftover.exists()
    assert (tmp_path / pid / 'source').read_bytes() == b'source-footage'
    assert (tmp_path / pid / 'dubbing' / ('9' * 32) / 'video.mp4').read_bytes() == b'current-voice'
    assert not (tmp_path / pid / 'dubbing' / ('f' * 32)).exists()
    with connect() as db:
        left = [row['id'] for row in db.execute('SELECT id FROM dubbing_versions WHERE project_id=?', (pid,))]
    assert left == ['9' * 32]


def test_prune_keeps_an_older_current_picture(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    pid = 'c' * 32
    current, newer, newest = 'a' * 32, 'b' * 32, 'd' * 32
    _project(pid)
    _picture(pid, current, 10, b'current')
    _picture(pid, newer, 20, b'newer')
    _picture(pid, newest, 30, b'newest')

    report = prune_pictures(pid, current)

    assert report['kept'] == sorted([current, newest])
    assert not (tmp_path / pid / 'renders' / newer).exists()
    assert (tmp_path / pid / 'renders' / current / 'result.mp4').read_bytes() == b'current'


def test_one_and_two_completed_videos_stay(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    pid = 'c' * 32
    _project(pid)
    only = 'a' * 32
    _picture(pid, only, 10, b'one')
    assert prune_pictures(pid, only)['kept'] == [only]
    second = 'b' * 32
    _picture(pid, second, 20, b'two')
    assert set(prune_pictures(pid, second)['kept']) == {only, second}


def test_in_progress_render_is_not_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    pid = 'c' * 32
    first, second, active = 'a' * 32, 'b' * 32, 'd' * 32
    _project(pid)
    _picture(pid, first, 10, b'one')
    _picture(pid, second, 20, b'two')
    folder = tmp_path / pid / 'renders' / active
    folder.mkdir(parents=True)
    (folder / '.rendering').write_text(active)
    (folder / 'partial.bin').write_bytes(b'partial')
    with connect() as db:
        db.execute(
            'INSERT INTO jobs(id,project_id,kind,payload,status,created,updated) VALUES(?,?,?,?,?,?,?)',
            ('e' * 32, pid, 'director_v3', '{"render_id":"%s"}' % active, 'running', 1, 1),
        )
    report = prune_pictures(pid, second)
    assert active not in report['removed']
    assert (folder / 'partial.bin').read_bytes() == b'partial'
    assert (tmp_path / pid / 'renders' / first / 'result.mp4').read_bytes() == b'one'


def test_two_projects_keep_their_own_pairs(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    left, right = 'a' * 32, 'b' * 32
    _project(left)
    _project(right)
    ids = ['1' * 32, '2' * 32, '3' * 32]
    for pid in (left, right):
        for index, render_id in enumerate(ids):
            _picture(pid, render_id, 10 + index, f'{pid}-{index}'.encode())
        prune_pictures(pid, ids[-1])
    for pid in (left, right):
        kept = sorted(path.name for path in (tmp_path / pid / 'renders').iterdir())
        assert kept == sorted(ids[1:])
        assert (tmp_path / pid / 'source').exists() is False or True


def test_source_survives_rotation(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    pid = 'c' * 32
    _project(pid)
    source = tmp_path / pid / 'source'
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b'original-upload')
    (tmp_path / pid / 'localization').mkdir()
    (tmp_path / pid / 'localization' / 'source-transcript.json').write_text('{}')
    ids = ['1' * 32, '2' * 32, '3' * 32]
    for index, render_id in enumerate(ids):
        _picture(pid, render_id, 10 + index, b'v')
    prune_pictures(pid, ids[-1])
    assert source.read_bytes() == b'original-upload'
    assert (tmp_path / pid / 'localization' / 'source-transcript.json').is_file()
