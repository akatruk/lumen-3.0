"""Visual quality optimizer.

Reads a finished Director plan and writes evidence-backed findings.
Default mode is off, so an existing job is unchanged. Shadow mode attaches
a report and does not edit scenes. apply_safe may drop an unsupported
optional graphic, shorten a stale display, or swap a repeated plate only
when an approved relevant alternative is already in the finding.

pgvector retrieval is advisory. Cosine similarity is not a quality score.
Source text is the fact source. This module does not plan scenes and does
not call an embedding model.
"""
from __future__ import annotations

import copy
import time
from typing import Any

from .director_v14 import timeline_order_verified

FINDING_TYPES = (
    'UNSUPPORTED_VISIBLE_CLAIM',
    'CROSS_SCENE_SEMANTIC_LEAK',
    'REPEATED_BROLL',
    'WEAK_MEDIA_RELEVANCE',
    'UNJUSTIFIED_PROCESS_TIMELINE',
    'UNNECESSARY_TEXT_CARD',
    'STALE_SEMANTIC_GRAPHIC',
    'COMPONENT_PARAMETER_INVALID',
    'LAYOUT_REPETITION',
    'NO_SAFE_ALTERNATIVE',
)
MODES = ('off', 'shadow', 'apply_safe')
VECTOR_DIM = 512
_HOLD_SLACK = 1.5
_SAFE_ACTIONS = {
    'UNJUSTIFIED_PROCESS_TIMELINE': 'SAFE_FALLBACK',
    'UNSUPPORTED_VISIBLE_CLAIM': 'SAFE_FALLBACK',
    'COMPONENT_PARAMETER_INVALID': 'SAFE_FALLBACK',
    'STALE_SEMANTIC_GRAPHIC': 'SHORTEN_DISPLAY',
    'UNNECESSARY_TEXT_CARD': 'DROP_CARD',
    'REPEATED_BROLL': 'HOLD',
    'WEAK_MEDIA_RELEVANCE': 'HOLD',
    'CROSS_SCENE_SEMANTIC_LEAK': 'SAFE_FALLBACK',
    'LAYOUT_REPETITION': 'NO_CHANGE',
    'NO_SAFE_ALTERNATIVE': 'NO_CHANGE',
}
_DROP_MOTION = {
    'UNJUSTIFIED_PROCESS_TIMELINE',
    'UNSUPPORTED_VISIBLE_CLAIM',
    'COMPONENT_PARAMETER_INVALID',
    'CROSS_SCENE_SEMANTIC_LEAK',
}


def normalize_mode(value: Any) -> str:
    text = str(value or '').strip()
    if text in MODES:
        return text
    return 'off'


def _tokens(text: str) -> set[str]:
    parts = []
    buf = []
    for ch in text or '':
        if '\u4e00' <= ch <= '\u9fff':
            if buf:
                parts.append(''.join(buf))
                buf = []
            parts.append(ch)
            continue
        if ch.isalnum():
            buf.append(ch.lower())
        elif buf:
            parts.append(''.join(buf))
            buf = []
    if buf:
        parts.append(''.join(buf))
    cjk = ''.join(part for part in parts if len(part) == 1 and '\u4e00' <= part <= '\u9fff')
    grams = {cjk[i:i + 2] for i in range(len(cjk) - 1)} if len(cjk) >= 2 else set()
    words = {part for part in parts if len(part) > 1 and not ('\u4e00' <= part <= '\u9fff')}
    return grams | words


def _quote(payload: dict) -> str:
    evidence = payload.get('evidence') or {}
    if isinstance(evidence, dict):
        return str(evidence.get('sourceQuote') or evidence.get('sourceText') or '')
    return ''


def _segments(payload: dict) -> list[str]:
    life = payload.get('lifecycle') or {}
    ids = [str(item) for item in (life.get('source_segment_ids') or []) if item]
    evidence = payload.get('evidence') or {}
    if isinstance(evidence, dict) and evidence.get('segmentId') and evidence['segmentId'] not in ids:
        ids.append(str(evidence['segmentId']))
    return ids


