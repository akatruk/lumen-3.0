"""Director V4 — execution compliance: structured plan, validate, repair.

Director defines intent. Remotion enforces layout. This module validates the
scene contract *before* render and applies deterministic repairs. It does not
lengthen LLM prompts.

Baseline defects in Hypit outputs (tiny circle PIP, fragment cards, duplicate
49%) are Hypit interpretation failures — Remotion path must not reproduce them.
"""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

# Portrait frame (matches motion/src/preview/portraitLayouts.ts).
FRAME_W = 1080
FRAME_H = 1920
# Minimum PIP width as fraction of frame — phone-readable face (~28–35%).
MIN_PIP_WIDTH_FRAC = 0.30
MIN_PIP_WIDTH_PX = int(FRAME_W * MIN_PIP_WIDTH_FRAC)  # 324
DEFAULT_PIP = {'width': 360, 'height': 480, 'right': 36, 'bottom': 220}

# Layouts that keep a meaningful speaker panel (not a decorative avatar).
SPEAKER_PRIMARY = {
    'speaker_fullscreen', 'speaker_closeup', 'speaker_medium', 'speaker_punch_in',
    'speaker_split_left', 'speaker_split_right',
}
SPEAKER_PIP_OK = {
    'speaker_with_media', 'speaker_with_foreground', 'speaker_with_diagram',
}
# Tiny-circle risk if planner emits these without bumping size.
SPEAKER_PIP_RISK = SPEAKER_PIP_OK | {'speaker_pip', 'host_circle', 'circle'}

FRAGMENT_HEADING = re.compile(
    r'^(look at|look|and the|but this|but the|or the|usually|in other words|'
    r'that is|this is|so that|and then|the|a|an|of|to|for|with)$',
    re.I,
)
FRAGMENT_PREFIX = re.compile(
    r'^(and the|but this|but the|or the|usually|in other words|that is|this is|so that|and then)\b',
    re.I,
)
INCOMPLETE_TAIL = re.compile(
    r'[,;:\-–—]\s*$|^\W+$|\b(is|are|of|the|a|an|to|for|with|and|but)\s*$',
    re.I,
)
WORDY_STOP = re.compile(r'^(and|but|or|the|a|an|of|to|for|with|in|on)\b', re.I)

MAX_REPAIR_ATTEMPTS = 3


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[\w%]+", text or '', flags=re.UNICODE) if w]


def is_incomplete_heading(text: str | None, *, kinetic_reveal: bool = False) -> bool:
    """True when a headline is not a complete semantic unit."""
    if kinetic_reveal:
        return False
    raw = ' '.join(str(text or '').split())
    if not raw:
        return True
    if FRAGMENT_HEADING.match(raw.strip()):
        return True
    if FRAGMENT_PREFIX.match(raw) and len(_words(raw)) < 8:
        return True
    tokens = _words(raw)
    if len(tokens) <= 1 and not re.search(r'\d|%|\$', raw):
        # Single non-numeric token ("Look") is incomplete; "49%" is ok.
        if not re.fullmatch(r'[\d.,]+%?', raw.strip()):
            return True
    if INCOMPLETE_TAIL.search(raw) and len(tokens) < 8:
        return True
    if WORDY_STOP.match(raw) and len(tokens) < 4:
        return True
    return False


def is_transcript_fragment_card(card_text: str | None, caption: str | None = None) -> bool:
    """Card that is only an arbitrary incomplete speech fragment — not a concept."""
    card = ' '.join(str(card_text or '').split())
    if not card:
        return True
    if is_incomplete_heading(card):
        return True
    cap = ' '.join(str(caption or '').split())
    if cap and card.lower() in cap.lower() and len(_words(card)) < 6:
        # Substring of the spoken line with few tokens → subtitle, not card.
        return True
    # Trailing comma / conjunction-only starts.
    if card.endswith(',') or FRAGMENT_HEADING.match(card.split()[0] if card.split() else ''):
        if len(_words(card)) < 8:
            return True
    return False


