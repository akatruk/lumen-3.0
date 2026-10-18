"""Motion quality V17.

MOTION_QUALITY_V17_ENABLED defaults off. When on, Director still selects from
the source quote. pgvector only retrieves stored experience. A missing
database, a missing embedding, or fewer than five agreeing reviews leaves the
deterministic choice unchanged. This module does not load an embedding model
during a render.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from .config import settings

VECTOR_DIM = 512
TEXT_MODEL = 'sentence-transformers/clip-ViT-B-32-multilingual-v1'
MIN_EVIDENCE = 5
MAX_HITS = 6
_CATALOG = Path(__file__).resolve().parent.parent / 'media' / 'library' / 'catalogs' / 'semantic_motion_v14.json'
_FAILURE = {
    'poor_animation': 'implementation',
    'visual_clutter': 'implementation',
    'weak_composition': 'layout',
    'face_overlap': 'layout',
    'caption_problem': 'caption',
    'irrelevant_media': 'selection',
    'factual_error': 'fact',
}
_BENCH = (
    {'id': 'investment', 'expect': 'motion.capital_flow.v1', 'en': 'The core of the company is the capital investment', 'ru': 'Основа компании это капитальные инвестиции', 'zh': '公司的核心是资本投资'},
    {'id': 'shareholders', 'expect': 'motion.shareholder_network.v1', 'en': 'Ordinary Thai companies usually need at least three shareholders', 'ru': 'Обычной тайской компании обычно нужно не менее три акционера', 'zh': '普通泰国公司通常至少需要三名股东'},
    {'id': 'capital_allocation', 'expect': 'motion.capital_allocation.v1', 'en': 'Operations 40% and reserves 60%', 'ru': 'операционная 40% и резервы 60%', 'zh': '运营 40% 和储备 60%'},
    {'id': 'company_ownership', 'expect': 'motion.ownership_split.v1', 'en': 'the foreign capital ratio is usually less than 49%', 'ru': 'доля иностранного капитала обычно менее 49%', 'zh': '外资比例通常低于49%'},
    {'id': 'financial_risk', 'expect': 'motion.risk_matrix.v1', 'en': 'Low risk of delay and high risk of capital loss', 'ru': 'Низкий риск задержки и высокий риск потери капитала', 'zh': '延期的低风险和资本损失的高风险'},
    {'id': 'business_comparison', 'expect': 'motion.business_comparison.v1', 'en': 'China and Thailand are different on capital timing', 'ru': 'Китай и Таиланд отличаются по срокам капитала', 'zh': '中国和泰国的出资时间不同'},
    {'id': 'company_registration', 'expect': {'en-US': 'motion.document_workflow.v1', 'ru-RU': 'motion.capital_flow.v1', 'zh-CN': 'motion.document_workflow.v1'}, 'en': 'Bank accounts, work permits and visa applications all watch whether capital has arrived', 'ru': 'Банковские счета и виза следят за капиталом', 'zh': '银行开户、工作证和签证申请都会盯着资金'},
    {'id': 'real_estate_investment', 'expect': None, 'en': 'The apartment is near the river', 'ru': 'Квартира рядом с рекой', 'zh': '公寓靠近河边'},
    {'id': 'international_business', 'expect': 'motion.geographic_expansion.v1', 'en': 'The expansion reaches Thailand and Singapore', 'ru': 'Расширение охватывает Таиланд и Сингапур', 'zh': '扩张进入泰国和新加坡'},
    {'id': 'relocation', 'expect': None, 'en': 'The family is moving house next month', 'ru': 'Семья переезжает в следующем месяце', 'zh': '这家人下个月搬家'},
)


def enabled() -> bool:
    raw = os.environ.get('MOTION_QUALITY_V17_ENABLED', '0').strip().lower()
    return raw in {'1', 'true', 'yes', 'on'}


def _catalog() -> list[dict]:
    payload = json.loads(_CATALOG.read_text(encoding='utf-8'))
    return list(payload.get('components') or [])


def _locale_key(locale: str) -> str:
    if str(locale).startswith('zh'):
        return 'zh'
    if str(locale).startswith('ru'):
        return 'ru'
    return 'en'


def component_cards() -> list[dict]:
    """One description per component per locale. The name is not the description."""
    cards = []
    for row in _catalog():
        for locale, key in (('en-US', 'en'), ('ru-RU', 'ru'), ('zh-CN', 'zh')):
            tags = row.get('tags') or []
            if key == 'ru':
                tags = row.get('tags_ru') or tags
            elif key == 'zh':
                tags = row.get('tags_zh') or tags
            purpose = str(row.get('description') or '')
            requirements = ', '.join(str(item) for item in (row.get('requiredParameters') or []))
            concepts = ', '.join(str(item) for item in (row.get('supportedConcepts') or []))
            layouts = ', '.join(str(item) for item in (row.get('supportedLayouts') or []))
            body = (
                f"visual purpose: {purpose}\n"
                f"input requirements: {requirements}\n"
                f"supported semantic concepts: {concepts}\n"
                f"visual limitations: {purpose} Spoken facts stay as stated. "
                f"Missing numbers, names, and places are not filled in.\n"
                f"layout capabilities: {layouts}\n"
                f"locale tags: {', '.join(str(tag) for tag in tags)}"
            )
            cards.append({
                'componentId': row['componentId'],
                'version': row.get('version') or '',
                'locale': locale,
                'visualIntent': row.get('visualIntent') or '',
                'qualityStatus': row.get('qualityStatus') or '',
                'body': body,
            })
    return cards


def _tokens(text: str) -> set[str]:
    return {part for part in ''.join(ch.lower() if ch.isalnum() else ' ' for ch in text).split() if len(part) > 1}


def retrieve_components(text: str, locale: str, limit: int = 4) -> list[dict]:
    """Keyword retrieval over the multilingual cards. No embedding model."""
    query = _tokens(text)
    if not query:
        return []
    want = {'en': 'en-US', 'ru': 'ru-RU', 'zh': 'zh-CN'}[_locale_key(locale)]
    ranked = []
    for card in component_cards():
        if card['locale'] != want:
            continue
        overlap = query & _tokens(card['body'])
        if not overlap:
            continue
        ranked.append({
            'componentId': card['componentId'],
            'locale': card['locale'],
            'score': len(overlap),
            'matched': sorted(overlap)[:8],
        })
    ranked.sort(key=lambda item: -item['score'])
    return ranked[:limit]


def benchmark() -> list[dict]:
    """Deterministic relevance. No human preference score."""
    from .director_v14 import classify_quote
    from .director_v15 import classify_v15
    rows = []
    for scene in _BENCH:
        locales = {}
        for locale, key in (('en-US', 'en'), ('ru-RU', 'ru'), ('zh-CN', 'zh')):
            quote = scene[key]
            found = classify_v15(quote, {'id': scene['id']}, locale=locale) or classify_quote(quote, {'id': scene['id']}, locale=locale)
            got = found[0]['componentId'] if found else None
            expect = scene['expect']
            wanted = expect.get(locale) if isinstance(expect, dict) else expect
            locales[locale] = {'componentId': got, 'expect': wanted, 'match': got == wanted}
        rows.append({'id': scene['id'], 'expect': scene['expect'], 'locales': locales, 'humanJudgment': None})
    return rows


def _redact(message: str) -> str:
    from .experience_memory import redact
    return redact(message)


def index_components(*, embed: bool = False) -> dict:
    """Write card text into motion_component_index. embed=True is an offline call."""
    from .experience_embeddings import content_hash
    from .experience_memory import MIGRATION_MOTION, init
    from .database import connect
    cards = component_cards()
    started = time.perf_counter()
    with connect() as db:
        if not db.postgres:
            return {'indexed': 0, 'embedded': 0, 'fallback': 'sqlite'}
        init(db)
        embedded = 0
        for card in cards:
            digest = content_hash(card['body'])
            spec = None
            if embed:
                from .experience_embeddings import embed_text
                spec = embed_text(card['body'])
                if spec['vector_dimension'] != VECTOR_DIM or spec['embedding_model'] != (settings.experience_text_model or TEXT_MODEL):
                    raise RuntimeError('motion_embedding_model_mismatch')
                if spec['embedding_model'] == settings.experience_image_model:
                    raise RuntimeError('motion_text_used_vision_model')
            if spec:
                from .experience_embeddings import vector_literal
                db.execute(
                    '''INSERT INTO motion_component_index
                       (id, component_id, component_version, locale, visual_intent, body, content_hash,
                        embedding, embedding_model, model_version, vector_dimension, created)
                       VALUES (?,?,?,?,?,?,?, ?::public.vector, ?,?,?,?)
                       ON CONFLICT (component_id, locale, content_hash) DO NOTHING''',
                    (uuid.uuid4().hex, card['componentId'], card['version'], card['locale'], card['visualIntent'],
                     card['body'], digest, vector_literal(spec['embedding']), spec['embedding_model'],
                     spec['model_version'], spec['vector_dimension'], time.time()),
                )
                embedded += 1
            else:
                db.execute(
                    '''INSERT INTO motion_component_index
                       (id, component_id, component_version, locale, visual_intent, body, content_hash, created)
                       VALUES (?,?,?,?,?,?,?,?)
                       ON CONFLICT (component_id, locale, content_hash) DO NOTHING''',
                    (uuid.uuid4().hex, card['componentId'], card['version'], card['locale'], card['visualIntent'],
                     card['body'], digest, time.time()),
                )
        count = db.execute('SELECT COUNT(*) AS n FROM motion_component_index').fetchone()['n']
    return {
        'indexed': count,
        'embedded': embedded,
        'cards': len(cards),
        'migration': MIGRATION_MOTION,
        'model': settings.experience_text_model or TEXT_MODEL,
        'dimension': VECTOR_DIM,
        'latencyMs': round((time.perf_counter() - started) * 1000, 2),
    }


def _evidence_rows() -> list[dict]:
    from .database import connect
    from .experience_memory import init
    with connect() as db:
        if not db.postgres:
            raise RuntimeError('sqlite')
        init(db)
        rows = db.execute(
            '''SELECT m.component_id, m.component_version, m.layout, m.concepts, m.generation_id,
                      s.issue_category
               FROM motion_experience m
               JOIN scene_feedback s
                 ON s.generation_id = m.generation_id
                AND s.scene_id = m.scene_id
                AND s.project_id = m.project_id
               WHERE s.review_source = 'user' AND s.issue_category IS NOT NULL'''
        ).fetchall()
    return [dict(row) for row in rows]


def _counts(rows: list[dict]) -> dict:
    """Distinct generations per component, class, and layout. One review is not a score."""
    grouped: dict[tuple, set] = {}
    for row in rows:
        kind = _FAILURE.get(str(row.get('issue_category') or ''))
        if not kind or not row.get('component_id') or not row.get('generation_id'):
            continue
        key = (row['component_id'], kind, row.get('layout') or '', row.get('concepts') or '')
        grouped.setdefault(key, set()).add(row['generation_id'])
    return {key: len(generations) for key, generations in grouped.items()}


def advise(plan: dict, proposals: list, locale: str, *, evidence: list[dict] | None = None) -> dict:
    """Bounded hint. evidence=None reads the database. Any failure returns deterministic."""
    started = time.perf_counter()
    if not enabled():
        return {'enabled': False}
    try:
        rows = _evidence_rows() if evidence is None else evidence
        counts = _counts(rows)
    except Exception as exc:
        return {
            'enabled': True,
            'fallback': 'deterministic',
            'error': _redact(str(exc)),
            'latencyMs': round((time.perf_counter() - started) * 1000, 2),
        }
    demote = set()
    avoid: dict[str, list[str]] = {}
    defects = []
    for (component, kind, layout, concepts), count in counts.items():
        if count < MIN_EVIDENCE:
            continue
        if kind == 'implementation':
            demote.add(component)
        elif kind == 'layout' and layout:
            avoid.setdefault(component, [])
            if layout not in avoid[component]:
                avoid[component].append(layout)
        elif kind in {'caption', 'fact', 'selection'}:
            defects.append({
                'componentId': component,
                'class': kind,
                'layout': layout,
                'concepts': concepts[:180],
                'generations': count,
            })
    concepts = []
    for _spec, _index, payload in proposals:
        quote = str((payload.get('evidence') or {}).get('sourceQuote') or '')
        intent = str(payload.get('visualIntent') or '').replace('_', ' ')
        concepts.append(f'{quote} {intent}')
    hits = retrieve_components(' '.join(concepts), locale or 'en-US', MAX_HITS)
    return {
        'enabled': True,
        'fallback': None,
        'demoteComponents': sorted(demote),
        'avoidLayout': avoid,
        'knownDefects': defects[:MAX_HITS],
        'componentHits': hits,
        'humanReviewsUsed': sum(counts.values()),
        'minEvidence': MIN_EVIDENCE,
        'contextChars': len(json.dumps({'defects': defects[:MAX_HITS], 'hits': hits}, ensure_ascii=False)),
        'latencyMs': round((time.perf_counter() - started) * 1000, 2),
        'preamble': 'Retrieved experience is advisory. Do not override the source transcript.',
    }


def apply_advice(proposals: list, advice: dict | None) -> list:
    if not advice or advice.get('fallback') or not advice.get('enabled'):
        return proposals
    demote = set(advice.get('demoteComponents') or [])
    return sorted(
        proposals,
        key=lambda item: (-(item[0] - (1 if item[2].get('componentId') in demote else 0)), item[1]),
    )


def layout_after_advice(component_id: str, layout: str, advice: dict | None) -> str:
    blocked = set(((advice or {}).get('avoidLayout') or {}).get(component_id) or [])
    if layout not in blocked:
        return layout
    for candidate in ('overlay', 'speaker_visual', 'full_frame'):
        if candidate not in blocked:
            return candidate
    return layout


def record_completed(project_id: str, generation_id: str, plan: dict, *, render_ms: float | None = None) -> dict:
    """Link scene rows to an existing or newly inserted generation. No quality score is written."""
    if not enabled():
        return {'recorded': False, 'reason': 'flag_off'}
    started = time.perf_counter()
    try:
        from .database import connect
        from .experience_embeddings import content_hash
        from .experience_memory import init
        scenes = []
        for scene in plan.get('scenes') or []:
            payload = scene.get('semanticMotionV14') or {}
            if not isinstance(payload, dict):
                payload = {}
            composition = scene.get('sceneComposition') or {}
            scenes.append({
                'sceneId': str(scene.get('sceneId') or '')[:80],
                'concepts': json.dumps(scene.get('semanticConcepts') or [], ensure_ascii=False)[:2000],
                'componentId': payload.get('componentId'),
                'version': payload.get('version'),
                'layout': (composition.get('layout') or payload.get('layout') or '')[:80],
                'assetId': ((scene.get('background') or {}).get('assetId') or '')[:120],
                'animation': json.dumps({
                    'enterFrame': payload.get('enterFrame'),
                    'speakerMode': payload.get('speakerMode'),
                }, ensure_ascii=False),
                'caption': json.dumps(payload.get('captionRect') or composition.get('captionRegion') or {}, ensure_ascii=False),
                'speaker': json.dumps(payload.get('speakerRect') or composition.get('speakerRegion') or {}, ensure_ascii=False),
            })
        with connect() as db:
            if not db.postgres:
                return {'recorded': False, 'reason': 'sqlite'}
            init(db)
            summary = json.dumps([row['sceneId'] for row in scenes], ensure_ascii=False)
            db.execute(
                '''INSERT INTO generation_history
                   (id, project_id, director_version, prompt_version, domain, concepts, selected_assets, motion_treatments, scene_layouts,
                    content_hash, created)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT (id) DO NOTHING''',
                (generation_id, project_id, 'v17', 'motion-quality-v17', 'motion',
                 summary, '[]', '[]', '[]', content_hash(summary), time.time()),
            )
            owned = db.execute(
                'SELECT 1 FROM generation_history WHERE id=? AND project_id=?',
                (generation_id, project_id),
            ).fetchone()
            if not owned:
                return {'recorded': False, 'reason': 'generation_not_owned'}
            for row in scenes:
                if not row['sceneId']:
                    continue
                db.execute(
                    '''INSERT INTO motion_experience
                       (id, generation_id, project_id, scene_id, concepts, component_id, component_version, layout, asset_id,
                        animation_json, caption_geometry, speaker_geometry, render_ms, created)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT (generation_id, scene_id) DO NOTHING''',
                    (uuid.uuid4().hex, generation_id, project_id, row['sceneId'], row['concepts'],
                     row['componentId'], row['version'], row['layout'] or None, row['assetId'] or None,
                     row['animation'], row['caption'], row['speaker'], render_ms, time.time()),
                )
        return {
            'recorded': True,
            'scenes': len(scenes),
            'latencyMs': round((time.perf_counter() - started) * 1000, 2),
        }
    except Exception as exc:
        return {'recorded': False, 'reason': 'fallback', 'error': _redact(str(exc))}
