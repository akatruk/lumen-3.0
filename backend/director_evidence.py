"""Keep viewer-facing labels and plates inside the scene that says them.

A domain tag (immigration, investment) is not evidence for a card.
A concept from a later sentence is not a query for the opening.
"""
from __future__ import annotations

from typing import Any

from .director_media_rules import same_media_source

_PAD = 1.5


def scene_windows(plan: dict, transcript: list | None = None) -> list[tuple[float, float]]:
    from .director_v14 import _windows
    return _windows(plan, list(transcript or []))


def _rows(transcript: list | None) -> list[dict]:
    rows = []
    for row in transcript or []:
        if hasattr(row, 'model_dump'):
            row = row.model_dump()
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _text(row: dict) -> str:
    return str(row.get('original') or row.get('text') or row.get('zh') or row.get('en') or '').strip()


def _overlaps(start: float, end: float, win: tuple[float, float], pad: float) -> bool:
    return end >= win[0] - pad and start <= win[1] + pad


def rows_in_window(rows: list[dict], win: tuple[float, float], pad: float = 0.4) -> list[dict]:
    kept = []
    for row in rows:
        try:
            start = float(row.get('start') or 0)
            end = float(row.get('end') or start)
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        words = [
            token for token in (row.get("words") or [])
            if isinstance(token, dict)
            and _overlaps(float(token.get("start") or 0), float(token.get("end") or 0), win, pad)
        ]
        if words:
            kept.append({
                **row,
                "text": "".join(str(token.get("text") or "") for token in words),
                "start": float(words[0].get("start") or start),
                "end": float(words[-1].get("end") or end),
                "words": words,
            })
            continue
        if _overlaps(start, end, win, pad):
            kept.append(row)
    return kept


def _local_text(rows: list[dict]) -> str:
    return ' '.join(_text(row) for row in rows if _text(row))


def _claim_in_text(claim: str, text: str) -> bool:
    claim = (claim or '').strip()
    if not claim or not text:
        return False
    return claim in text


def _clear_plate(scene: dict) -> dict:
    scene = dict(scene)
    bg = dict(scene.get('background') or {})
    for key in ('assetId', 'file', 'staged', 'conceptId'):
        bg.pop(key, None)
    scene['background'] = bg
    return scene


def _merge_ordinal_list(plan: dict, rows: list[dict], locale: str | None) -> dict:
    """One process timeline for a complete 第N层 cluster.

    Rows stay hidden until the line that names them, and stop being the
    current thought when that line ends. Scenes that overlap the cluster
    become one scene so the list does not reset or keep the last label active.
    """
    from .director_v14 import ordinal_timeline_payloads

    events = ordinal_timeline_payloads(rows, locale=locale or plan.get('language') or 'zh-CN')
    if not events:
        return plan
    scenes = [dict(scene) for scene in plan.get('scenes') or []]
    weights = list(plan.get('beatWeights') or [])
    if len(weights) != len(scenes):
        weights = [1] * len(scenes)
    windows = scene_windows(plan, rows)
    for _cluster, payload in reversed(events):
        stamp = (payload.get('evidence') or {}).get('sourceTimestamp') or [0, 0]
        try:
            start, end = float(stamp[0]), float(stamp[1])
        except (TypeError, ValueError):
            continue
        indexes = [
            index for index, win in enumerate(windows)
            if win[1] > start and win[0] < end
        ]
        if not indexes:
            continue
        first, last = indexes[0], indexes[-1]
        scene = _clear_plate(dict(scenes[first]))
        typ = dict(scene.get('typography') or {})
        typ['steps'] = []
        typ['stepsTitle'] = ''
        typ['cards'] = []
        typ['cardMode'] = 'none'
        scene['typography'] = typ
        scene['steps'] = []
        scene['stepsTitle'] = ''
        scene['criteriaCards'] = []
        scene['cardMode'] = 'none'
        mounted = dict(payload)
        mounted['layout'] = 'speaker_visual'
        mounted['mediaSide'] = 'left'
        mounted['sceneTheme'] = 'ink'
        mounted['connectorBackground'] = '#12110F'
        mounted['enterFrame'] = 0
        mounted['outputTime'] = [round(windows[first][0], 3), round(windows[last][1], 3)]
        mounted['timebase'] = {
            'sourceOrigin': start,
            'sceneStart': round(windows[first][0], 3),
            'stepClock': 'sourceOrigin_plus_step_at',
        }
        scene['semanticMotionV14'] = mounted
        scene['spokenStructure'] = {
            'kind': 'process_timeline',
            'evidence': mounted.get('evidence'),
        }
        scene['speaker'] = {
            'layout': 'speaker_split_right',
            'framing': 'split',
            'visibility': 'primary',
        }
        weight = sum(weights[first:last + 1]) or 1
        scenes = scenes[:first] + [scene] + scenes[last + 1:]
        weights = weights[:first] + [weight] + weights[last + 1:]
        plan = dict(plan)
        plan['scenes'] = scenes
        plan['beatWeights'] = weights
        windows = scene_windows(plan, rows)
    out = dict(plan)
    out['scenes'] = scenes
    out['beatWeights'] = weights
    return out


