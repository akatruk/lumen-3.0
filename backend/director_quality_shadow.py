"""Read-only findings on a Director plan. Does not change the plan."""
from __future__ import annotations

from typing import Any

from .director_evidence import rows_in_window, scene_windows


def _text(row: dict) -> str:
    return str(row.get('original') or row.get('text') or row.get('zh') or '').strip()


def diagnose(plan: dict, transcript: list | None = None) -> dict[str, Any]:
    rows = []
    for row in transcript or plan.get('transcript') or []:
        if hasattr(row, 'model_dump'):
            row = row.model_dump()
        if isinstance(row, dict):
            rows.append(row)
    windows = scene_windows(plan, rows)
    findings: list[dict[str, Any]] = []
    seen: list[str] = []
    for index, scene in enumerate(plan.get('scenes') or []):
        win = windows[index] if index < len(windows) else (0.0, 0.0)
        local_rows = rows_in_window(rows, win, 0.4)
        local = ' '.join(_text(row) for row in local_rows)
        sid = scene.get('sceneId')
        cards = (scene.get('criteriaCards') or (scene.get('typography') or {}).get('cards') or [])
        for card in cards:
            title = str((card or {}).get('title') or '')
            explanation = str((card or {}).get('explanation') or '')
            if title and title not in local:
                findings.append({
                    'code': 'unsupported_card',
                    'sceneId': sid,
                    'timestamp': list(win),
                    'evidence': title,
                    'rootCause': 'card title is not in the scene quote',
                    'suggestion': 'omit',
                })
            elif explanation and explanation not in local:
                findings.append({
                    'code': 'unsupported_card',
                    'sceneId': sid,
                    'timestamp': list(win),
                    'evidence': explanation,
                    'rootCause': 'card explanation is not in the scene quote',
                    'suggestion': 'omit',
                })
        for concept in scene.get('semanticConcepts') or []:
            try:
                start = float(concept.get('start'))
                end = float(concept.get('end'))
            except (TypeError, ValueError):
                findings.append({
                    'code': 'cross_scene_concept',
                    'sceneId': sid,
                    'timestamp': list(win),
                    'evidence': concept.get('conceptId'),
                    'rootCause': 'concept has no source time',
                    'suggestion': 'NO_CHANGE',
                })
                continue
            if end < win[0] - 1.5 or start > win[1] + 1.5:
                findings.append({
                    'code': 'cross_scene_concept',
                    'sceneId': sid,
                    'timestamp': list(win),
                    'evidence': concept.get('evidence') or concept.get('conceptId'),
                    'rootCause': 'concept time is outside this scene',
                    'suggestion': 'drop the concept from this scene',
                })
        asset = (scene.get('background') or {}).get('assetId')
        if asset and asset in seen:
            findings.append({
                'code': 'repeated_asset',
                'sceneId': sid,
                'timestamp': list(win),
                'evidence': asset,
                'rootCause': 'the same asset id was already selected',
                'suggestion': 'speaker-only when no other approved plate fits this quote',
            })
        elif asset:
            seen.append(asset)
        steps = scene.get('steps') or (scene.get('typography') or {}).get('steps') or []
        if steps and not any(str(step) in local for step in steps):
            findings.append({
                'code': 'unnecessary_text_only_scene',
                'sceneId': sid,
                'timestamp': list(win),
                'evidence': steps,
                'rootCause': 'step labels are absent from this scene',
                'suggestion': 'omit',
            })
        motion = scene.get('semanticMotionV14') or {}
        if motion.get('componentId') and not (motion.get('evidence') or {}).get('sourceQuote'):
            findings.append({
                'code': 'missing_component_parameters',
                'sceneId': sid,
                'timestamp': list(win),
                'evidence': motion.get('componentId'),
                'rootCause': 'component has no source quote',
                'suggestion': 'NO_CHANGE',
            })
    if not findings:
        findings.append({
            'code': 'NO_CHANGE',
            'sceneId': None,
            'timestamp': None,
            'evidence': None,
            'rootCause': None,
            'suggestion': 'NO_CHANGE',
        })
    return {'findings': findings, 'altersPlan': False}