def is_redundant_stat_pair(headline: str | None, card: str | None) -> bool:
    """Same statistic twice without a distinct relationship explanation."""
    h = ' '.join(str(headline or '').split())
    c = ' '.join(str(card or '').split())
    if not h or not c:
        return False
    nums_h = set(re.findall(r'\d+(?:[.,]\d+)?%?', h))
    nums_c = set(re.findall(r'\d+(?:[.,]\d+)?%?', c))
    if not nums_h or not nums_h.intersection(nums_c):
        return False
    # Card adds nothing beyond the number itself.
    c_stripped = re.sub(r'\d+(?:[.,]\d+)?%?', '', c).strip(' .:-–—')
    return len(_words(c_stripped)) < 2


def normalize_execution(scene: dict) -> dict:
    """Fill structured Director V4 execution fields from existing scene keys."""
    out = deepcopy(scene)
    speaker = dict(out.get('speaker') or {})
    layout = speaker.get('layout') or 'speaker_fullscreen'
    typography = dict(out.get('typography') or {})
    execution = dict(out.get('execution') or {})

    purpose = out.get('semanticPurpose') or execution.get('scenePurpose') or 'explain'
    headline = (
        execution.get('headline')
        or typography.get('headline')
        or typography.get('title')
        or ''
    )
    caption = execution.get('caption') or typography.get('caption') or ''
    card = execution.get('cardText') or typography.get('card') or typography.get('body') or ''

    framing = execution.get('speakerFraming') or (
        'fullscreen' if layout in ('speaker_fullscreen', 'speaker_closeup', 'speaker_medium', 'speaker_punch_in')
        else 'split' if layout in ('speaker_split_left', 'speaker_split_right')
        else 'pip'
    )
    visibility = execution.get('speakerVisibility') or (
        'primary' if framing in ('fullscreen', 'split') else 'pip'
    )
    # Keep requested pip size for validation; repair bumps below-min values.
    pip = dict(DEFAULT_PIP)
    if execution.get('pip'):
        pip.update({k: execution['pip'][k] for k in ('width', 'height', 'right', 'bottom') if k in execution['pip']})
    pip['width'] = int(pip.get('width') or DEFAULT_PIP['width'])
    pip['height'] = int(pip.get('height') or max(DEFAULT_PIP['height'], int(pip['width'] * 4 / 3)))

    media_role = execution.get('mediaRole') or (
        'supporting' if (out.get('background') or {}).get('assetId') else 'none'
    )
    caption_mode = execution.get('captionMode') or (
        'speech' if caption or True else 'off'
    )
    motion = execution.get('motionPreset') or typography.get('animate') or out.get('transition') or 'cut'

    execution.update({
        'scenePurpose': purpose,
        'speakerFraming': framing,
        'speakerVisibility': visibility,
        'mediaRole': media_role,
        'headline': headline,
        'cardText': card,
        'caption': caption,
        'captionMode': caption_mode,
        'motionPreset': motion,
        'pip': pip,
        'safeZones': execution.get('safeZones') or {
            'faceBand': {'top': 0.1, 'bottom': 0.46},
            'captionClearance': 160,
            'sideMargin': 28,
        },
        'timing': execution.get('timing') or {
            'entranceFrames': 14,
            'holdMinFrames': 45,
            'exitFrames': 12,
        },
        'expectedResult': execution.get('expectedResult') or (
            f'{framing} speaker; {media_role} media; caption={caption_mode}'
        ),
        'kineticReveal': bool(execution.get('kineticReveal')),
    })
    speaker['layout'] = layout
    speaker['framing'] = framing
    speaker['visibility'] = visibility
    speaker['pip'] = pip
    out['speaker'] = speaker
    out['typography'] = typography
    out['execution'] = execution
    return out