def _stamp_spoken(plan: dict, rows: list[dict], locale: str | None) -> dict:
    """Put 不是/而是 and 第N层 labels on the scene that speaks them."""
    from .director_v14 import adjacent_contrasts, contrast_sides, ordinal_timeline_payloads

    locale = locale or plan.get('language') or 'zh-CN'
    windows = scene_windows(plan, rows)
    scenes = [dict(scene) for scene in (plan.get('scenes') or [])]
    if len(windows) != len(scenes):
        return plan

    def _scene_index(start: float, end: float) -> int | None:
        mid = (start + end) / 2
        for index, win in enumerate(windows):
            if win[0] <= mid < win[1] or (index == len(windows) - 1 and win[0] <= mid <= win[1]):
                return index
        return None

    comparisons = list(adjacent_contrasts(rows, locale=locale))
    for row in rows:
        text = _text(row)
        sides = contrast_sides(text)
        if not sides:
            continue
        try:
            start = float(row.get('start') or 0)
            end = float(row.get('end') or start)
        except (TypeError, ValueError):
            continue
        comparisons.append({
            'left': sides[0],
            'right': sides[1],
            'evidence': {
                'segmentId': row.get('id'),
                'segmentIds': [row.get('id')],
                'sourceTimestamp': [start, end],
                'sourceQuote': text,
            },
        })

    for event in comparisons:
        evidence = event.get('evidence') or {}
        stamp = evidence.get('sourceTimestamp') or [None, None]
        try:
            start, end = float(stamp[0]), float(stamp[1])
        except (TypeError, ValueError, IndexError):
            continue
        index = _scene_index(start, end)
        if index is None:
            continue
        left = event.get('left')
        right = event.get('right')
        if not left or not right:
            continue
        scene = scenes[index]
        local = _local_text(rows_in_window(rows, windows[index], 0.4))
        if left not in local or right not in local:
            continue
        cards = [
            {
                'title': left,
                'explanation': '',
                'evidence': {
                    'segmentId': (evidence.get('segmentIds') or [None])[0],
                    'sourceTimestamp': [start, end],
                    'sourceText': evidence.get('sourceQuote') or local,
                    'semanticConcept': 'contrast',
                    'selectionReason': '不是/而是 sides are in this scene',
                },
            },
            {
                'title': right,
                'explanation': '',
                'evidence': {
                    'segmentId': (evidence.get('segmentIds') or [None])[-1],
                    'sourceTimestamp': [start, end],
                    'sourceText': evidence.get('sourceQuote') or local,
                    'semanticConcept': 'contrast',
                    'selectionReason': '不是/而是 sides are in this scene',
                },
            },
        ]
        typ = dict(scene.get('typography') or {})
        typ['cards'] = cards
        typ['cardMode'] = 'progressive_one'
        scene['typography'] = typ
        scene['criteriaCards'] = cards
        scene['cardMode'] = 'progressive_one'
        exe = dict(scene.get('execution') or {})
        exe['headline'] = ''
        exe['cardText'] = f'{left} | {right}'
        scene['execution'] = exe
        scenes[index] = scene

    out = dict(plan)
    out['scenes'] = scenes
    return _merge_ordinal_list(out, rows, locale)