def _interval(payload: dict) -> list[float] | None:
    life = payload.get('lifecycle') or {}
    if life.get('evidence_start') is not None and life.get('evidence_end') is not None:
        return [float(life['evidence_start']), float(life['evidence_end'])]
    evidence = payload.get('evidence') or {}
    stamp = evidence.get('sourceTimestamp') if isinstance(evidence, dict) else None
    if isinstance(stamp, (list, tuple)) and len(stamp) == 2:
        return [float(stamp[0]), float(stamp[1])]
    return None


def _asset_id(scene: dict) -> str | None:
    """Library plate only. Icon SVGs are not B-roll."""
    foreground = scene.get('foreground') if isinstance(scene.get('foreground'), dict) else {}
    file = str((foreground or {}).get('file') or '')
    icon = file.endswith('.svg') or 'static/icons/' in file
    if (foreground or {}).get('assetId') and not icon:
        return str(foreground['assetId'])
    background = scene.get('background') if isinstance(scene.get('background'), dict) else {}
    if background.get('assetId'):
        return str(background['assetId'])
    media = scene.get('media') if isinstance(scene.get('media'), dict) else {}
    if media.get('assetId'):
        return str(media['assetId'])
    return None


def _finding(
    scene: dict,
    payload: dict,
    finding_type: str,
    *,
    evidence: dict,
    current: dict,
    suggested: str,
    severity: str,
    status: str = 'open',
) -> dict:
    scene_id = str(scene.get('sceneId') or '')
    return {
        'finding_id': f'{scene_id}:{finding_type}',
        'scene_id': scene_id,
        'source_segment_ids': _segments(payload) if payload else [],
        'source_interval': _interval(payload) if payload else None,
        'finding_type': finding_type,
        'evidence': evidence,
        'current_decision': current,
        'suggested_action': suggested,
        'severity': severity,
        'evaluation_status': status,
    }


def _label_missing(label: str, quote: str) -> bool:
    text = str(label or '').strip()
    if len(text) < 2:
        return False
    return text not in (quote or '')


def _motion_findings(scene: dict, payload: dict, other_quotes: list[str]) -> list[dict]:
    findings = []
    intent = payload.get('visualIntent')
    quote = _quote(payload)
    current = {
        'componentId': payload.get('componentId'),
        'visualIntent': intent,
    }
    if intent == 'process_timeline':
        steps = [str(step.get('label') or '') for step in (payload.get('steps') or []) if isinstance(step, dict)]
        if not steps:
            findings.append(_finding(
                scene, payload, 'COMPONENT_PARAMETER_INVALID',
                evidence={'reason': 'process_timeline_without_steps', 'sourceQuote': quote},
                current=current, suggested='SAFE_FALLBACK', severity='high',
            ))
        elif not timeline_order_verified(quote):
            findings.append(_finding(
                scene, payload, 'UNJUSTIFIED_PROCESS_TIMELINE',
                evidence={
                    'reason': 'noun_list_without_order_cue',
                    'sourceQuote': quote,
                    'labels': steps,
                },
                current=current, suggested='SAFE_FALLBACK', severity='high',
            ))
        else:
            missing = [label for label in steps if _label_missing(label, quote)]
            if missing:
                findings.append(_finding(
                    scene, payload, 'UNSUPPORTED_VISIBLE_CLAIM',
                    evidence={'reason': 'step_label_absent_from_quote', 'labels': missing, 'sourceQuote': quote},
                    current=current, suggested='SAFE_FALLBACK', severity='high',
                ))
    if intent == 'business_comparison':
        for side in ('left', 'right'):
            label = str(payload.get(side) or '')
            if not _label_missing(label, quote):
                continue
            leaked = any(label and label in other for other in other_quotes)
            kind = 'CROSS_SCENE_SEMANTIC_LEAK' if leaked else 'UNSUPPORTED_VISIBLE_CLAIM'
            findings.append(_finding(
                scene, payload, kind,
                evidence={'reason': 'comparison_side_absent_from_active_quote', 'side': side, 'label': label, 'sourceQuote': quote},
                current={**current, side: label}, suggested='SAFE_FALLBACK', severity='high',
            ))
    span = payload.get('range') if isinstance(payload.get('range'), dict) else {}
    unit = str(span.get('unit') or span.get('currency') or '')
    if intent == 'numeric_range' and unit and unit not in quote and not payload.get('unitOmitted'):
        findings.append(_finding(
            scene, payload, 'UNSUPPORTED_VISIBLE_CLAIM',
            evidence={'reason': 'currency_absent_from_quote', 'unit': unit, 'sourceQuote': quote},
            current={**current, 'unit': unit}, suggested='SAFE_FALLBACK', severity='high',
        ))
    life = payload.get('lifecycle') or {}
    if life.get('evidence_end') is not None and life.get('display_end') is not None:
        slack = float(life['display_end']) - float(life['evidence_end'])
        if slack > _HOLD_SLACK:
            findings.append(_finding(
                scene, payload, 'STALE_SEMANTIC_GRAPHIC',
                evidence={
                    'reason': 'display_exceeds_evidence_hold',
                    'evidence_end': life.get('evidence_end'),
                    'display_end': life.get('display_end'),
                    'slack_seconds': round(slack, 3),
                },
                current=current, suggested='SHORTEN_DISPLAY', severity='medium',
            ))
    return findings