def validate_scene(scene: dict) -> list[dict]:
    """Return list of {code, severity, detail} for one scene."""
    s = normalize_execution(scene)
    ex = s['execution']
    issues = []
    framing = ex['speakerFraming']
    pip_w = int((ex.get('pip') or {}).get('width') or 0)
    if framing == 'pip' and pip_w < MIN_PIP_WIDTH_PX:
        issues.append({
            'code': 'speaker_too_small',
            'severity': 'blocking',
            'detail': f'pip width {pip_w}px < min {MIN_PIP_WIDTH_PX}px',
        })
    if framing == 'pip' and (s.get('speaker') or {}).get('layout') in ('host_circle', 'circle'):
        issues.append({
            'code': 'tiny_circle_layout',
            'severity': 'blocking',
            'detail': 'circle avatar layout forbidden; use rounded PIP or split',
        })

    headline = ex.get('headline') or ''
    if headline and is_incomplete_heading(headline, kinetic_reveal=ex.get('kineticReveal')):
        issues.append({
            'code': 'incomplete_heading',
            'severity': 'blocking',
            'detail': f'headline={headline!r}',
        })

    card = ex.get('cardText') or ''
    caption = ex.get('caption') or ''
    if card and is_transcript_fragment_card(card, caption or headline):
        issues.append({
            'code': 'fragment_card',
            'severity': 'blocking',
            'detail': f'card={card!r}',
        })

    if is_redundant_stat_pair(headline, card):
        issues.append({
            'code': 'redundant_stat',
            'severity': 'blocking',
            'detail': f'headline={headline!r} card={card!r}',
        })

    # Typography: heading must not be mid-word clipped markers.
    if headline and re.search(r'\w-\s*$', headline):
        issues.append({
            'code': 'heading_midword_break',
            'severity': 'blocking',
            'detail': headline,
        })
    return issues


def repair_scene(scene: dict, issues: list[dict] | None = None) -> tuple[dict, list[str]]:
    """Deterministic repairs. Returns (scene, repair_actions)."""
    out = normalize_execution(scene)
    ex = out['execution']
    typography = dict(out.get('typography') or {})
    speaker = dict(out.get('speaker') or {})
    actions: list[str] = []
    found = issues if issues is not None else validate_scene(out)
    codes = {i['code'] for i in found}

    if 'speaker_too_small' in codes or 'tiny_circle_layout' in codes:
        # Prefer split when media exists; else enlarge PIP; else fullscreen.
        has_media = bool((out.get('background') or {}).get('assetId'))
        if has_media:
            speaker['layout'] = 'speaker_split_right'
            ex['speakerFraming'] = 'split'
            ex['speakerVisibility'] = 'primary'
            actions.append('switch_to_split_screen')
        else:
            speaker['layout'] = 'speaker_fullscreen'
            ex['speakerFraming'] = 'fullscreen'
            ex['speakerVisibility'] = 'primary'
            actions.append('switch_to_fullscreen_speaker')
        pip = dict(DEFAULT_PIP)
        pip['width'] = max(pip['width'], MIN_PIP_WIDTH_PX)
        ex['pip'] = pip
        speaker['pip'] = pip
        actions.append('enforce_min_pip_size')

    if 'incomplete_heading' in codes:
        bad = ex.get('headline') or ''
        # Demote incomplete heading — caption keeps speech; card cleared.
        typography['headline'] = ''
        typography['title'] = ''
        ex['headline'] = ''
        ex['kineticReveal'] = False
        actions.append(f'drop_incomplete_heading:{bad!r}')

    if 'fragment_card' in codes:
        frag = ex.get('cardText') or ''
        # Replace invalid card with caption-only mode.
        typography['card'] = ''
        typography['body'] = ''
        ex['cardText'] = ''
        ex['captionMode'] = 'speech'
        if frag and not (ex.get('caption') or '').strip():
            # Keep as caption only if it looks like a full phrase.
            if not is_incomplete_heading(frag) and len(_words(frag)) >= 5:
                ex['caption'] = frag
                typography['caption'] = frag
                actions.append('fragment_card_to_caption')
            else:
                actions.append('drop_fragment_card')
        else:
            actions.append('drop_fragment_card')

    if 'redundant_stat' in codes:
        # Keep dominant headline; clear duplicate card number.
        typography['card'] = ''
        typography['body'] = ''
        ex['cardText'] = ''
        actions.append('dedupe_stat_keep_headline')

    if 'heading_midword_break' in codes:
        h = re.sub(r'-\s*$', '', ex.get('headline') or '').strip()
        ex['headline'] = h
        typography['headline'] = h
        actions.append('trim_midword_hyphen')

    # Always stamp min PIP on pip framing.
    if ex.get('speakerFraming') == 'pip':
        pip = dict(ex.get('pip') or DEFAULT_PIP)
        if int(pip.get('width') or 0) < MIN_PIP_WIDTH_PX:
            pip.update(DEFAULT_PIP)
            pip['width'] = MIN_PIP_WIDTH_PX
            pip['height'] = int(MIN_PIP_WIDTH_PX * 4 / 3)
            actions.append('bump_pip_width')
        ex['pip'] = pip
        speaker['pip'] = pip

    out['speaker'] = speaker
    out['typography'] = typography
    out['execution'] = ex
    repairs = list(out.get('repairs') or [])
    repairs.extend(actions)
    out['repairs'] = repairs
    return out, actions


