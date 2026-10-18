"""Two short proofs through the same Director chain Web Studio render uses.

The excerpt window is the experiment. Component choice and step times come
from the cached transcript. SEMANTIC_NUMERIC_RANGE_ENABLED is set only for
the salary proof, in this process.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import director_v3, remotion_engine
from backend.visual_variation import resolve_plan
from scripts.overnight_director_render import gate


def _shift(rows: list[dict], start: float, end: float) -> list[dict]:
    shifted = []
    for row in rows:
        a = float(row.get('start') or 0)
        b = float(row.get('end') or a)
        if b < start or a > end:
            continue
        text = row.get('original') or row.get('text') or row.get('zh') or ''
        shifted.append({
            'id': row.get('id'),
            'start': round(max(0.0, a - start), 3),
            'end': round(min(end - start, b - start), 3),
            'original': text,
            'zh': text,
            'text': text,
        })
    return shifted


def render_excerpt(*, source: Path, rows: list[dict], start: float, end: float, dest: Path, generation_id: str, seed: int = 448815100) -> str:
    seconds = round(end - start, 3)
    plan = resolve_plan(seed, language='zh-CN')
    plan['language'] = 'zh-CN'
    plan['durationSeconds'] = seconds
    plan['visualSeed'] = seed
    plan['generationId'] = generation_id
    transcript = _shift(rows, start, end)
    plan = gate(plan, transcript, seconds)
    speaker = director_v3.speaker_for(seconds, source)
    render_plan = remotion_engine.resolve_scene_plan(
        visual_plan=plan,
        locale='zh-CN',
        duration_seconds=seconds,
        speaker_file=speaker,
        source_ref=str(source),
        generation_id=generation_id,
    )
    render_plan = remotion_engine.attach_transcript_captions(
        render_plan, transcript, locale='zh-CN', dubbed=False,
    )
    visual = remotion_engine.visual_plan_from_render_plan(render_plan)
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest = director_v3.render_assembly(dest, seconds=seconds, speaker=speaker, visual_plan=visual)
    sidecar = dest.with_suffix('.plan.json')
    sidecar.write_text(json.dumps({
        'generationId': generation_id,
        'visualSeed': seed,
        'locale': 'zh-CN',
        'dubbed': False,
        'seconds': seconds,
        'sourceStart': start,
        'sourceEnd': end,
        'scenes': [
            {
                'sceneId': scene.get('sceneId'),
                'componentId': (scene.get('semanticMotionV14') or {}).get('componentId'),
                'visualIntent': (scene.get('semanticMotionV14') or {}).get('visualIntent'),
                'layout': (scene.get('semanticMotionV14') or {}).get('layout'),
                'outputTime': (scene.get('semanticMotionV14') or {}).get('outputTime'),
                'steps': (scene.get('semanticMotionV14') or {}).get('steps'),
                'range': (scene.get('semanticMotionV14') or {}).get('range'),
                'evidence': (scene.get('semanticMotionV14') or {}).get('evidence'),
                'assetId': (scene.get('background') or {}).get('assetId'),
            }
            for scene in plan.get('scenes') or []
        ],
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    return digest


def main() -> None:
    which = sys.argv[1]
    dest = Path(sys.argv[2]).resolve()
    if which == 'original3':
        os.environ['SEMANTIC_NUMERIC_RANGE_ENABLED'] = '0'
        source = Path(sys.argv[3])
        asr = json.loads(Path('data/original3/asr.json').read_text())
        rows = asr['segments'] if isinstance(asr, dict) else asr
        for row in rows:
            row['original'] = row.get('text') or row.get('original') or ''
        print(render_excerpt(
            source=source, rows=rows, start=42.80, end=76.68,
            dest=dest, generation_id='gen_o3_list_proof',
        ))
    elif which == 'original2':
        os.environ['SEMANTIC_NUMERIC_RANGE_ENABLED'] = '1'
        source = Path(sys.argv[3])
        rows = json.loads(Path('data/original2/source.transcript.json').read_text())
        print(render_excerpt(
            source=source, rows=rows, start=15.46, end=35.46,
            dest=dest, generation_id='gen_o2_range_proof',
        ))
    else:
        raise SystemExit('original2 or original3')


if __name__ == '__main__':
    main()
