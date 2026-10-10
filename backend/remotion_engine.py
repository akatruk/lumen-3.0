"""Remotion Professional Video Engine V1 — Director → render plan → Remotion.

Feature flag: REMOTION_ENGINE_ENABLED / settings.remotion_engine_enabled.
When off, Hypit remains the picture path for ordinary projects. Project «e»
keeps Director V3 Remotion regardless (existing delivery).
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from .config import settings

log = logging.getLogger(__name__)

FPS = 30
WIDTH = 1080
HEIGHT = 1920
COMPOSITION = 'DirectorV3Preview'

# Motion registry ids Remotion can render today (keep in sync with motion/types).
RENDERABLE_SCENE_TYPES = (
    'kinetic_hook',
    'big_number',
    'progress_steps',
    'speaker_focus',
    'broll_caption',
    'timeline',
    'comparison',
    'split_screen',
    'checklist',
    'stat_reveal',
    'animated_diagram',
)


def enabled() -> bool:
    return bool(getattr(settings, 'remotion_engine_enabled', False))


def should_use_remotion(project_id: str) -> bool:
    """Project «e» always uses Remotion. Others require the feature flag."""
    from .director_v3 import PROJECT_ID
    if project_id == PROJECT_ID:
        return True
    return enabled()


def plans_dir(data_dir, project_id: str) -> Path:
    folder = Path(data_dir) / project_id / 'remotion-plans'
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def resolve_scene_plan(
    *,
    visual_plan: dict | None,
    locale: str | None = None,
    duration_seconds: int = 20,
    speaker_file: str = 'speaker.mp4',
    source_ref: str | None = None,
    concept_triggers: bool = True,
    generation_id: str | None = None,
) -> dict:
    """Validate Director inputs into an immutable Remotion render plan.

    Does not call Remotion. Does not invent asset bytes. Asset ids come from
    the seeded visual plan (media library search already ran upstream).
    """
    plan = dict(visual_plan or {})
    seed = int(plan.get('visualSeed') or plan.get('visual_seed') or 0)
    scenes = []
    for raw in plan.get('scenes') or []:
        scene = {
            'sceneId': raw.get('sceneId'),
            'semanticPurpose': raw.get('semanticPurpose'),
            'query': raw.get('query'),
            'speaker': dict(raw.get('speaker') or {}),
            'background': dict(raw.get('background') or {}),
            'foreground': dict(raw.get('foreground') or {}),
            'typography': dict(raw.get('typography') or {}),
            'transition': raw.get('transition') or 'cut',
            'motionIntensity': raw.get('motionIntensity') or 'medium',
            'rejected': list(raw.get('rejected') or []),
        }
        # Strip director-illegal keys if a buggy planner leaked them.
        for bucket in ('speaker', 'background', 'foreground', 'typography'):
            for bad in ('x', 'y', 'css', 'style', 'fontSize', 'color', 'react'):
                scene[bucket].pop(bad, None)
        scenes.append(scene)

    render_plan = {
        'generationId': generation_id or plan.get('generationId') or f'remotion_{uuid.uuid4().hex[:12]}',
        'engine': 'remotion',
        'engineVersion': 'v1',
        'composition': COMPOSITION,
        'locale': locale or plan.get('language') or 'ru-RU',
        'fps': FPS,
        'width': WIDTH,
        'height': HEIGHT,
        'durationSeconds': int(duration_seconds),
        'visualSeed': seed,
        'artDirection': plan.get('artDirection') or plan.get('visualStyle'),
        'visualEnergy': plan.get('visualEnergy') or 'balanced',
        'motionIntensity': plan.get('motionIntensity') or 'medium',
        'speakerFile': speaker_file,
        'sourceRef': source_ref,
        'conceptTriggers': bool(concept_triggers if plan.get('conceptTriggers') is None else plan.get('conceptTriggers')),
        'backgroundPlate': plan.get('backgroundPlate'),
        'heroObject': plan.get('heroObject'),
        'motionRegistry': list(RENDERABLE_SCENE_TYPES),
        'scenes': scenes,
        'audio': {
            'speech': speaker_file,
            'bed': 'bed.mp3',
            'speechDominant': True,
        },
    }
    return render_plan


def store_render_plan(data_dir, project_id: str, render_plan: dict) -> Path:
    folder = plans_dir(data_dir, project_id)
    dest = folder / f"{render_plan['generationId']}.json"
    if not dest.exists():
        dest.write_text(json.dumps(render_plan, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'latest.json').write_text(
        json.dumps({
            'generationId': render_plan['generationId'],
            'visualSeed': render_plan.get('visualSeed'),
            'composition': render_plan.get('composition'),
        }),
        encoding='utf-8',
    )
    return dest


def visual_plan_from_render_plan(render_plan: dict) -> dict:
    """Props.visualPlan shape expected by DirectorV3."""
    return {
        'generationId': render_plan.get('generationId'),
        'visualSeed': render_plan.get('visualSeed'),
        'artDirection': render_plan.get('artDirection'),
        'visualEnergy': render_plan.get('visualEnergy'),
        'motionIntensity': render_plan.get('motionIntensity'),
        'conceptTriggers': render_plan.get('conceptTriggers', True),
        'backgroundPlate': render_plan.get('backgroundPlate'),
        'heroObject': render_plan.get('heroObject'),
        'scenes': render_plan.get('scenes') or [],
        'language': render_plan.get('locale'),
    }


def render_with_plan(dest: Path, render_plan: dict) -> str:
    """Render via Director V3 Remotion using a resolved plan. Returns sha256."""
    from . import director_v3
    visual = visual_plan_from_render_plan(render_plan)
    return director_v3.render_assembly(
        dest,
        seconds=int(render_plan.get('durationSeconds') or 20),
        speaker=render_plan.get('speakerFile') or 'speaker.mp4',
        visual_plan=visual,
    )