def enforce_plan(visual_plan: dict | None, *, max_attempts: int = MAX_REPAIR_ATTEMPTS) -> dict:
    """Normalize + validate + repair every scene. Fail closed on persistent blockers."""
    plan = dict(visual_plan or {})
    scenes_out = []
    report = []
    for raw in plan.get('scenes') or []:
        scene = normalize_execution(raw)
        attempt = 0
        while attempt < max_attempts:
            issues = validate_scene(scene)
            blocking = [i for i in issues if i.get('severity') == 'blocking']
            if not blocking:
                break
            scene, actions = repair_scene(scene, blocking)
            report.append({
                'sceneId': scene.get('sceneId'),
                'attempt': attempt + 1,
                'issues': blocking,
                'actions': actions,
            })
            attempt += 1
        final_issues = validate_scene(scene)
        blocking = [i for i in final_issues if i.get('severity') == 'blocking']
        if blocking:
            scene['executionFailed'] = True
            scene['executionErrors'] = blocking
            # Last resort: force fullscreen speaker, no card.
            scene, actions = repair_scene({
                **scene,
                'speaker': {**(scene.get('speaker') or {}), 'layout': 'speaker_fullscreen'},
                'typography': {
                    **(scene.get('typography') or {}),
                    'headline': '',
                    'card': '',
                    'body': '',
                },
                'execution': {
                    **(scene.get('execution') or {}),
                    'headline': '',
                    'cardText': '',
                    'speakerFraming': 'fullscreen',
                },
            })
            scene['repairs'] = list(scene.get('repairs') or []) + actions + ['fail_closed_fullscreen']
            report.append({
                'sceneId': scene.get('sceneId'),
                'attempt': 'fail_closed',
                'issues': blocking,
                'actions': scene['repairs'],
            })
        scenes_out.append(scene)
    plan['scenes'] = scenes_out
    plan['executionCompliance'] = {
        'version': 'director_execution_v4',
        'minPipWidthPx': MIN_PIP_WIDTH_PX,
        'maxRepairAttempts': max_attempts,
        'repairs': report,
    }
    return plan


def assert_plan_executable(plan: dict) -> None:
    """Raise ValueError if any scene still has blocking errors after enforce."""
    for scene in plan.get('scenes') or []:
        # Re-validate post-enforce; fail_closed should have cleared blockers.
        issues = [i for i in validate_scene(scene) if i.get('severity') == 'blocking']
        if issues and scene.get('executionFailed') and not scene.get('repairs'):
            raise ValueError(f"execution_compliance_failed:{scene.get('sceneId')}:{issues[0]['code']}")


def qa_sample_points(duration_s: float, *, fps: int = 30) -> list[dict]:
    """Entrance / hold / exit samples across the timeline (not only settled frames)."""
    duration_s = max(1.0, float(duration_s))
    points = []
    # Global thirds + local scene heuristics for a single-span preview.
    for label, t in (
        ('open_entrance', 0.4),
        ('open_hold', min(2.0, duration_s * 0.15)),
        ('mid_entrance', duration_s * 0.35),
        ('mid_hold', duration_s * 0.5),
        ('late_hold', duration_s * 0.72),
        ('exit', max(0.0, duration_s - 0.6)),
    ):
        t = max(0.0, min(duration_s - 0.05, t))
        points.append({'label': label, 't': round(t, 3), 'frame': int(round(t * fps))})
    return points
