#!/usr/bin/env python3
"""Ordinary Director V3 create-video chain (no Hypit, no preview-only shortcut).

Mirrors studio.create_video → plan_for_request → remotion_engine → director_v3.render_assembly.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--language', default='ru-RU')
    parser.add_argument('--energy', default='balanced')
    parser.add_argument('--duration', type=int, default=None, help='seconds (step 5); default=max from source')
    parser.add_argument('--seed', type=int, default=None)
    args = parser.parse_args()

    from backend import remotion_engine, director_v3, media
    from backend.visual_variation import plan_for_request, stage_backgrounds, resolve_plan, store_plan
    from backend.config import settings

    source = args.source.resolve()
    if not source.is_file():
        raise SystemExit(f'missing source: {source}')
    meta = media.probe(source)
    duration = float(meta['duration'])
    seconds = director_v3.output_seconds(args.duration, duration)
    # Stage project source for speaker_for (>20s uses source-edit.mp4)
    project_dir = Path(settings.data_dir) / args.project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    dest_source = project_dir / 'source'
    if not dest_source.exists() or dest_source.stat().st_size != source.stat().st_size:
        dest_source.write_bytes(source.read_bytes())

    # Same entry as studio.create_video (recent_ids + history).
    if args.seed is not None:
        from backend.visual_variation import recent_asset_ids
        plan = resolve_plan(args.seed, args.energy, 'automatic', recent_asset_ids(settings.data_dir))
        plan['generationId'] = f'ordinary_{args.project_id[:8]}_{seconds}s'
        plan['language'] = args.language
        store_plan(settings.data_dir, args.project_id, plan)
    else:
        plan = plan_for_request(
            settings.data_dir, args.project_id, 'automatic', args.energy, args.language,
        )
        plan = {**plan, 'generationId': f"ordinary_{args.project_id[:8]}_{seconds}s"}

    transcript = plan.get('transcript') or []
    # Optional sidecar transcript next to source (stem or full name).
    for side in (
        source.with_suffix('.transcript.json'),
        Path(str(source) + '.transcript.json'),
        project_dir / 'source.transcript.json',
        project_dir / 'transcript.json',
        project_dir / 'localization' / 'source-transcript.json',
    ):
        if transcript:
            break
        if side.is_file():
            raw = json.loads(side.read_text(encoding='utf-8'))
            if isinstance(raw, dict) and isinstance(raw.get('segments'), list):
                transcript = [
                    {
                        'start': s.get('start'),
                        'end': s.get('end'),
                        'original': s.get('text'),
                        'ru': s.get('text') if str(args.language).startswith('ru') else '',
                        'en': s.get('text') if str(args.language).startswith('en') else '',
                        'zh': s.get('text') if str(args.language).startswith('zh') else '',
                        'id': s.get('id'),
                    }
                    for s in raw['segments']
                ]
            else:
                transcript = raw

    from backend.director_semantics import enrich_plan_from_transcript, motion_diversity_summary
    plan = enrich_plan_from_transcript(plan, transcript, locale=args.language)
    plan['language'] = args.language
    store_plan(settings.data_dir, args.project_id, plan)

    speaker = director_v3.speaker_for(seconds, dest_source)
    public = director_v3._public_director()
    plan = stage_backgrounds(plan, public, ROOT / 'media' / 'library' / 'out')

    render_plan = remotion_engine.resolve_scene_plan(
        visual_plan=plan,
        locale=args.language,
        duration_seconds=seconds,
        speaker_file=speaker,
        source_ref=str(dest_source),
        generation_id=plan['generationId'],
    )
    render_plan = remotion_engine.attach_transcript_captions(
        render_plan, transcript, locale=args.language,
    )
    render_plan['motionDiversity'] = motion_diversity_summary(render_plan.get('scenes') or [])
    remotion_engine.store_render_plan(settings.data_dir, args.project_id, render_plan)

    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    digest = remotion_engine.render_with_plan(out, render_plan)
    accept = director_v3._accept(out, seconds)

    report = {
        'projectId': args.project_id,
        'source': str(source),
        'out': str(out),
        'durationSeconds': seconds,
        'sourceDuration': duration,
        'speakerFile': speaker,
        'language': args.language,
        'generationId': plan['generationId'],
        'visualSeed': plan.get('visualSeed'),
        'deliverySha256': digest,
        'renderer': render_plan.get('renderer') or 'remotion',
        'directorMode': render_plan.get('directorMode') or plan.get('directorMode') or 'heuristic',
        'executionValidation': render_plan.get('executionValidation') or 'passed',
        'captionSource': render_plan.get('captionSource') or 'unavailable',
        'captionCount': len(render_plan.get('captions') or []),
        'metadata': accept,
        'scenes': [
            {
                'sceneId': s.get('sceneId'),
                'query': s.get('query'),
                'representation': s.get('representation'),
                'background': (s.get('background') or {}).get('assetId'),
                'foreground': (s.get('foreground') or {}).get('assetId'),
                'rejected': s.get('rejected'),
                'mediaGap': s.get('mediaGap'),
            }
            for s in render_plan.get('scenes') or []
        ],
        'path': 'plan_for_request≈resolve_plan → resolve_scene_plan → render_with_plan → DirectorV3Preview',
    }
    report_path = out.with_suffix('.report.json')
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'out': str(out), 'seconds': seconds, 'sha': digest[:16], 'report': str(report_path)}))


if __name__ == '__main__':
    main()
