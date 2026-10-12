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


def _hero_or_none(hero, scenes: list) -> str | None:
    """Omit passport/key SVG heroes when a photo/video plate already carries the beat."""
    if not hero:
        return None
    for scene in scenes:
        if scene.get('sceneId') != 'residency':
            continue
        bg = scene.get('background') or {}
        if bg.get('staged') or (bg.get('assetId') and bg.get('assetId') != 'passport.png'):
            return None
    return hero


def should_use_remotion(project_id: str) -> bool:
    """Supported production path: Remotion when enabled (default V5).

    Project «e» always Remotion. When the flag is off, only «e» stays on Remotion;
    other projects use explicit Hypit legacy — never a silent mix.
    """
    from .director_v3 import PROJECT_ID
    if project_id == PROJECT_ID:
        return True
    return enabled()


def attach_transcript_captions(
    render_plan: dict,
    transcript: list | None,
    *,
    locale: str | None = None,
    dubbed: bool = False,
) -> dict:
    """Stamp timed caption phrases from real transcript onto the render plan."""
    from .caption_phrases import caption_source_label, phrases_from_transcript

    duration = float(render_plan.get('durationSeconds') or 0) or None
    phrases = phrases_from_transcript(transcript, locale=locale or render_plan.get('locale'), duration_s=duration)
    out = dict(render_plan)
    out['captions'] = phrases
    out['captionSource'] = caption_source_label(phrases, dubbed=dubbed)
    compliance = dict(out.get('executionCompliance') or {})
    repairs = compliance.get('repairs') or []
    status = 'passed'
    if repairs:
        status = 'repaired'
    if any((s.get('executionFailed') for s in out.get('scenes') or [])):
        status = 'failed'
    out['executionValidation'] = status
    out['renderer'] = 'remotion'
    if not out.get('directorMode'):
        mode = (out.get('executionCompliance') or {}).get('directorMode')
        if not mode:
            provider = str(getattr(settings, 'llm_provider', None) or 'none').lower()
            mode = 'runpod_llm' if provider == 'runpod' else 'heuristic'
        out['directorMode'] = mode
    return out


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
    Enforces same-source ban (main plate vs inset) via director_media_rules.
    """
    from .director_media_rules import sanitize_scene_layers
    from .director_execution import enforce_plan

    plan = dict(visual_plan or {})
    # Structured execution contract + deterministic repairs (Director V4).
    plan = enforce_plan(plan)
    seed = int(plan.get('visualSeed') or plan.get('visual_seed') or 0)
    scenes = []
    for raw in plan.get('scenes') or []:
        scene = {
            'sceneId': raw.get('sceneId'),
            'semanticPurpose': raw.get('semanticPurpose'),
            'query': raw.get('query'),
            'representation': raw.get('representation'),
            'speaker': dict(raw.get('speaker') or {}),
            'background': dict(raw.get('background') or {}),
            'foreground': dict(raw.get('foreground') or {}),
            'typography': dict(raw.get('typography') or {}),
            'execution': dict(raw.get('execution') or {}),
            'repairs': list(raw.get('repairs') or []),
            'transition': raw.get('transition') or 'cut',
            'motionIntensity': raw.get('motionIntensity') or 'medium',
            'animateGraphics': raw.get('animateGraphics', True),
            'overlayBudget': raw.get('overlayBudget'),
            'rejected': list(raw.get('rejected') or []),
            'mediaGap': raw.get('mediaGap'),
        }
        # Strip director-illegal keys if a buggy planner leaked them.
        for bucket in ('speaker', 'background', 'foreground', 'typography'):
            for bad in ('x', 'y', 'css', 'style', 'fontSize', 'color', 'react'):
                scene[bucket].pop(bad, None)
        scenes.append(sanitize_scene_layers(scene))

    render_plan = {
        'generationId': generation_id or plan.get('generationId') or f'remotion_{uuid.uuid4().hex[:12]}',
        'engine': 'remotion',
        'engineVersion': 'v1',
        'composition': COMPOSITION,
        # Callers must stamp visual_plan.language. No silent RU default.
        'locale': locale or plan.get('language'),
        'fps': FPS,
        'width': WIDTH,
        'height': HEIGHT,
        'durationSeconds': int(duration_seconds),
        'visualSeed': seed,
        'artDirection': plan.get('artDirection') or plan.get('visualStyle'),
        'visualEnergy': plan.get('visualEnergy') or 'balanced',
        'motionIntensity': plan.get('motionIntensity') or 'medium',
        'editingControls': dict(plan.get('editingControls') or {}),
        'speakerFile': speaker_file,
        'sourceRef': source_ref,
        'conceptTriggers': bool(concept_triggers if plan.get('conceptTriggers') is None else plan.get('conceptTriggers')),
        'backgroundPlate': plan.get('backgroundPlate'),
        # Drop decorative SVG hero when residency already has photographic media.
        'heroObject': _hero_or_none(plan.get('heroObject'), scenes),
        'motionRegistry': list(RENDERABLE_SCENE_TYPES),
        'scenes': scenes,
        'executionCompliance': plan.get('executionCompliance') or {},
        'renderer': 'remotion',
        'directorMode': plan.get('directorMode') or (
            'runpod_llm' if str(getattr(settings, 'llm_provider', None) or 'none').lower() == 'runpod'
            else 'heuristic'
        ),
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
    # Always overwrite — caption attachment + executionCompliance must persist.
    dest.write_text(json.dumps(render_plan, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'latest.json').write_text(
        json.dumps({
            'generationId': render_plan['generationId'],
            'visualSeed': render_plan.get('visualSeed'),
            'composition': render_plan.get('composition'),
            'renderer': render_plan.get('renderer') or 'remotion',
            'directorMode': render_plan.get('directorMode'),
            'captionSource': render_plan.get('captionSource'),
            'executionValidation': render_plan.get('executionValidation'),
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
        'editingControls': render_plan.get('editingControls') or {},
        'conceptTriggers': render_plan.get('conceptTriggers', True),
        'backgroundPlate': render_plan.get('backgroundPlate'),
        'heroObject': render_plan.get('heroObject'),
        'scenes': render_plan.get('scenes') or [],
        'language': render_plan.get('locale'),
        'executionCompliance': render_plan.get('executionCompliance') or {},
        'captions': list(render_plan.get('captions') or []),
        'captionSource': render_plan.get('captionSource') or 'unavailable',
        'renderer': render_plan.get('renderer') or 'remotion',
        'executionValidation': render_plan.get('executionValidation') or 'passed',
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
