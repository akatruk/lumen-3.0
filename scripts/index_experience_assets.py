"""Index approved library media into the existing asset_embeddings table.

Images use the CLIP vision encoder. Video keyframes keep frame timestamps.
Text tags use the multilingual CLIP-aligned model. Original files are not modified.
Rejected, quarantined, held, low-quality, and unapproved experimental 3D assets are skipped.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import connect
from backend.db import init_db
from backend.experience_embeddings import (
    IMAGE_MODEL_ID,
    TEXT_MODEL_ID,
    content_hash,
    embed_frames,
    embed_image_batch,
    embed_texts,
    sample_video_frames,
)
from backend.experience_memory import store_asset_embedding
from media.library.search import _eligible_for_auto

RASTER = {'.png', '.jpg', '.jpeg', '.webp'}
VIDEO = {'.mp4', '.webm', '.mov', '.avi'}


def _text(asset: dict) -> str:
    parts = [str(asset.get('id') or ''), str(asset.get('type') or '')]
    for key in ('tags', 'tags_ru', 'tags_zh', 'situations', 'actions', 'sceneRoles'):
        values = asset.get(key) or []
        if isinstance(values, list):
            parts.extend(str(v) for v in values)
    description = asset.get('description') or {}
    if isinstance(description, dict):
        parts.extend(str(v) for v in description.values())
    elif isinstance(description, str):
        parts.append(description)
    return ' '.join(part for part in parts if part)


def _approved(asset: dict) -> bool:
    if not asset.get('id'):
        return False
    if not _eligible_for_auto(asset):
        return False
    if (asset.get('visualFamily') or '') == 'premium_3d':
        return False
    if str(asset.get('id')).startswith('l3d_'):
        return False
    if asset.get('kind') == '3d_motion':
        return False
    return True


def _known() -> set[tuple]:
    with connect() as db:
        if not db.postgres:
            return set()
        rows = db.execute(
            '''SELECT asset_id, modality, content_hash, embedding_model
               FROM asset_embeddings WHERE scope='library' AND project_id IS NULL'''
        ).fetchall()
    return {(row['asset_id'], row['modality'], row['content_hash'], row['embedding_model']) for row in rows}


def _drop_unapproved(eligible_ids: set[str]) -> int:
    removed = 0
    with connect() as db:
        if not db.postgres:
            return 0
        rows = db.execute(
            '''SELECT id, asset_id FROM asset_embeddings
               WHERE scope='library' AND project_id IS NULL'''
        ).fetchall()
        for row in rows:
            if row['asset_id'] not in eligible_ids:
                db.execute('DELETE FROM asset_embeddings WHERE id=?', (row['id'],))
                removed += 1
    return removed


def _rss_mb() -> float | None:
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux reports KB. macOS reports bytes.
        if usage > 10_000_000:
            return round(usage / (1024 * 1024), 1)
        return round(usage / 1024, 1)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=Path('media/library/out/manifest.json'))
    parser.add_argument('--limit', type=int, default=40)
    parser.add_argument('--images', type=int, default=0)
    parser.add_argument('--videos', type=int, default=0)
    parser.add_argument('--approved', action='store_true', help='Index every quality-gate-approved raster and video')
    parser.add_argument('--only-prefix', default='', help='Index only ids with this prefix; does not delete other rows')
    args = parser.parse_args()
    started = time.perf_counter()
    init_db()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    assets = manifest.get('assets') or []
    root = args.manifest.parent
    indexed = {'text': 0, 'image': 0, 'video_keyframe': 0, 'skipped': 0, 'errors': 0}
    known = _known()
    if args.approved or args.only_prefix:
        eligible = [asset for asset in assets if _approved(asset)]
        if args.only_prefix:
            eligible = [
                asset for asset in eligible
                if str(asset.get('id') or '').startswith(args.only_prefix)
            ]
        if args.approved and not args.only_prefix:
            indexed['removed_unapproved'] = _drop_unapproved({asset['id'] for asset in eligible})
            known = _known()
        pending_text = []
        pending_images = []
        for asset in eligible:
            asset_id = asset['id']
            text = _text(asset)
            digest = content_hash(text)
            if (asset_id, 'text', digest, TEXT_MODEL_ID) not in known:
                pending_text.append((asset_id, text))
            relative = asset.get('file') or ''
            path = root / relative if relative else None
            suffix = path.suffix.lower() if path else ''
            kind = asset.get('type')
            if path and path.is_file() and kind == 'image' and suffix in RASTER:
                raw_hash = content_hash(path.read_bytes())
                if (asset_id, 'image', raw_hash, IMAGE_MODEL_ID) not in known:
                    pending_images.append((asset_id, path))
            elif path and path.is_file() and kind == 'video' and suffix in VIDEO:
                try:
                    frames = sample_video_frames(path, limit=3)
                except Exception:
                    indexed['errors'] += 1
                    continue
                pending_frames = [
                    frame for frame in frames
                    if (asset_id, 'video_keyframe', frame['content_hash'], IMAGE_MODEL_ID) not in known
                ]
                if not pending_frames:
                    continue
                try:
                    for spec in embed_frames(pending_frames):
                        store_asset_embedding(asset_id=asset_id, modality='video_keyframe', spec=spec, scope='library')
                        indexed['video_keyframe'] += 1
                        known.add((asset_id, 'video_keyframe', spec['content_hash'], spec['embedding_model']))
                except Exception:
                    indexed['errors'] += 1
        for start in range(0, len(pending_text), 32):
            chunk = pending_text[start:start + 32]
            for (asset_id, _text_value), spec in zip(chunk, embed_texts([item[1] for item in chunk])):
                store_asset_embedding(asset_id=asset_id, modality='text', spec=spec, scope='library', locale='multi')
                indexed['text'] += 1
        for start in range(0, len(pending_images), 16):
            chunk = pending_images[start:start + 16]
            try:
                specs = embed_image_batch([path for _, path in chunk])
            except Exception:
                indexed['errors'] += len(chunk)
                continue
            for (asset_id, _path), spec in zip(chunk, specs):
                store_asset_embedding(asset_id=asset_id, modality='image', spec=spec, scope='library')
                indexed['image'] += 1
    else:
        images_left = args.images
        videos_left = args.videos
        for asset in assets:
            if indexed['text'] >= args.limit and images_left <= 0 and videos_left <= 0:
                break
            asset_id = asset.get('id')
            if not asset_id or not _approved(asset):
                indexed['skipped'] += 1
                continue
            if indexed['text'] < args.limit:
                spec = embed_texts([_text(asset)])[0]
                store_asset_embedding(asset_id=asset_id, modality='text', spec=spec, scope='library', locale='multi')
                indexed['text'] += 1
            relative = asset.get('file')
            path = root / relative if relative else None
            suffix = path.suffix.lower() if path else ''
            kind = asset.get('type')
            if path and path.is_file() and kind == 'image' and images_left > 0 and suffix in RASTER:
                spec = embed_image_batch([path])[0]
                store_asset_embedding(asset_id=asset_id, modality='image', spec=spec, scope='library')
                indexed['image'] += 1
                images_left -= 1
            if path and path.is_file() and kind == 'video' and videos_left > 0 and suffix in VIDEO:
                for spec in embed_frames(sample_video_frames(path, limit=1)):
                    store_asset_embedding(asset_id=asset_id, modality='video_keyframe', spec=spec, scope='library')
                    indexed['video_keyframe'] += 1
                videos_left -= 1
    indexed['seconds'] = round(time.perf_counter() - started, 2)
    indexed['rss_mb'] = _rss_mb()
    print(json.dumps(indexed))


if __name__ == '__main__':
    main()