def _drop_unsupported_claims(plan: dict, rows: list[dict], windows: list[tuple[float, float]] | None = None) -> dict:
    if windows is None:
        windows = scene_windows(plan, rows)
    scenes = []
    for index, scene in enumerate(plan.get('scenes') or []):
        scene = dict(scene)
        win = windows[index] if index < len(windows) else None
        local = _local_text(rows_in_window(rows, win, 0.4)) if win else ''
        typ = dict(scene.get('typography') or {})
        cards = list(scene.get('criteriaCards') or typ.get('cards') or [])
        kept = []
        for card in cards:
            if not isinstance(card, dict):
                continue
            title = str(card.get('title') or '')
            explanation = str(card.get('explanation') or '')
            if not _claim_in_text(title, local):
                continue
            if explanation and not _claim_in_text(explanation, local):
                card = dict(card)
                card['explanation'] = ''
            kept.append(card)
        typ['cards'] = kept
        if not kept:
            typ['cardMode'] = 'none'
            scene['cardMode'] = 'none'
        scene['criteriaCards'] = kept
        steps = list(scene.get('steps') or typ.get('steps') or [])
        step_labels = []
        for step in steps:
            label = step.get('label') if isinstance(step, dict) else str(step)
            if _claim_in_text(str(label), local):
                step_labels.append(str(label))
        typ['steps'] = step_labels
        scene['steps'] = step_labels
        title = str(scene.get('stepsTitle') or typ.get('stepsTitle') or '')
        if title and not _claim_in_text(title, local):
            title = ''
        evidenced = bool((scene.get('spokenStructure') or {}).get('evidence'))
        if len(step_labels) < 2 and not evidenced:
            step_labels = []
            typ['steps'] = []
            scene['steps'] = []
            title = ''
        typ['stepsTitle'] = title
        scene['stepsTitle'] = title
        scene['typography'] = typ
        exe = dict(scene.get('execution') or {})
        for key in ('headline', 'cardText'):
            value = str(exe.get(key) or scene.get(key) or '')
            if value and not _claim_in_text(value, local) and value not in (
                ' | '.join(c.get('title', '') for c in kept),
                ' → '.join(step_labels),
            ):
                exe[key] = ''
                scene[key] = None
        scene['execution'] = exe
        scenes.append(scene)
    out = dict(plan)
    out['scenes'] = scenes
    return out


def drop_repeated_assets(plan: dict) -> dict:
    """One plate identity per plan. A later copy becomes no plate."""
    seen: list[str] = []
    scenes = []
    for scene in plan.get('scenes') or []:
        scene = dict(scene)
        bg = dict(scene.get('background') or {})
        asset_id = bg.get('assetId')
        if asset_id and any(same_media_source(asset_id, prev) or asset_id == prev for prev in seen):
            scene = _clear_plate(scene)
            rejected = list(scene.get('rejected') or [])
            if 'repeated_asset' not in rejected:
                rejected.append('repeated_asset')
            scene['rejected'] = rejected
            scene['mediaGap'] = scene.get('mediaGap') or 'repeated_asset'
        elif asset_id:
            seen.append(str(asset_id))
        scenes.append(scene)
    out = dict(plan)
    out['scenes'] = scenes
    return out


def apply_claim_check(plan: dict, transcript: list | None = None) -> dict:
    """Drop labels the scene interval does not speak. Do not invent a new layout."""
    rows = _rows(transcript if transcript is not None else plan.get('transcript'))
    windows = [
        (float(scene.get('start') or 0), float(scene.get('end') or scene.get('start') or 0))
        for scene in plan.get('scenes') or []
    ]
    return drop_repeated_assets(_drop_unsupported_claims(plan, rows, windows))


def apply_evidence_gate(plan: dict, transcript: list | None = None, *, locale: str | None = None) -> dict:
    rows = _rows(transcript if transcript is not None else plan.get('transcript'))
    plan = _stamp_spoken(plan, rows, locale or plan.get('language'))
    plan = _drop_unsupported_claims(plan, rows)
    plan = drop_repeated_assets(plan)
    return plan
