"""Private, on-demand Douyin previews. Never creates projects or analysis jobs."""
import fcntl
import re
import shutil
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from .auth import current_user
from .config import settings
from . import douyin, media

router = APIRouter(prefix='/api/douyin/results')


def owned(rid, user):
    if not re.fullmatch(r'[a-f0-9]{32}', rid):
        raise HTTPException(404, 'douyin_search_expired')
    try:
        return douyin.owned_result(rid, user['id'])
    except douyin.DouyinError as exc:
        raise HTTPException(404, str(exc)) from None


def folder(rid):
    return settings.data_dir / 'douyin_previews' / rid


@router.post('/{rid}/preview')
def prepare(rid: str, request: Request, user=Depends(current_user)):
    from .app import rate_limit
    result = owned(rid, user)
    rate_limit(request, 'douyin_preview', 30, 3600)
    target = folder(rid) / 'preview.mp4'
    if target.is_file():
        return {'url': f'/api/douyin/results/{rid}/preview'}
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with (settings.data_dir / '.douyin-preview.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise HTTPException(429, 'preview_busy') from None
        cache = target.parent.parent
        cache.mkdir(exist_ok=True)
        for item in cache.iterdir():
            if item.is_dir() and item.stat().st_mtime < time.time() - 3600:
                shutil.rmtree(item)
        if target.is_file():
            return {'url': f'/api/douyin/results/{rid}/preview'}
        cached_bytes = sum(p.stat().st_size for p in cache.rglob('*') if p.is_file())
        if cached_bytes > 512 * 1024 ** 2 or shutil.disk_usage(settings.data_dir).free < 1.5 * 1024 ** 3:
            raise HTTPException(507, 'storage_full')
        target.parent.mkdir(exist_ok=True)
        source = target.parent / 'source.download'
        temporary = target.parent / 'preview.partial.mp4'
        try:
            try:
                if not result.get('media_url'):
                    raise douyin.DouyinError('douyin_media_unavailable')
                douyin.download(result['media_url'], source, settings.max_upload_mb * 1024 ** 2)
            except douyin.DouyinError as exc:
                if str(exc) != 'douyin_media_unavailable':
                    raise
                # Refresh only the same Douyin identity when its CDN link has expired.
                refreshed = douyin.fetch_video(result['aweme_id'])
                douyin.download(refreshed['media_url'], source, settings.max_upload_mb * 1024 ** 2)
            meta = media.probe(source)
            if meta['duration'] > settings.max_duration_seconds + 1:
                raise ValueError('video_too_long')
            video = ['-c:v', 'copy'] if meta['codec'] == 'h264' else ['-vf', "scale='min(640,iw)':-2", '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '26', '-pix_fmt', 'yuv420p']
            media.ffmpeg('-i', source, '-map', '0:v:0', '-map', '0:a:0?', *video,
                         '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', temporary, timeout=180)
            checked = media.probe(temporary)
            if not 0 < checked['duration'] <= settings.max_duration_seconds + 1 or abs(checked['duration'] - meta['duration']) > .5:
                raise ValueError('invalid_preview')
            temporary.replace(target)
        except douyin.DouyinError as exc:
            raise HTTPException(503, str(exc)) from None
        except Exception:
            raise HTTPException(503, 'douyin_media_unavailable') from None
        finally:
            source.unlink(missing_ok=True)
            temporary.unlink(missing_ok=True)
    return {'url': f'/api/douyin/results/{rid}/preview'}


@router.get('/{rid}/preview')
def preview(rid: str, user=Depends(current_user)):
    owned(rid, user)
    path = folder(rid) / 'preview.mp4'
    if not path.is_file():
        raise HTTPException(404, 'preview_not_ready')
    return FileResponse(path, media_type='video/mp4', headers={'Cache-Control': 'private, max-age=300'})