def _card_findings(scene: dict) -> list[dict]:
    findings = []
    cards = ((scene.get('typography') or {}).get('cards') or []) + list(scene.get('criteriaCards') or [])
    for card in cards:
        if not isinstance(card, dict):
            continue
        title = str(card.get('title') or '').strip()
        evidence = card.get('evidence') or {}
        source = str(evidence.get('sourceText') or evidence.get('sourceQuote') or '') if isinstance(evidence, dict) else ''
        if title and source and title not in source:
            findings.append(_finding(
                scene, {'evidence': evidence, 'lifecycle': {}}, 'UNNECESSARY_TEXT_CARD',
                evidence={'reason': 'card_title_absent_from_its_source', 'title': title, 'sourceText': source},
                current={'title': title}, suggested='DROP_CARD', severity='medium',
            ))
    return findings


def _broll_findings(scenes: list[dict], alternatives: list[dict] | None) -> tuple[list[dict], list[dict]]:
    findings = []
    ranking = []
    seen: dict[str, str] = {}
    for scene in scenes:
        asset = _asset_id(scene)
        if not asset:
            continue
        quote = _quote(scene.get('semanticMotionV14') or {})
        if not quote:
            quote = str(((scene.get('typography') or {}).get('headline')) or '')
        if asset not in seen:
            seen[asset] = quote
            continue
        earlier = seen[asset]
        shared = _tokens(earlier) & _tokens(quote)
        if shared:
            findings.append(_finding(
                scene, scene.get('semanticMotionV14') or {}, 'REPEATED_BROLL',
                evidence={'reason': 'subject_recurs', 'assetId': asset, 'sharedTokens': sorted(shared)[:8]},
                current={'assetId': asset}, suggested='NO_CHANGE', severity='info', status='justified_reuse',
            ))
            continue
        ranked, log = rank_candidates(alternatives or [], quote, recent_asset_ids={asset})
        ranking.extend(log)
        if not ranked:
            findings.append(_finding(
                scene, scene.get('semanticMotionV14') or {}, 'NO_SAFE_ALTERNATIVE',
                evidence={'reason': 'repeated_asset_without_approved_relevant_alternative', 'assetId': asset},
                current={'assetId': asset}, suggested='NO_CHANGE', severity='low',
            ))
            findings.append(_finding(
                scene, scene.get('semanticMotionV14') or {}, 'REPEATED_BROLL',
                evidence={'reason': 'exact_reuse_without_shared_subject', 'assetId': asset},
                current={'assetId': asset}, suggested='HOLD', severity='medium',
            ))
            continue
        choice, reasons = ranked[0]
        findings.append(_finding(
            scene, scene.get('semanticMotionV14') or {}, 'REPEATED_BROLL',
            evidence={
                'reason': 'exact_reuse_with_approved_alternative',
                'assetId': asset,
                'alternative': choice.get('asset_id'),
                'rankReasons': reasons,
            },
            current={'assetId': asset}, suggested='REPLACE_APPROVED', severity='medium',
        ))
    return findings, ranking


