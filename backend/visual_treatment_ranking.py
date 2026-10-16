"""Rank existing semantic-motion layouts. Does not plan scenes.

Geometry matches motion/src/semantic/layouts.ts and portraitLayouts.ts.
Layouts: editorial_focus, speaker_visual, full_frame, overlay.
Default mode is off.
"""
from __future__ import annotations

import copy
import time
from typing import Any

MODES = ('off', 'shadow', 'apply')
CANVAS = (1080, 1920)
CAPTION_CLEARANCE = 320
PAD = 28
GUTTER = 20
SPLIT_SPEAKER_WIDTH = 500
LABEL_ROW = 440
STEP_MARK = 28
STEP_GAP = 18
ACTIVE_STEP = 120
QUIET_STEP = 72

LAYOUTS = ('editorial_focus', 'speaker_visual', 'full_frame', 'overlay')


def normalize_mode(value: Any) -> str:
    text = str(value or '').strip()
    return text if text in MODES else 'off'


def _overlap(a: dict, b: dict, gap: int = 0) -> bool:
    return (
        a['left'] < b['left'] + b['width'] + gap
        and a['left'] + a['width'] + gap > b['left']
        and a['top'] < b['top'] + b['height'] + gap
        and a['top'] + a['height'] + gap > b['top']
    )


def caption_band() -> dict[str, int]:
    plate = 210
    top = CANVAS[1] - CAPTION_CLEARANCE - plate
    return {'left': 0, 'top': top, 'width': CANVAS[0], 'height': CANVAS[1] - top}


def face_band_rect() -> dict[str, int]:
    top = round(CANVAS[1] * 0.10)
    bottom = round(CANVAS[1] * 0.46)
    return {
        'left': round(CANVAS[0] * 0.18),
        'top': top,
        'width': round(CANVAS[0] * 0.64),
        'height': bottom - top,
    }


def pip_safe_rect() -> dict[str, int]:
    width = 360
    height = 480
    right = 36
    bottom = CAPTION_CLEARANCE + 48
    return {
        'left': CANVAS[0] - right - width,
        'top': CANVAS[1] - bottom - height,
        'width': width,
        'height': height,
    }


def split_speaker_rect(side: str) -> dict[str, int]:
    top = 180 - 40
    bottom_clearance = CAPTION_CLEARANCE + 36
    height = CANVAS[1] - top - bottom_clearance
    left = PAD if side == 'left' else CANVAS[0] - PAD - SPLIT_SPEAKER_WIDTH
    return {'left': left, 'top': top, 'width': SPLIT_SPEAKER_WIDTH, 'height': height}


def editorial_focus_rects() -> tuple[dict[str, int], dict[str, int]]:
    """Graphic above a PIP that stops before the caption band. Mirrors layouts.ts."""
    cap = caption_band()
    gap = 20
    pip_w, pip_h, margin = 360, 640, 64
    speaker = {
        'left': CANVAS[0] - margin - pip_w,
        'top': cap['top'] - gap - pip_h,
        'width': pip_w,
        'height': pip_h,
    }
    top = 128
    graphic = {
        'left': margin,
        'top': top,
        'width': CANVAS[0] - margin * 2,
        'height': speaker['top'] - gap - top,
    }
    return graphic, speaker


def region_for(layout: str, media_side: str = 'left') -> dict[str, int]:
    cap = caption_band()
    if layout == 'editorial_focus':
        return editorial_focus_rects()[0]
    if layout == 'overlay':
        face = face_band_rect()
        top = max(face['top'] + face['height'] + 36, round(CANVAS[1] * 0.55))
        bottom = cap['top'] - 36
        return {'left': 72, 'top': top, 'width': CANVAS[0] - 144, 'height': max(240, bottom - top)}
    if layout == 'full_frame':
        pip = pip_safe_rect()
        left = 64
        right = pip['left'] - 28
        return {
            'left': left,
            'top': 150,
            'width': max(420, right - left),
            'height': max(480, cap['top'] - 170),
        }
    speaker_side = 'right' if media_side == 'left' else 'left'
    speaker = split_speaker_rect(speaker_side)
    if media_side == 'left':
        left = PAD
        width = speaker['left'] - GUTTER - PAD
    else:
        left = speaker['left'] + speaker['width'] + GUTTER
        width = CANVAS[0] - PAD - left
    top = max(140, 160)
    bottom = min(140 + speaker['height'], cap['top'] - 16)
    return {'left': left, 'top': top, 'width': width, 'height': max(320, bottom - top)}


def speaker_rect_for(layout: str, media_side: str = 'left') -> dict[str, int]:
    if layout == 'editorial_focus':
        return editorial_focus_rects()[1]
    if layout == 'overlay':
        return {'left': 0, 'top': 0, 'width': CANVAS[0], 'height': CANVAS[1]}
    if layout == 'full_frame':
        return pip_safe_rect()
    side = 'right' if media_side == 'left' else 'left'
    return split_speaker_rect(side)


