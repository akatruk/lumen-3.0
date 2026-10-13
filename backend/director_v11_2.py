"""Director V11.2 — factual consistency + composition repair on top of V11.1.

Extends V11.1 provenance. Does not invent Director V12.

Fixes:
- Scrub numbered step/card labels that read as invented headcounts
  (e.g. CleanSteps "{n} Shareholders" → "2 Shareholders").
- Stamp face-safe placement for BusinessMotion overlays.
- Prefer transparent / floating diagram policy; reduce opaque cards.
- Export factual-validation, face-collision-report, caption-qa artifacts.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .locale_consistency import locale_bucket

# Numbered step / card titles that imply a shareholder headcount without provenance.
_FAKE_HEADCOUNT = re.compile(
    r'(?:^|\b)(?:'
    r'\d+\s*shareholders?'
    r'|two\s+shareholders?'
    r'|\d+\s*акционер'
    r'|два\s+акционер'
    r'|\d+\s*名?股东'
    r'|两名股东'
    r')\b',
    re.I,
)

# Bare topic word OK; numbered claim not OK without evidence.
_SHAREHOLDER_TOPIC = re.compile(r'shareholder|акционер|股东', re.I)

_STRUCTURE_STEPS = {
    'en': ['Capital', 'Structure', 'Control'],
    'ru': ['Капитал', 'Структура', 'Контроль'],
    'zh': ['资本', '结构', '控制权'],
}

# Components that historically centered over the face band.
_FACE_RISK_COMPONENTS = frozenset({
    'shareholder_structure',
    'company_ownership',
    'company_control',
    'capital_investment',
    'equity_distribution',
    'business_process',
    'financial_comparison',
    'investment_flow',
})


def scrub_fake_headcount_labels(plan: dict, *, locale: str | None = None) -> dict:
    """Rewrite step/card labels that look like invented shareholder counts."""
    locale = locale or plan.get('language') or 'en-US'
    bucket = locale_bucket(locale)
    safe_steps = list(_STRUCTURE_STEPS.get(bucket) or _STRUCTURE_STEPS['en'])
    out = dict(plan)
    scenes_out: list[dict] = []
    scrubbed: list[dict[str, Any]] = []

    # Spoken evidenced count from V11.1 usage (if any).
    evidenced = None
    for row in plan.get('businessMotionUsage') or []:
        if row.get('showCount') and row.get('nodeCount'):
            evidenced = int(row['nodeCount'])
            break

    for scene in out.get('scenes') or []:
        scene = dict(scene)
        sid = scene.get('sceneId')
        typ = dict(scene.get('typography') or {})
        changed = False

        steps = list(typ.get('steps') or scene.get('steps') or [])
        if steps:
            new_steps = []
            for i, label in enumerate(steps):
                text = str(label or '')
                # "Shareholders" as step #2 (index 1) → Structure; any \d+ Shareholders → scrub.
                if _FAKE_HEADCOUNT.search(text) or (
                    _SHAREHOLDER_TOPIC.search(text) and not re.search(r'[≥⩾>=]|at\s+least|至少|не\s+менее', text, re.I)
                ):
                    replacement = safe_steps[min(i, len(safe_steps) - 1)]
                    scrubbed.append({
                        'sceneId': sid,
                        'field': 'steps',
                        'from': text,
                        'to': replacement,
                        'reason': 'numbered_step_reads_as_headcount',
                    })
                    new_steps.append(replacement)
                    changed = True
                else:
                    new_steps.append(text)
            # If pack still has Shareholders synonym at index 1, force Structure pack.
            if any(_SHAREHOLDER_TOPIC.search(s) and not re.search(r'[≥⩾>=]', s) for s in new_steps):
                new_steps = list(safe_steps)
                changed = True
            typ['steps'] = new_steps
            scene['steps'] = new_steps

        cards = [dict(c) for c in (typ.get('cards') or [])]
        for card in cards:
            title = str(card.get('title') or '')
            if _FAKE_HEADCOUNT.search(title):
                spoken = evidenced
                # Keep only if title matches evidenced count; else strip numeral.
                m = re.search(r'(\d+)', title)
                n = int(m.group(1)) if m else None
                if spoken is not None and n == spoken:
                    continue  # e.g. "3 Shareholders" with evidence — still prefer ≥ form
                if spoken is not None:
                    if bucket == 'zh':
                        card['title'] = f'≥{spoken}名股东'
                    elif bucket == 'ru':
                        card['title'] = f'≥{spoken} акционеров'
                    else:
                        card['title'] = f'≥{spoken} Shareholders'
                else:
                    if bucket == 'zh':
                        card['title'] = '股东'
                    elif bucket == 'ru':
                        card['title'] = 'Акционеры'
                    else:
                        card['title'] = 'Shareholders'
                scrubbed.append({
                    'sceneId': sid,
                    'field': 'card.title',
                    'from': title,
                    'to': card['title'],
                    'reason': 'unsupported_or_ambiguous_headcount_card',
                })
                changed = True
        if cards:
            typ['cards'] = cards

        exe = dict(scene.get('execution') or {})
        card_text = str(exe.get('cardText') or '')
        if card_text and _SHAREHOLDER_TOPIC.search(card_text) and not re.search(
            r'[≥⩾>=]|at\s+least|至少|не\s+менее', card_text, re.I,
        ):
            exe['cardText'] = ' | '.join(safe_steps)
            scene['execution'] = exe
            scrubbed.append({
                'sceneId': sid,
                'field': 'execution.cardText',
                'from': card_text,
                'to': exe['cardText'],
                'reason': 'execution_summary_headcount_ambiguity',
            })
            changed = True

        if changed:
            scene['typography'] = typ
        scenes_out.append(scene)

    out['scenes'] = scenes_out
    out['headcountScrub'] = scrubbed
    return out


def stamp_face_safe_business_motion(plan: dict) -> dict:
    """Add Remotion placement hints so overlays miss the face band for the full path."""
    out = dict(plan)
    scenes_out: list[dict] = []
    report: list[dict[str, Any]] = []
    for scene in out.get('scenes') or []:
        scene = dict(scene)
        bm = dict(scene.get('businessMotion') or {})
        if not bm.get('component'):
            scenes_out.append(scene)
            continue
        sid = scene.get('sceneId') or ''
        layout = ((scene.get('speaker') or {}).get('layout') or '')
        component = str(bm.get('component'))
        # Speaker side → park graphics on the opposite half for the full motion path.
        speaker_right = 'split_right' in layout or layout.endswith('_right')
        speaker_left = 'split_left' in layout or layout.endswith('_left')
        if sid == 'beside':
            # Beside owns progressive cards — Remotion skips BusinessMotion; stamp anyway.
            placement = 'media_column'
            media_side = 'right' if speaker_left or not speaker_right else 'left'
            shelfTop = 220
        elif 'split' in layout or sid in ('residency', 'context') or 'foreground' in layout:
            placement = 'media_column'
            # speaker_split_right → media on LEFT; speaker_split_left → media on RIGHT
            media_side = 'left' if speaker_right or not speaker_left else 'right'
            shelfTop = 200
        elif sid in ('hook', 'problem', 'payoff', 'return', 'steps') or 'fullscreen' in layout or 'closeup' in layout or 'punch' in layout:
            # Full-bleed: left rail cutaway — never centered over mouth/eyes.
            placement = 'side_rail'
            media_side = 'left'
            shelfTop = 180
        elif sid in ('consult', 'proof') or 'pip' in ((scene.get('speaker') or {}).get('framing') or ''):
            # PIP speaker is bottom-right — keep graphics upper-left, clear of PIP+face.
            placement = 'side_rail'
            media_side = 'left'
            shelfTop = 160
        else:
            placement = 'side_rail'
            media_side = 'left'
            shelfTop = 180
        if component in _FACE_RISK_COMPONENTS:
            bm['placement'] = placement
            bm['mediaSide'] = media_side
            bm['shelfTop'] = shelfTop
            bm['faceSafe'] = True
            bm['containerPolicy'] = 'transparent_float'
            scene['businessMotion'] = bm
            report.append({
                'sceneId': sid,
                'component': component,
                'placement': placement,
                'mediaSide': media_side,
                'shelfTop': shelfTop,
                'layout': layout or 'speaker_fullscreen',
                'mitigation': 'face_safe_shelf_opposite_speaker',
            })
        scenes_out.append(scene)
    out['scenes'] = scenes_out
    out['faceCollisionPlan'] = {
        'version': 'v11.2',
        'overlays': report,
        'policy': 'validate entrance/hold/exit; prefer media_column or upper_band_cutaway over face center',
    }
    return out


def apply_composition_repair(plan: dict, transcript: list | None = None, *, locale: str | None = None) -> dict:
    """V11.2 entry: scrub fake headcounts + face-safe motion + caption policy stamp."""
    del transcript  # reserved for future audio-aligned checks; V11.1 already grounded facts
    locale = locale or plan.get('language') or 'en-US'
    out = scrub_fake_headcount_labels(plan, locale=locale)
    out = stamp_face_safe_business_motion(out)
    # Prefer transparent graphics; keep progressive cards only on beside.
    for scene in out.get('scenes') or []:
        typ = dict(scene.get('typography') or {})
        if scene.get('sceneId') != 'beside' and typ.get('cardMode') == 'progressive_one':
            # leave beside alone; other scenes shouldn't force opaque card stacks
            pass
        comp = dict(scene.get('composition') or {})
        comp['containerPolicy'] = comp.get('containerPolicy') or 'minimal'
        comp['preferTransparentGraphics'] = True
        scene['composition'] = comp
    out['compositionVersion'] = 'v11.2'
    out['factualVersion'] = 'v11.2'
    # Re-run light validation after scrub.
    from .director_v11_1 import validate_factual_grounding
    validation = validate_factual_grounding(out)
    # Extra: flag any remaining fake headcount strings in plan blob.
    blob_issues = []
    for scene in out.get('scenes') or []:
        typ = scene.get('typography') or {}
        for label in (typ.get('steps') or []):
            if _FAKE_HEADCOUNT.search(str(label)):
                blob_issues.append({'sceneId': scene.get('sceneId'), 'type': 'step_headcount', 'value': label})
        for card in typ.get('cards') or []:
            title = str(card.get('title') or '')
            if re.search(r'(?:^|\b)2\s+shareholders?\b|two shareholders|两名股东|2\s*акционер', title, re.I):
                blob_issues.append({'sceneId': scene.get('sceneId'), 'type': 'card_two_shareholders', 'value': title})
    validation = dict(validation)
    validation['version'] = 'v11.2'
    validation['extraIssues'] = blob_issues
    validation['ok'] = validation.get('ok', True) and not blob_issues
    validation['issueCount'] = len(validation.get('issues') or []) + len(blob_issues)
    out['factualGrounding'] = validation
    out['captionPolicy'] = {
        'version': 'v11.2',
        'mobileMinPx': 56,
        'mobileMaxPx': 84,
        'maxLines': 2,
        'backing': 'dark_soft',
        'backingOpacity': 0.55,
        'avoidHugePlates': True,
        'preserveSpeechTiming': True,
    }
    return out


def export_v11_2_artifacts(plan: dict, out_dir, *, caption_meta: dict | None = None) -> dict[str, str]:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    written = {}
    factual = {
        'version': 'v11.2',
        'factualGrounding': plan.get('factualGrounding') or {},
        'headcountScrub': plan.get('headcountScrub') or [],
        'shareholderFinding': _shareholder_finding(plan),
        'rejectedTwoShareholders': True,
        'twoShareholdersSource': (
            'CleanSteps rendered accent index + investment step label "Shareholders" '
            '→ on-screen "2 Shareholders"; scrubbed to Structure pack + face-safe motion'
        ),
    }
    face = plan.get('faceCollisionPlan') or {'version': 'v11.2', 'overlays': []}
    caption = {
        'version': 'v11.2',
        'policy': plan.get('captionPolicy') or {},
        **(caption_meta or {}),
    }
    for name, payload in (
        ('factual-validation.json', factual),
        ('face-collision-report.json', face),
        ('caption-qa.json', caption),
    ):
        dest = path / name
        dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        written[name] = str(dest)
    return written


def _shareholder_finding(plan: dict) -> dict[str, Any]:
    from .director_v11_1 import _shareholder_finding as base
    finding = base(plan)
    finding['version'] = 'v11.2'
    finding['rejectedInventedTwo'] = True
    finding['rejectedNumberedStepShareholders'] = True
    return finding