def _layout_findings(scenes: list[dict]) -> list[dict]:
    findings = []
    run: list[dict] = []
    last = None
    for scene in scenes:
        layout = str(((scene.get('speaker') or {}).get('layout')) or '')
        if layout and layout == last:
            run.append(scene)
        else:
            run = [scene] if layout else []
            last = layout or None
        if len(run) == 3:
            findings.append(_finding(
                scene, scene.get('semanticMotionV14') or {}, 'LAYOUT_REPETITION',
                evidence={'reason': 'same_speaker_layout_three_scenes', 'layout': layout},
                current={'layout': layout}, suggested='NO_CHANGE', severity='low',
            ))
    return findings


def _weak_media_findings(scenes: list[dict]) -> list[dict]:
    findings = []
    for scene in scenes:
        asset = _asset_id(scene)
        foreground = scene.get('foreground') if isinstance(scene.get('foreground'), dict) else {}
        query = str((foreground or {}).get('query') or scene.get('query') or '')
        quote = _quote(scene.get('semanticMotionV14') or {}) or str(((scene.get('typography') or {}).get('headline')) or '')
        if not asset or not query:
            continue
        if _tokens(query) & _tokens(quote):
            continue
        findings.append(_finding(
            scene, scene.get('semanticMotionV14') or {}, 'WEAK_MEDIA_RELEVANCE',
            evidence={'reason': 'asset_query_shares_no_token_with_quote', 'assetId': asset, 'query': query, 'sourceQuote': quote},
            current={'assetId': asset, 'query': query}, suggested='HOLD', severity='medium',
        ))
    return findings


def rank_candidates(candidates: list[dict], quote: str, *, recent_asset_ids: set[str] | None = None) -> tuple[list[tuple[dict, list[str]]], list[dict]]:
    """Deterministic filter. Overlap count is a sort key, not a quality score."""
    recent = recent_asset_ids or set()
    query = _tokens(quote)
    kept: list[tuple[int, int, dict, list[str]]] = []
    log = []
    for candidate in candidates or []:
        asset_id = str(candidate.get('asset_id') or '')
        if not candidate.get('approved'):
            log.append({'asset_id': asset_id, 'decision': 'reject', 'reason': 'not_approved'})
            continue
        overlap = query & _tokens(str(candidate.get('label') or ''))
        if not overlap:
            log.append({'asset_id': asset_id, 'decision': 'reject', 'reason': 'no_source_overlap'})
            continue
        if asset_id in recent and not candidate.get('subject_recurs'):
            log.append({'asset_id': asset_id, 'decision': 'reject', 'reason': 'recent_duplicate'})
            continue
        reasons = ['approved', 'source_overlap:' + ','.join(sorted(overlap)[:6])]
        rating = candidate.get('user_quality_rating')
        if candidate.get('review_source') == 'user' and isinstance(rating, (int, float)):
            reasons.append(f'user_rating:{int(rating)}')
            rating_key = int(rating)
        else:
            reasons.append('no_verified_user_rating')
            rating_key = 0
        log.append({'asset_id': asset_id, 'decision': 'keep', 'reason': ';'.join(reasons)})
        kept.append((len(overlap), rating_key, candidate, reasons))
    kept.sort(key=lambda row: (row[0], row[1], str(row[2].get('asset_id'))), reverse=True)
    return [(row[2], row[3]) for row in kept], log


