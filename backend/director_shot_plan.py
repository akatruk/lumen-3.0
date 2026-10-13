"""Director V7 — per-scene shot plans + motion choreography + anti-repetition.

Plans visual *actions* over time. Remotion executes; meaning stays speech-bound.
"""
from __future__ import annotations

from typing import Any

# Fixed editorial progression for the 6-beat DirectorV3 composition.
# Framing variety is intentional, not random template shuffle.
_BEAT_SHOTS: dict[str, dict[str, Any]] = {
    'hook': {
        'narrativePurpose': 'hook',
        'speakerPresence': 'primary',
        'speakerLayout': 'speaker_punch_in',
        'speakerFraming': 'fullscreen',
        'primaryVisual': 'speaker',
        'supportingVisual': 'kinetic_keyword',
        'foregroundObject': 'hero_concept',
        'backgroundTreatment': 'slow_zoom_in',
        'motionFamily': 'camera+kinetic',
        'kineticTypography': 'phrase_pop',
        'captionPlacement': 'bottom_safe',
        'transition': 'cut',
        'cardMode': 'none',
        'choreography': [
            {'at': 0.0, 'action': 'speaker_establish', 'detail': 'close punch-in'},
            {'at': 0.25, 'action': 'kinetic_keyword', 'detail': 'headline from speech'},
            {'at': 0.7, 'action': 'concept_route', 'detail': 'relocation relationship'},
        ],
    },
    'residency': {
        'narrativePurpose': 'document',
        'speakerPresence': 'primary',
        'speakerLayout': 'speaker_with_foreground',
        'speakerFraming': 'split',
        'primaryVisual': 'library_media',
        'supportingVisual': 'speaker',
        'foregroundObject': 'none',
        'backgroundTreatment': 'mask_reveal',
        'motionFamily': 'media+mask',
        'kineticTypography': 'none',
        'captionPlacement': 'bottom_safe',
        'transition': 'crossfade',
        'cardMode': 'none',
        'choreography': [
            {'at': 0.0, 'action': 'media_reveal', 'detail': 'mask reveal plate'},
            {'at': 0.35, 'action': 'speaker_enter', 'detail': 'split column'},
            {'at': 0.8, 'action': 'hold', 'detail': 'speech continues'},
        ],
    },
    'consult': {
        'narrativePurpose': 'proof',
        'speakerPresence': 'pip',
        'speakerLayout': 'speaker_with_media',
        'speakerFraming': 'pip',
        'primaryVisual': 'broll_consult',
        'supportingVisual': 'speaker_pip',
        'foregroundObject': 'none',
        'backgroundTreatment': 'ambient_loop',
        'motionFamily': 'broll',
        'kineticTypography': 'none',
        'captionPlacement': 'bottom_safe',
        'transition': 'cut',
        'cardMode': 'none',
        'choreography': [
            {'at': 0.0, 'action': 'broll_full', 'detail': 'consultation plate'},
            {'at': 0.4, 'action': 'speaker_pip', 'detail': 'large PIP floor'},
        ],
    },
    'beside': {
        'narrativePurpose': 'criteria',
        'speakerPresence': 'primary',
        'speakerLayout': 'speaker_split_left',
        'speakerFraming': 'split',
        'primaryVisual': 'progressive_card',
        'supportingVisual': 'speaker',
        'foregroundObject': 'none',
        'backgroundTreatment': 'static_editorial',
        'motionFamily': 'info_reveal',
        'kineticTypography': 'editorial_slide',
        'captionPlacement': 'bottom_safe',
        'transition': 'cut',
        'cardMode': 'progressive_one',
        'choreography': [
            {'at': 0.0, 'action': 'speaker_column', 'detail': 'left speaker'},
            {'at': 0.2, 'action': 'card_1', 'detail': 'goals'},
            {'at': 0.45, 'action': 'card_2', 'detail': 'family replaces'},
            {'at': 0.7, 'action': 'card_3', 'detail': 'budget replaces'},
        ],
    },
    'steps': {
        'narrativePurpose': 'process',
        'speakerPresence': 'secondary',
        'speakerLayout': 'speaker_with_diagram',
        'speakerFraming': 'pip',
        'primaryVisual': 'progress_steps',
        'supportingVisual': 'speaker_pip',
        'foregroundObject': 'none',
        'backgroundTreatment': 'gradient_reveal',
        'motionFamily': 'infographic',
        'kineticTypography': 'none',
        'captionPlacement': 'bottom_safe',
        'transition': 'cut',
        'cardMode': 'none',
        'choreography': [
            {'at': 0.0, 'action': 'title', 'detail': 'process title'},
            {'at': 0.25, 'action': 'step_1', 'detail': 'consult'},
            {'at': 0.5, 'action': 'step_2', 'detail': 'program'},
            {'at': 0.75, 'action': 'step_3', 'detail': 'documents'},
        ],
    },
    'return': {
        'narrativePurpose': 'payoff',
        'speakerPresence': 'primary',
        'speakerLayout': 'speaker_medium',
        'speakerFraming': 'fullscreen',
        'primaryVisual': 'speaker',
        'supportingVisual': 'none',
        'foregroundObject': 'none',
        'backgroundTreatment': 'slow_zoom_out',
        'motionFamily': 'camera',
        'kineticTypography': 'none',
        'captionPlacement': 'bottom_safe',
        'transition': 'crossfade',
        'cardMode': 'none',
        'choreography': [
            {'at': 0.0, 'action': 'speaker_return', 'detail': 'fullscreen medium'},
            {'at': 0.5, 'action': 'hold', 'detail': 'payoff hold'},
        ],
    },
}