def layout_is_safe(layout: str, media_side: str = 'left') -> bool:
    rect = region_for(layout, media_side)
    if _overlap(rect, caption_band()):
        return False
    if rect['left'] < 24 or rect['top'] < 80:
        return False
    if rect['left'] + rect['width'] > CANVAS[0] - 24:
        return False
    if layout == 'overlay' and _overlap(rect, face_band_rect()):
        return False
    if layout == 'full_frame' and _overlap(rect, pip_safe_rect()):
        return False
    # The full-frame PIP sits on the caption band. That layout is not selectable.
    if layout == 'full_frame' and _overlap(speaker_rect_for(layout), caption_band()):
        return False
    if layout == 'speaker_visual' and _overlap(rect, speaker_rect_for(layout, media_side)):
        return False
    if layout == 'editorial_focus':
        speaker_box = speaker_rect_for(layout, media_side)
        if _overlap(rect, speaker_box, 12) or _overlap(speaker_box, caption_band(), 12):
            return False
    speaker = speaker_rect_for(layout, media_side)
    if speaker['width'] < 324 or speaker['height'] < 400:
        return False
    return rect['width'] >= 360 and rect['height'] >= 220


def _steps(payload: dict) -> list[str]:
    labels = []
    for step in payload.get('steps') or []:
        if isinstance(step, str):
            labels.append(step)
        elif isinstance(step, dict) and step.get('label'):
            labels.append(str(step['label']))
    return labels


def _quote(payload: dict) -> str:
    evidence = payload.get('evidence') or {}
    if isinstance(evidence, dict):
        return str(evidence.get('sourceQuote') or evidence.get('sourceText') or '')
    return ''


def readability_need(payload: dict) -> dict[str, int]:
    """Minimum box the existing component paints. Not a quality score."""
    intent = payload.get('visualIntent')
    if intent == 'process_timeline':
        count = max(2, len(_steps(payload)))
        height = ACTIVE_STEP + (count - 1) * QUIET_STEP + (count - 1) * STEP_GAP
        return {'width': STEP_MARK + STEP_GAP + LABEL_ROW, 'height': height, 'reason': 'timeline_label_row'}
    if intent == 'numeric_range':
        # Label 56 + two 160px figures + 18px bar + three 10px gaps. Width is the 480px figure.
        return {'width': 480, 'height': 424, 'reason': 'range_figure'}
    if intent == 'business_comparison':
        return {'width': 420, 'height': 320, 'reason': 'two_comparison_cards'}
    return {'width': 360, 'height': 240, 'reason': 'component_floor'}


def _evidence_ok(payload: dict) -> tuple[bool, str]:
    quote = _quote(payload)
    intent = payload.get('visualIntent')
    if not payload.get('componentId') or not intent:
        return False, 'missing_component'
    if intent == 'process_timeline':
        labels = _steps(payload)
        if len(labels) < 2:
            return False, 'timeline_without_steps'
        missing = [label for label in labels if label not in quote]
        if missing:
            return False, 'step_absent_from_quote'
    if intent == 'business_comparison':
        for side in ('left', 'right'):
            label = str(payload.get(side) or '')
            if len(label) >= 2 and label not in quote:
                return False, 'comparison_side_absent'
    span = payload.get('range') if isinstance(payload.get('range'), dict) else {}
    unit = str(span.get('unit') or span.get('currency') or '')
    if intent == 'numeric_range' and unit and unit not in quote and not payload.get('unitOmitted'):
        return False, 'currency_absent'
    return True, 'source_labels_present'


def _candidate(payload: dict, layout: str, media_side: str = 'left') -> dict:
    rect = region_for(layout, media_side)
    speaker = speaker_rect_for(layout, media_side)
    need = readability_need(payload)
    safe = layout_is_safe(layout, media_side)
    fits = rect['width'] >= need['width'] and rect['height'] >= need['height']
    reasons = []
    rejected = None
    if not safe:
        rejected = 'layout_hits_caption_face_or_speaker'
    elif not fits:
        rejected = 'graphic_box_smaller_than_component'
        reasons.append(
            f"need {need['width']}x{need['height']} ({need['reason']}), region {rect['width']}x{rect['height']}"
        )
    else:
        slack_w = rect['width'] - need['width']
        reasons.append(f"region {rect['width']}x{rect['height']}")
        reasons.append(f"width_slack {slack_w}px")
        reasons.append(f"speaker {speaker['width']}x{speaker['height']}")
        reasons.append('caption_band_clear')
        if layout == 'full_frame':
            reasons.append('speaker_pip_at_floor')
        elif layout == 'overlay':
            reasons.append('speaker_full_frame')
        elif layout == 'editorial_focus':
            reasons.append('graphic_above_caption_clear_pip')
        else:
            reasons.append('speaker_column')
    return {
        'layout': layout,
        'mediaSide': media_side,
        'rect': rect,
        'speaker': speaker,
        'valid': rejected is None,
        'rejected': rejected,
        'reasons': reasons,
        'graphic_area': rect['width'] * rect['height'],
        'speaker_area': speaker['width'] * speaker['height'],
        'width_slack': rect['width'] - need['width'],
    }