def recall_experience(query_embedding: list[float] | None = None, *, project_id: str | None = None) -> dict:
    """Retrieve user-reviewed scene rows. Never embeds text. Never treats cosine as quality."""
    started = time.perf_counter()
    base = {'available': False, 'hits': [], 'queries': 0, 'similarityIsNotQuality': True}
    if query_embedding is None:
        base['reason'] = 'no_query_embedding'
        base['elapsed_ms'] = 0
        return base
    if len(query_embedding) != VECTOR_DIM:
        base['reason'] = 'embedding_dimension_mismatch'
        base['dimension'] = len(query_embedding)
        base['expected'] = VECTOR_DIM
        base['elapsed_ms'] = round((time.perf_counter() - started) * 1000, 3)
        return base
    from . import experience_memory
    if not experience_memory.enabled():
        base['reason'] = 'experience_memory_disabled'
        base['elapsed_ms'] = round((time.perf_counter() - started) * 1000, 3)
        return base
    try:
        from .database import connect
        from .experience_embeddings import vector_literal
        literal = vector_literal([float(value) for value in query_embedding])
        with connect() as db:
            if not db.postgres:
                base['reason'] = 'postgres_unavailable'
                base['elapsed_ms'] = round((time.perf_counter() - started) * 1000, 3)
                return base
            db.execute("SET LOCAL statement_timeout = '1500ms'")
            rows = db.execute(
                '''SELECT generation_id, treatment, user_quality_rating, review_source,
                          vector_dimension,
                          (1 - (embedding <=> ?::public.vector)) AS similarity
                   FROM scene_feedback
                   WHERE review_source='user'
                     AND embedding IS NOT NULL
                     AND vector_dimension=?
                     AND (? IS NULL OR project_id=?)
                   ORDER BY embedding <=> ?::public.vector
                   LIMIT 8''',
                (literal, VECTOR_DIM, project_id, project_id, literal),
            ).fetchall()
        hits = []
        for row in rows:
            if int(row['vector_dimension'] or 0) != VECTOR_DIM:
                continue
            if row['review_source'] != 'user':
                continue
            hits.append({
                'generation_id': row['generation_id'],
                'treatment': row['treatment'],
                'user_quality_rating': row['user_quality_rating'],
                'review_source': 'user',
                'similarity': float(row['similarity']),
                'similarityIsNotQuality': True,
            })
        return {
            'available': True,
            'reason': 'user_scene_feedback',
            'hits': hits,
            'queries': 1,
            'similarityIsNotQuality': True,
            'elapsed_ms': round((time.perf_counter() - started) * 1000, 3),
        }
    except Exception as exc:
        from .experience_memory import redact
        base['reason'] = 'experience_store_error'
        base['detail'] = redact(str(exc))
        base['elapsed_ms'] = round((time.perf_counter() - started) * 1000, 3)
        return base


def evaluate(plan: dict, transcript: list | None = None, *, experience: dict | None = None, alternatives: list[dict] | None = None) -> dict:
    started = time.perf_counter()
    if not isinstance(plan, dict) or not isinstance(plan.get('scenes'), list):
        return {
            'status': 'malformed_plan',
            'findings': [],
            'decisions': [],
            'experience': experience or {'available': False, 'reason': 'not_queried'},
            'elapsed_ms': round((time.perf_counter() - started) * 1000, 3),
        }
    scenes = plan['scenes']
    quotes = []
    payloads = []
    for scene in scenes:
        payload = scene.get('semanticMotionV14') if isinstance(scene, dict) else None
        payloads.append(payload if isinstance(payload, dict) else None)
        quotes.append(_quote(payload) if isinstance(payload, dict) else '')
    findings: list[dict] = []
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        payload = payloads[index]
        if payload:
            others = [quotes[i] for i in range(len(quotes)) if i != index]
            findings.extend(_motion_findings(scene, payload, others))
        findings.extend(_card_findings(scene))
    usable = [scene for scene in scenes if isinstance(scene, dict)]
    broll, ranking = _broll_findings(usable, alternatives)
    findings.extend(broll)
    findings.extend(_layout_findings(usable))
    findings.extend(_weak_media_findings(usable))
    flagged = {item['scene_id'] for item in findings if item['severity'] != 'info'}
    decisions = []
    for scene, payload in zip(scenes, payloads):
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get('sceneId') or '')
        if scene_id in flagged:
            continue
        if payload:
            decisions.append({'scene_id': scene_id, 'decision': 'NO_CHANGE', 'reason': 'motion_supported_by_active_quote'})
        else:
            decisions.append({'scene_id': scene_id, 'decision': 'NO_CHANGE', 'reason': 'no_optional_motion'})
    store = experience if experience is not None else {'available': False, 'reason': 'no_query_embedding', 'hits': [], 'queries': 0, 'similarityIsNotQuality': True}
    return {
        'status': 'ok',
        'findings': findings,
        'decisions': decisions,
        'ranking': ranking,
        'experience': store,
        'transcript_rows': len(transcript or []),
        'elapsed_ms': round((time.perf_counter() - started) * 1000, 3),
        'queries': int(store.get('queries') or 0),
    }