_KEYWORD_RULES: tuple[tuple[str, str, str], ...] = (
    # substring (any case), keyword id, concept preset
    # Immigration (speech-evidence only)
    ('переезд', 'relocation', 'route_link'),
    ('relocati', 'relocation', 'route_link'),
    ('жительств', 'residency', 'document_stamp'),
    ('residenc', 'residency', 'document_stamp'),
    ('паспорт', 'passport', 'document_stamp'),
    ('passport', 'passport', 'document_stamp'),
    ('программ', 'program', 'steps_reveal'),
    ('консульт', 'consult', 'comparison_columns'),
    ('consult', 'consult', 'comparison_columns'),
    ('документ', 'documents', 'document_stamp'),
    ('семь', 'family', 'family_cluster'),
    ('бюджет', 'budget', 'budget_scale'),
    ('целей', 'goals', 'comparison_columns'),
    ('целя', 'goals', 'comparison_columns'),
    # Investment / corporate structure (origin1-class)
    ('investment', 'investment', 'comparison_columns'),
    ('инвестиц', 'investment', 'comparison_columns'),
    ('投资', 'investment', 'comparison_columns'),
    ('shareholder', 'shareholder', 'comparison_columns'),
    ('акционер', 'shareholder', 'comparison_columns'),
    ('股东', 'shareholder', 'comparison_columns'),
    ('capital', 'capital', 'budget_scale'),
    ('капитал', 'capital', 'budget_scale'),
    ('资本', 'capital', 'budget_scale'),
    ('thailand', 'thailand', 'route_link'),
    ('тайланд', 'thailand', 'route_link'),
    ('泰国', 'thailand', 'route_link'),
    ('ownership', 'ownership', 'comparison_columns'),
    ('control', 'control', 'comparison_columns'),
    ('контроль', 'control', 'comparison_columns'),
    ('控制', 'control', 'comparison_columns'),
)


def extract_keywords(text: str, locale: str | None = None) -> list[dict[str, str]]:
    """Semantic keywords for emphasis — not caption fragments."""
    lowered = (text or '').lower()
    hits = []
    seen = set()
    for needle, kid, preset in _KEYWORD_RULES:
        if needle in lowered and kid not in seen:
            seen.add(kid)
            hits.append({'id': kid, 'preset': preset, 'match': needle})
    return hits


def composition_signature(scene: dict) -> str:
    sp = scene.get('speaker') or {}
    bg = scene.get('background') or {}
    shot = scene.get('shotPlan') or {}
    return '|'.join([
        str(sp.get('framing') or shot.get('speakerFraming') or ''),
        str(sp.get('layout') or shot.get('speakerLayout') or ''),
        str(shot.get('motionFamily') or bg.get('treatment') or ''),
        str(shot.get('cardMode') or 'none'),
        str((bg.get('assetId') or '')[:24]),
    ])


