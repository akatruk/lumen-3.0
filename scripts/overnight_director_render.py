"""Isolated evidence-gated render. Does not touch production or the baseline MP4."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from backend import (
    director_v8,
    director_v10,
    director_v11_1,
    director_v11_2,
    director_v14,
    director_v15,
    director_v3,
    motion_design_v18,
    scene_composer_v16,
    semantic_numeric_range,
)
from backend.director_evidence import apply_evidence_gate
from backend.director_semantics import enrich_plan_from_transcript
from backend.director_v11 import apply_semantic_intelligence
from backend import director_v9


def gate(visual_plan: dict, transcript: list, seconds: float) -> dict:
    locale = visual_plan.get('language') or 'zh-CN'
    cleaned = director_v8.filter_locale_transcript(transcript, locale)
    plan = enrich_plan_from_transcript(visual_plan, cleaned, locale=locale)
    plan = director_v8.expand_plan_for_duration(
        plan, duration_seconds=seconds, transcript=cleaned, locale=locale,
    )
    plan = director_v8.fill_media_for_scenes(plan, seed=plan.get('visualSeed'))
    plan = director_v9.apply_composition_intelligence(plan)
    plan = apply_semantic_intelligence(plan, cleaned, locale=locale)
    plan = director_v11_1.apply_factual_business_motion(plan, cleaned, locale=locale)
    plan = director_v11_2.apply_composition_repair(plan, cleaned, locale=locale)
    plan = director_v8.fill_media_for_scenes(plan, seed=plan.get('visualSeed'))
    plan = director_v9.apply_composition_intelligence(plan)
    plan = director_v10.apply_premium_3d(plan, seed=plan.get('visualSeed'))
    plan = director_v14.apply_semantic_motion(plan, transcript, locale=locale)
    plan = director_v15.apply_semantic_motion_v15(plan, transcript, locale=locale)
    plan = scene_composer_v16.apply_scene_composer(plan, transcript, locale=locale)
    plan = motion_design_v18.apply_motion_design(plan, transcript, locale=locale)
    plan = semantic_numeric_range.apply_numeric_range(plan, transcript, locale=locale)
    plan = apply_evidence_gate(plan, cleaned, locale=locale)
    plan['language'] = locale
    return plan


def render_isolated_60(dest: Path) -> None:
    db = sqlite3.connect('/tmp/lumen-asr-e2e-20261016/lumen.db')
    payload = json.loads(db.execute(
        "select payload from jobs where id='89c29199445f4c5982c40de604b88ef3'"
    ).fetchone()[0])
    from backend import remotion_engine
    source = Path('/tmp/lumen-asr-e2e-20261016/fc451a1e44834e73a28f7e02157e28dd/source')
    plan = gate(payload['visual_plan'], payload['transcript'], 60.1)
    speaker = director_v3.speaker_for(60.1, source)
    render_plan = remotion_engine.resolve_scene_plan(
        visual_plan=plan,
        locale='zh-CN',
        duration_seconds=60.1,
        speaker_file=speaker,
        source_ref=str(source),
        generation_id=plan.get('generationId'),
    )
    render_plan = remotion_engine.attach_transcript_captions(
        render_plan, payload['transcript'], locale='zh-CN', dubbed=False,
    )
    visual = remotion_engine.visual_plan_from_render_plan(render_plan)
    digest = director_v3.render_assembly(dest, seconds=60.1, speaker=speaker, visual_plan=visual)
    print(digest)


if __name__ == '__main__':
    target = Path(sys.argv[1])
    render_isolated_60(target)