def _shorten(payload: dict) -> dict:
    life = dict(payload.get('lifecycle') or {})
    evidence_end = life.get('evidence_end')
    if evidence_end is None:
        return payload
    limit = float(evidence_end) + 1.2
    life['display_end'] = min(float(life.get('display_end') or limit), limit)
    out = dict(payload)
    out['lifecycle'] = life
    output = list(payload.get('outputTime') or [])
    if len(output) == 2:
        out['outputTime'] = [output[0], min(float(output[1]), limit)]
    return out


def apply_safe(plan: dict, report: dict) -> dict:
    out = copy.deepcopy(plan)
    scenes = {str(scene.get('sceneId')): scene for scene in out.get('scenes') or [] if isinstance(scene, dict)}
    applied = []
    for finding in report.get('findings') or []:
        scene = scenes.get(finding.get('scene_id'))
        if scene is None:
            continue
        kind = finding.get('finding_type')
        if kind in _DROP_MOTION and scene.get('semanticMotionV14'):
            scene.pop('semanticMotionV14', None)
            applied.append({'finding_id': finding.get('finding_id'), 'action': 'drop_motion'})
        elif kind == 'STALE_SEMANTIC_GRAPHIC' and isinstance(scene.get('semanticMotionV14'), dict):
            scene['semanticMotionV14'] = _shorten(scene['semanticMotionV14'])
            applied.append({'finding_id': finding.get('finding_id'), 'action': 'shorten_display'})
        elif kind == 'UNNECESSARY_TEXT_CARD':
            title = (finding.get('evidence') or {}).get('title')
            cards = ((scene.get('typography') or {}).get('cards') or [])
            if isinstance(scene.get('typography'), dict):
                scene['typography']['cards'] = [card for card in cards if card.get('title') != title]
            scene['criteriaCards'] = [card for card in (scene.get('criteriaCards') or []) if card.get('title') != title]
            applied.append({'finding_id': finding.get('finding_id'), 'action': 'drop_card', 'title': title})
        elif kind == 'REPEATED_BROLL' and finding.get('suggested_action') == 'REPLACE_APPROVED':
            alternative = (finding.get('evidence') or {}).get('alternative')
            reasons = (finding.get('evidence') or {}).get('rankReasons') or []
            if alternative and any(str(reason).startswith('approved') for reason in reasons):
                foreground = dict(scene.get('foreground') or {})
                foreground['assetId'] = alternative
                foreground['optimizerReplacement'] = True
                scene['foreground'] = foreground
                applied.append({'finding_id': finding.get('finding_id'), 'action': 'replace_broll', 'assetId': alternative})
    out['visualOptimizerApplied'] = applied
    out['visualQualityReport'] = report
    out['visualOptimizerMode'] = 'apply_safe'
    return out


def apply(plan: dict | None, transcript: list | None = None, *, mode: Any = None, experience: dict | None = None, alternatives: list[dict] | None = None) -> dict | None:
    """Fail open. A diagnostic error leaves the Director plan renderable."""
    chosen = normalize_mode(mode)
    if chosen == 'off' or not isinstance(plan, dict):
        return plan
    try:
        if experience is None and chosen != 'off':
            experience = recall_experience(None)
        report = evaluate(plan, transcript, experience=experience, alternatives=alternatives)
    except Exception as exc:
        out = dict(plan)
        out['visualOptimizerMode'] = chosen
        out['visualOptimizerError'] = type(exc).__name__
        return out
    if report.get('status') != 'ok':
        out = dict(plan)
        out['visualOptimizerMode'] = chosen
        out['visualQualityReport'] = report
        return out
    if chosen == 'shadow':
        return {**plan, 'visualOptimizerMode': 'shadow', 'visualQualityReport': report}
    return apply_safe(plan, report)