def candidates_for(payload: dict) -> list[dict]:
    """One row per layout the renderer implements."""
    ok, why = _evidence_ok(payload)
    rows = []
    for layout in LAYOUTS:
        row = _candidate(payload, layout, 'left')
        if not ok:
            row['valid'] = False
            row['rejected'] = why
        rows.append(row)
    return rows


def rank_treatments(payload: dict) -> dict:
    """Hard-reject invalid layouts. Among the rest, prefer a box at least 65% of the frame wide with real slack."""
    rows = candidates_for(payload)
    valid = [row for row in rows if row['valid']]
    if not valid:
        current = str(payload.get('layout') or 'speaker_visual')
        return {
            'winner': current,
            'changed': False,
            'reason': 'no_valid_alternative_keep_current',
            'candidates': rows,
        }
    # Comfortable slack first. A few pixels of leftover width still clips a 440px label row.
    # A graphic under 65% of the frame stays available, but a wider box that
    # already cleared the caption and the speaker is preferred. Width is not a score.
    pool = sorted(
        valid,
        key=lambda row: (
            row['rect']['width'] / CANVAS[0] >= 0.65,
            row['width_slack'] >= 48,
            row['width_slack'],
        ),
        reverse=True,
    )
    winner = pool[0]
    current = str(payload.get('layout') or 'speaker_visual')
    return {
        'winner': winner['layout'],
        'mediaSide': winner['mediaSide'],
        'changed': winner['layout'] != current,
        'reason': winner['reasons'],
        'candidates': rows,
    }


def rank_plan(plan: dict) -> dict:
    started = time.perf_counter()
    scenes = []
    if isinstance(plan, dict):
        for scene in plan.get('scenes') or []:
            if not isinstance(scene, dict):
                continue
            payload = scene.get('semanticMotionV14')
            if not isinstance(payload, dict) or not payload.get('componentId'):
                scenes.append({'scene_id': scene.get('sceneId'), 'decision': 'NO_CHANGE', 'reason': 'no_semantic_motion'})
                continue
            ranked = rank_treatments(payload)
            scenes.append({
                'scene_id': scene.get('sceneId'),
                'componentId': payload.get('componentId'),
                'current': payload.get('layout') or 'speaker_visual',
                'winner': ranked['winner'],
                'changed': ranked['changed'],
                'reason': ranked['reason'],
                'candidates': ranked['candidates'],
            })
    return {
        'status': 'ok' if isinstance(plan, dict) and isinstance(plan.get('scenes'), list) else 'malformed_plan',
        'scenes': scenes,
        'elapsed_ms': round((time.perf_counter() - started) * 1000, 3),
    }


def apply_ranking(plan: dict, report: dict) -> dict:
    out = copy.deepcopy(plan)
    by_id = {row['scene_id']: row for row in report.get('scenes') or []}
    applied = []
    for scene in out.get('scenes') or []:
        if not isinstance(scene, dict):
            continue
        row = by_id.get(scene.get('sceneId'))
        payload = scene.get('semanticMotionV14')
        if not row or not isinstance(payload, dict) or not row.get('changed'):
            continue
        winner = next((item for item in row['candidates'] if item['layout'] == row['winner'] and item['valid']), None)
        if winner is None:
            continue
        before = {
            'layout': payload.get('layout'),
            'mediaSide': payload.get('mediaSide'),
            'lifecycle': copy.deepcopy(payload.get('lifecycle')),
            'evidence': copy.deepcopy(payload.get('evidence')),
            'steps': copy.deepcopy(payload.get('steps')),
        }
        payload['layout'] = winner['layout']
        payload['mediaSide'] = winner['mediaSide']
        payload['treatmentRank'] = {
            'layout': winner['layout'],
            'reason': winner['reasons'],
            'previous': before['layout'],
        }
        if payload.get('lifecycle') != before['lifecycle'] or payload.get('evidence') != before['evidence'] or payload.get('steps') != before['steps']:
            payload['layout'] = before['layout']
            payload['mediaSide'] = before['mediaSide']
            payload.pop('treatmentRank', None)
            continue
        applied.append({'scene_id': scene.get('sceneId'), 'from': before['layout'], 'to': winner['layout']})
    out['treatmentRankingApplied'] = applied
    out['treatmentRanking'] = report
    out['visualTreatmentMode'] = 'apply'
    return out


def apply(plan: dict | None, *, mode: Any = None) -> dict | None:
    chosen = normalize_mode(mode)
    if chosen == 'off' or not isinstance(plan, dict):
        return plan
    try:
        report = rank_plan(plan)
    except Exception as exc:
        out = dict(plan)
        out['visualTreatmentMode'] = chosen
        out['visualTreatmentError'] = type(exc).__name__
        return out
    if chosen == 'shadow':
        return {**plan, 'visualTreatmentMode': 'shadow', 'treatmentRanking': report}
    if report.get('status') != 'ok':
        return {**plan, 'visualTreatmentMode': 'apply', 'treatmentRanking': report}
    return apply_ranking(plan, report)
