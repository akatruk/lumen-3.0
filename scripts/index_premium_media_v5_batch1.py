#!/usr/bin/env python3
"""Index Premium Media Factory V5 first-batch recipes into the existing manifest.

Extends media/library/out/manifest.json — no second library.
Does not overwrite approved binary masters. Recipe rows are remotion/metadata only
until GPU-approved generative masters exist.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / 'recipes' / 'premium-media-factory-v5-batch1.json'
MANIFEST = ROOT / 'media' / 'library' / 'out' / 'manifest.json'


def _row(asset_id: str, *, category: str, tags: list[str], description: str, extra: dict | None = None) -> dict:
    base = {
        'id': asset_id,
        'type': 'motion',
        'category': category,
        'tags': tags,
        'tags_ru': tags,
        'tags_zh': tags,
        'description': description,
        'file': f'remotion://premium-media-v5/{asset_id}',
        'aspectRatio': '9:16',
        'composition': 'remotion_deterministic',
        'background': category == 'backgrounds',
        'qualityScore': 0.82,
        'textSafe': True,
        'source': 'remotion',
        'sceneRoles': ['background'] if category == 'backgrounds' else ['explanation', 'transition'],
        'energy': 'balanced',
        'emotion': 'editorial',
        'visualFamily': 'deterministic_motion',
        'status': 'needs_review',
        'batch': 'premium-media-factory-v5-batch1',
        'indexedAt': datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        base.update(extra)
    return base


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--recipe', type=Path, default=RECIPE)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    recipe = json.loads(args.recipe.read_text(encoding='utf-8'))
    batch = recipe['batch']
    rows: list[dict] = []
    for bg in batch['cinematic_backgrounds']:
        rows.append(
            _row(
                bg['id'],
                category='backgrounds',
                tags=['cinematic', 'plate', bg['treatment'], 'v5'],
                description=f"Remotion cinematic plate {bg['treatment']}",
                extra={'treatment': bg['treatment'], 'sceneRoles': ['background', 'hero']},
            )
        )
    for px in batch['parallax_layers']:
        rows.append(
            _row(
                px['id'],
                category='layers',
                tags=['parallax', 'depth', 'v5'],
                description='Remotion parallax layer stack',
                extra={'depths': px.get('depths'), 'sceneRoles': ['background', 'overlay']},
            )
        )
    for bm in batch['business_motion']:
        rows.append(
            _row(
                bm['id'],
                category='business',
                tags=['business', 'connector', bm['component'], 'v5'],
                description=f"Deterministic business motion {bm['component']}",
                extra={
                    'component': bm['component'],
                    'status': 'approved' if bm.get('status') == 'approved_code' else 'needs_review',
                    'sceneRoles': ['explanation', 'proof'],
                    'qualityScore': 0.9,
                },
            )
        )
    for tr in batch['transitions']:
        rows.append(
            _row(
                tr['id'],
                category='transition',
                tags=['transition', tr['type'], 'v5'],
                description=f"Remotion transition {tr['type']}",
                extra={'transitionType': tr['type'], 'status': 'approved', 'sceneRoles': ['transition']},
            )
        )
    for p3d in batch['premium_3d']:
        rows.append(
            _row(
                p3d['id'],
                category='objects',
                tags=['premium_3d', 'v5', p3d.get('base', '')],
                description=f"3D candidate from {p3d.get('base')} — QA only; not production_ready",
                extra={
                    'visualFamily': 'premium_3d',
                    'status': 'needs_review',
                    'qualityScore': 0.55,
                    'sceneRoles': ['foreground_object', 'semantic_object'],
                    'note': 'quality_gate_v2 production_ready stays empty; PREMIUM_3D_MODE=off',
                },
            )
        )

    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    assets = list(manifest.get('assets') or [])
    by_id = {a.get('id'): i for i, a in enumerate(assets)}
    added, updated = 0, 0
    for row in rows:
        aid = row['id']
        if aid in by_id:
            prev = assets[by_id[aid]]
            if prev.get('status') == 'approved' and prev.get('source') != 'remotion':
                # Never overwrite approved binary masters.
                continue
            assets[by_id[aid]] = {**prev, **row}
            updated += 1
        else:
            assets.append(row)
            by_id[aid] = len(assets) - 1
            added += 1

    manifest['assets'] = assets
    manifest['premiumMediaFactoryV5'] = {
        'batch': 'batch1',
        'recipe': str(args.recipe.relative_to(ROOT)),
        'added': added,
        'updated': updated,
        'gpu': recipe.get('policy', {}).get('gpu'),
        'indexedAt': datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps({'added': added, 'updated': updated, 'total': len(assets), 'dryRun': args.dry_run}))
    if args.dry_run:
        return
    bak = args.manifest.with_suffix('.json.bak-pmv5')
    if not bak.exists():
        shutil.copy2(args.manifest, bak)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
