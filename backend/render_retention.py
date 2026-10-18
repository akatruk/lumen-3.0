"""Each project keeps two finished pictures: the current one and the previous one."""
import json
import logging
import re
import shutil

from .config import settings
from .db import connect

log = logging.getLogger(__name__)
KEEP_PICTURES = 2
_RENDER_ID = re.compile(r'^[a-f0-9]{32}$')


def prune_pictures(pid: str, current: str = '') -> dict:
    """Drop finished pictures beyond the newest two, always retaining `current`."""
    root = (settings.data_dir / pid / 'renders').resolve()
    kept = _kept_ids(root, current, _active_render_ids(pid))
    removed = []
    freed = 0
    if root.is_dir():
        for folder in list(root.iterdir()):
            if folder.name in kept or (folder / '.rendering').is_file():
                continue
            if not (_RENDER_ID.fullmatch(folder.name) or folder.name.startswith('audio-repair-')):
                continue
            target = folder.resolve()
            if root not in target.parents:
                log.error('render retention refused path outside %s: %s', root, target)
                continue
            freed += _sizeof(folder)
            shutil.rmtree(target, ignore_errors=True)
            removed.append(folder.name)
    dropped_audio = _drop_audio(pid, kept)
    if removed or dropped_audio:
        log.info('render retention %s kept=%s removed=%s audio=%s freed=%s', pid, sorted(kept), removed, dropped_audio, freed)
    return {'kept': sorted(kept), 'removed': removed, 'audio': dropped_audio, 'freed': freed}


def _active_render_ids(pid: str) -> set[str]:
    """Folders still owned by a queued or running job must survive rotation."""
    active = set()
    with connect() as db:
        rows = db.execute(
            "SELECT id, payload FROM jobs WHERE project_id=? AND status IN ('queued','running')",
            (pid,),
        ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row['payload'] or '{}')
        except (TypeError, ValueError):
            payload = {}
        if isinstance(payload, dict):
            for key in ('render_id', 'renderId'):
                value = str(payload.get(key) or '')
                if _RENDER_ID.fullmatch(value):
                    active.add(value)
    return active


def _kept_ids(root, current: str, protected: set[str] | None = None) -> set[str]:
    finished = []
    if root.is_dir():
        for folder in root.iterdir():
            if not _RENDER_ID.fullmatch(folder.name):
                continue
            video = folder / 'result.mp4'
            if video.is_file() and video.stat().st_size > 0:
                finished.append((video.stat().st_mtime, folder.name))
    finished.sort(reverse=True)
    kept = []
    if current and _RENDER_ID.fullmatch(current) and (root / current).is_dir():
        kept.append(current)
    for _, name in finished:
        if name in kept:
            continue
        kept.append(name)
        if len(kept) >= KEEP_PICTURES:
            break
    for name in protected or ():
        if _RENDER_ID.fullmatch(name):
            kept.append(name)
    return set(kept)


def _drop_audio(pid: str, kept: set[str]) -> list[str]:
    dropped = []
    with connect() as db:
        protect = set()
        for row in db.execute(
            'SELECT id, source_voice FROM final_music_versions WHERE project_id=? AND master_id IN (%s)' % ','.join('?' * len(kept)),
            (pid, *sorted(kept)),
        ) if kept else []:
            protect.add(row['id'])
            protect.add(row['source_voice'])
        for row in db.execute(
            "SELECT id FROM dubbing_versions WHERE project_id=? AND master_id IN (%s)" % ','.join('?' * len(kept)),
            (pid, *sorted(kept)),
        ) if kept else []:
            protect.add(row['id'])
        selected = db.execute(
            'SELECT version_id FROM project_final_outputs WHERE project_id=? AND master_id IN (%s)' % ','.join('?' * len(kept)),
            (pid, *sorted(kept)),
        ).fetchone() if kept else None
        if selected:
            protect.add(selected['version_id'])
        for table, folder_name in (('final_music_versions', 'audio-mixes'), ('dubbing_versions', 'dubbing')):
            rows = db.execute(
                f'SELECT id, master_id, status FROM {table} WHERE project_id=?',
                (pid,),
            ).fetchall()
            for row in rows:
                master = row['master_id'] or ''
                if not master or master in kept or row['id'] in protect or row['status'] in ('queued', 'running'):
                    continue
                db.execute(f'DELETE FROM {table} WHERE id=? AND project_id=?', (row['id'], pid))
                shutil.rmtree(settings.data_dir / pid / folder_name / row['id'], ignore_errors=True)
                dropped.append(row['id'])
    return dropped


def _sizeof(path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob('*') if item.is_file())
