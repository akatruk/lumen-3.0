"""Index library text (and a few visuals) into asset_embeddings.

Text uses the multilingual CLIP-aligned model. Images and video keyframes use
the CLIP vision encoder. Weights stay on the embedding cache directory.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db import init_db
from backend.experience_embeddings import embed_image, embed_text, embed_video_keyframes
from backend.experience_memory import store_asset_embedding


def _text(asset: dict) -> str:
    parts = [str(asset.get('id') or ''), str(asset.get('type') or '')]
    for key in ('tags', 'tags_ru', 'tags_zh'):
        values = asset.get(key) or []
        if isinstance(values, list):
            parts.extend(str(v) for v in values)
    description = asset.get('description') or {}
    if isinstance(description, dict):
        parts.extend(str(v) for v in description.values())
    elif isinstance(description, str):
        parts.append(description)
    return ' '.join(part for part in parts if part)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=Path('media/library/out/manifest.json'))
    parser.add_argument('--limit', type=int, default=40)
    parser.add_argument('--images', type=int, default=0)
    parser.add_argument('--videos', type=int, default=0)
    args = parser.parse_args()
    init_db()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    assets = manifest.get('assets') or []
    root = args.manifest.parent
    indexed = {'text': 0, 'image': 0, 'video_keyframe': 0}
    images_left = args.images
    videos_left = args.videos
    for asset in assets:
        if indexed['text'] >= args.limit and images_left <= 0 and videos_left <= 0:
            break
        asset_id = asset.get('id')
        if not asset_id:
            continue
        if indexed['text'] < args.limit:
            spec = embed_text(_text(asset))
            store_asset_embedding(asset_id=asset_id, modality='text', spec=spec, scope='library', locale='multi')
            indexed['text'] += 1
        relative = asset.get('file')
        path = root / relative if relative else None
        suffix = path.suffix.lower() if path else ''
        kind = asset.get('type')
        if path and path.is_file() and kind == 'image' and images_left > 0 and suffix in {'.png', '.jpg', '.jpeg', '.webp'}:
            spec = embed_image(path)
            store_asset_embedding(asset_id=asset_id, modality='image', spec=spec, scope='library')
            indexed['image'] += 1
            images_left -= 1
        if path and path.is_file() and kind == 'video' and videos_left > 0 and suffix in {'.mp4', '.webm', '.mov', '.avi'}:
            for spec in embed_video_keyframes(path, limit=1):
                store_asset_embedding(asset_id=asset_id, modality='video_keyframe', spec=spec, scope='library')
                indexed['video_keyframe'] += 1
            videos_left -= 1
    print(json.dumps(indexed))


if __name__ == '__main__':
    main()