def anti_repeat_ok(scenes: list[dict]) -> dict[str, Any]:
    sigs = [composition_signature(s) for s in scenes]
    streak = 1
    max_streak = 1
    for i in range(1, len(sigs)):
        if sigs[i] == sigs[i - 1]:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 1
    # Also flag three consecutive splits even if layouts differ slightly.
    framings = [
        ((s.get('speaker') or {}).get('framing') or (s.get('shotPlan') or {}).get('speakerFraming'))
        for s in scenes
    ]
    split_streak = 0
    max_split = 0
    for f in framings:
        if f == 'split':
            split_streak += 1
            max_split = max(max_split, split_streak)
        else:
            split_streak = 0
    return {
        'signatures': sigs,
        'maxIdenticalStreak': max_streak,
        'maxSplitStreak': max_split,
        'pass': max_streak < 3 and max_split < 3,
    }


def apply_shot_plans(plan: dict, *, locale: str | None = None, transcript_text: str = '') -> dict:
    """Stamp shotPlan + enforce editorial framing progression on each scene."""
    locale = locale or plan.get('language')
    keywords = extract_keywords(transcript_text, locale)
    scenes_out = []
    for scene in plan.get('scenes') or []:
        scene = dict(scene)
        sid = scene.get('sceneId') or ''
        shot = dict(_BEAT_SHOTS.get(sid) or {})
        if not shot:
            scenes_out.append(scene)
            continue
        # Apply speaker layout from shot plan (Director decides; Remotion executes).
        speaker = dict(scene.get('speaker') or {})
        speaker['layout'] = shot['speakerLayout']
        speaker['treatment'] = shot['speakerLayout']
        speaker['framing'] = shot['speakerFraming']
        speaker['visibility'] = (
            'primary' if shot['speakerFraming'] in ('fullscreen', 'split') else 'pip'
        )
        scene['speaker'] = speaker
        bg = dict(scene.get('background') or {})
        bg['treatment'] = shot['backgroundTreatment']
        scene['background'] = bg
        scene['transition'] = shot['transition']
        typ = dict(scene.get('typography') or {})
        if shot.get('kineticTypography') and shot['kineticTypography'] != 'none':
            typ['treatment'] = shot['kineticTypography']
            typ['animate'] = 'pop' if 'pop' in shot['kineticTypography'] else typ.get('animate') or 'fade'
        if shot.get('cardMode') == 'progressive_one':
            typ['cardMode'] = 'progressive_one'
        scene['typography'] = typ
        exe = dict(scene.get('execution') or {})
        exe['speakerFraming'] = shot['speakerFraming']
        exe['speakerVisibility'] = speaker['visibility']
        exe['motionPreset'] = shot.get('motionFamily')
        exe['cardMode'] = shot.get('cardMode')
        scene['execution'] = exe
        # Keywords for concept viz — capped, speech-linked.
        scene_keywords = keywords[:2] if sid in ('hook', 'residency', 'beside') else keywords[:1]
        shot['keywords'] = scene_keywords
        scene['shotPlan'] = shot
        # Intensity: hook high; payoff medium.
        if sid == 'hook':
            scene['motionIntensity'] = 'high'
        elif sid == 'return':
            scene['motionIntensity'] = 'medium'
        scenes_out.append(scene)

    out = dict(plan)
    out['scenes'] = scenes_out
    out['keywords'] = keywords
    out['antiRepetition'] = anti_repeat_ok(scenes_out)
    out['shotPlanVersion'] = 'v7'
    return out


def motion_usage_report(plan: dict) -> dict[str, Any]:
    scenes = plan.get('scenes') or []
    families = []
    layouts = []
    choreo_count = 0
    for s in scenes:
        shot = s.get('shotPlan') or {}
        families.append(shot.get('motionFamily'))
        layouts.append((s.get('speaker') or {}).get('layout'))
        choreo_count += len(shot.get('choreography') or [])
    anti = plan.get('antiRepetition') or anti_repeat_ok(scenes)
    return {
        'shotPlanVersion': plan.get('shotPlanVersion'),
        'motionFamilies': families,
        'uniqueMotionFamilies': len({f for f in families if f}),
        'layouts': layouts,
        'uniqueLayouts': len({x for x in layouts if x}),
        'choreographyActions': choreo_count,
        'keywords': plan.get('keywords') or [],
        'antiRepetition': anti,
        'pass': bool(anti.get('pass')) and len({x for x in layouts if x}) >= 4,
    }
