"""Director V11 — semantic intelligence: speech-first topic-aware visual planning.

Runs after V9 composition intelligence and before optional premium 3D.
Builds a semantic content map from the transcript, requires source evidence for
every selected visual concept, and rejects immigration/relocation defaults when
speech is about another domain (e.g. capital investment / shareholder structure).

Does not invent facts, percentages, or legal claims. Does not generate media.
"""
from __future__ import annotations

import re
from typing import Any

from .locale_consistency import locale_bucket, prefer_locale_field

# ---------------------------------------------------------------------------
# Concept lexicon: spoken evidence → stable concept IDs
# Each rule: (concept_id, patterns, domain, visual_hints)
# ---------------------------------------------------------------------------
_CONCEPT_RULES: tuple[tuple[str, tuple[str, ...], str, dict[str, Any]], ...] = (
    # Investment / corporate structure
    (
        'foreign_investment_company',
        (r'foreign\s+investment', r'иностранн\w*\s+инвестиц', r'外资', r'外商投资'),
        'investment',
        {'query': 'business meeting corporate office asia', 'keyword': 'investment'},
    ),
    (
        'chinese_investment_company',
        (r'chinese\s+investment', r'китайск\w*\s+инвестиц', r'中国投资', r'中资'),
        'investment',
        {'query': 'china business office skyline corporate', 'keyword': 'investment'},
    ),
    (
        'capital_investment',
        (r'capital\s+investment', r'капитальн\w*\s+вложен', r'资本投入', r'注册资本', r'\bcapital\b'),
        'investment',
        {'query': 'capital investment finance chart', 'keyword': 'capital'},
    ),
    (
        'government_leadership',
        (r'government', r'руководств\w*\s+правитель', r'政府'),
        'investment',
        {'query': 'government building formal architecture', 'keyword': 'governance'},
    ),
    (
        'deferred_payment',
        (r'pay\s+immediately', r'не\s+нужно\s+платить', r'无需立即', r'credit\s+card'),
        'investment',
        {'query': 'business contract signing desk', 'keyword': 'capital'},
    ),
    (
        'shareholder_responsibility',
        (r'shareholder\s+responsib', r'ответственност\w*\s+акционер', r'股东责任', r'shareholder'),
        'investment',
        {'query': 'corporate boardroom shareholders meeting', 'keyword': 'shareholder'},
    ),
    (
        'capital_judgment',
        (r'capital\s+judgment', r'оценк\w*\s+капитал', r'资本判断'),
        'investment',
        {'query': 'financial analysis spreadsheet desk', 'keyword': 'capital'},
    ),
    (
        'thailand_company_structure',
        (r'thailand', r'тайланд', r'泰国', r'shareholder\s+structure', r'структур\w*\s+акционер'),
        'investment',
        {'query': 'bangkok business district skyline daytime', 'keyword': 'thailand'},
    ),
    (
        'thai_shareholder_count',
        (
            r'three\s+shareholders', r'at\s+least\s+three\s+shareholders',
            r'три\s+акционер', r'至少三名股东', r'三名股东', r'三位股东', r'at\s+least\s+three',
        ),
        'investment',
        {'query': 'corporate ownership structure diagram desk', 'keyword': 'shareholder'},
    ),
    (
        'foreign_ownership_ratio',
        (r'foreign\s+capital\s+ratio', r'less\s+than\s+49', r'49\s*%', r'иностранн\w*\s+доля', r'外资比例', r'不超过\s*49'),
        'investment',
        {'query': 'equity ownership pie chart business', 'keyword': 'ownership'},
    ),
    (
        'company_control',
        (r'control\s+power', r'контроль', r'控制权', r'locked\s+in', r'就被锁定'),
        'investment',
        {'query': 'corporate control handshake boardroom', 'keyword': 'control'},
    ),
    (
        'capital_return',
        (r'money\s+is\s+returned', r'возврат\w*\s+денег', r'资金返还', r'initial\s+rhythm', r'出资节奏'),
        'investment',
        {'query': 'business growth arrow finance chart', 'keyword': 'capital'},
    ),
    # Immigration / relocation (only when spoken)
    (
        'passport_document',
        (r'\bpassport\b', r'паспорт', r'护照'),
        'immigration',
        {'query': 'passport document object', 'keyword': 'passport'},
    ),
    (
        'residence_permit',
        (r'residenc', r'жительств', r'居留', r'permit'),
        'immigration',
        {'query': 'residence permit document', 'keyword': 'residency'},
    ),
    (
        'relocation_move',
        (r'relocati', r'переезд', r'搬家', r'搬迁'),
        'immigration',
        {'query': 'family home doorway relocation', 'keyword': 'relocation'},
    ),
    (
        'visa_application',
        (r'\bvisa\b', r'виз[аыуе]', r'签证'),
        'immigration',
        {'query': 'visa application paperwork desk', 'keyword': 'passport'},
    ),
    (
        'family_travel',
        (r'family\s+who\s+travels', r'семья\s+едет', r'同行家人', r'travels\s+with\s+you'),
        'immigration',
        {'query': 'family new home arrival residence', 'keyword': 'family'},
    ),
    (
        'immigration_consult',
        (r'immigration', r'иммиграц', r'移民咨询'),
        'immigration',
        {'query': 'consultation meeting advisor', 'keyword': 'consult'},
    ),
    # Generic advisory (shared)
    (
        'consultation',
        (r'consult', r'консульт', r'咨询'),
        'generic',
        {'query': 'consultation meeting advisor', 'keyword': 'consult'},
    ),
    (
        'documents_process',
        (r'document', r'документ', r'文件', r'paperwork'),
        'generic',
        {'query': 'document review desk paperwork', 'keyword': 'documents'},
    ),
)

# Hardcoded immigration contamination signatures to strip when domain ≠ immigration.
_IMMIGRATION_QUERY_MARKERS = (
    'relocation', 'residence permit', 'passport document', 'family home doorway',
    'family new home arrival', 'visa application', 'immigrat',
)
_IMMIGRATION_CARD_MARKERS = (
    'travels with you', 'where you are going', 'переезжаете', 'кто едет',
    '迁往哪里', '同行家人', 'program can realistically cost', 'бюджет программы',
)
_IMMIGRATION_KEYWORDS = frozenset({
    'relocation', 'residency', 'passport', 'family',
})
_IMMIGRATION_ASSET_MARKERS = (
    'passport', 'suitcase', 'imm_obj', 'relocation', 'pm_scene_mobility',
)

# Topic packs for criteria / steps when speech evidence supports the domain.
_CRITERIA_PACKS: dict[str, dict[str, tuple[dict[str, str], ...]]] = {
    'investment': {
        'en': (
            {'title': 'Capital', 'explanation': 'how capital investment is structured'},
            {'title': 'Shareholders', 'explanation': 'who holds ownership and responsibility'},
            {'title': 'Control', 'explanation': 'how company control is locked at formation'},
        ),
        'ru': (
            {'title': 'Капитал', 'explanation': 'как устроено капитальное вложение'},
            {'title': 'Акционеры', 'explanation': 'кто несёт ответственность и долю'},
            {'title': 'Контроль', 'explanation': 'как фиксируется контроль при создании'},
        ),
        'zh': (
            {'title': '资本', 'explanation': '资本投入如何安排'},
            {'title': '股东', 'explanation': '谁持有股权与责任'},
            {'title': '控制权', 'explanation': '成立时如何锁定控制权'},
        ),
    },
    'immigration': {
        'en': (
            {'title': 'Goals', 'explanation': 'where you are going and why'},
            {'title': 'Family', 'explanation': 'who travels with you and when'},
            {'title': 'Budget', 'explanation': 'what the program can realistically cost'},
        ),
        'ru': (
            {'title': 'Цели', 'explanation': 'куда и зачем вы переезжаете'},
            {'title': 'Семья', 'explanation': 'кто едет с вами и в какие сроки'},
            {'title': 'Бюджет', 'explanation': 'какой бюджет программы реалистичен'},
        ),
        'zh': (
            {'title': '目标', 'explanation': '迁往哪里以及为何出发'},
            {'title': '家庭', 'explanation': '同行家人与时间安排'},
            {'title': '预算', 'explanation': '项目费用是否可承受'},
        ),
    },
}

_STEPS_PACKS: dict[str, dict[str, dict[str, Any]]] = {
    # Never use bare "Shareholders"/"Акционеры"/"股东" as a numbered step label —
    # CleanSteps paints "{n} {label}" which reads as invented headcount ("2 Shareholders").
    # Ownership count belongs on evidenced cards (V11.1+), not step indices.
    'investment': {
        'en': {'title': 'Formation path', 'steps': ['Capital', 'Structure', 'Control']},
        'ru': {'title': 'Путь создания', 'steps': ['Капитал', 'Структура', 'Контроль']},
        'zh': {'title': '设立路径', 'steps': ['资本', '结构', '控制权']},
    },
    'immigration': {
        'en': {'title': 'Guided process', 'steps': ['Consult', 'Program', 'Documents']},
        'ru': {'title': 'Сопровождение', 'steps': ['Консультация', 'Программа', 'Документы']},
        'zh': {'title': '全程陪同', 'steps': ['咨询', '方案', '文件']},
    },
}

# Scene-id → preferred concept ids for long60 beats (topic-aware substitution).
_BEAT_CONCEPT_PREF: dict[str, tuple[str, ...]] = {
    'hook': ('foreign_investment_company', 'chinese_investment_company', 'relocation_move', 'passport_document'),
    'context': ('capital_investment', 'chinese_investment_company', 'relocation_move'),
    'problem': ('government_leadership', 'deferred_payment', 'residence_permit'),
    'residency': ('shareholder_responsibility', 'thailand_company_structure', 'documents_process', 'residence_permit'),
    'consult': ('consultation', 'capital_judgment', 'immigration_consult'),
    'beside': ('thai_shareholder_count', 'foreign_ownership_ratio', 'company_control', 'family_travel'),
    'steps': ('company_control', 'capital_return', 'documents_process'),
    'proof': ('thailand_company_structure', 'foreign_ownership_ratio', 'documents_process'),
    'payoff': ('company_control', 'capital_return'),
    'return': ('capital_return',),
}


def _segment_rows(transcript: list | None, locale: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, row in enumerate(transcript or []):
        if hasattr(row, 'model_dump'):
            row = row.model_dump()
        if not isinstance(row, dict):
            continue
        text = prefer_locale_field(row, locale) or ' '.join(str(row.get('text') or '').split())
        if not text:
            text = ' '.join(str(row.get('original') or row.get('en') or '').split())
        if not text:
            continue
        try:
            start = float(row.get('start') or 0)
            end = float(row.get('end') or 0)
        except (TypeError, ValueError):
            start, end = float(i), float(i) + 1
        if end <= start:
            end = start + 0.5
        rows.append({
            'id': row.get('id') or f'seg_{i:03d}',
            'start': start,
            'end': end,
            'text': text,
        })
    return rows


def _match_concepts(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for concept_id, patterns, domain, hints in _CONCEPT_RULES:
        if concept_id in seen:
            continue
        for pat in patterns:
            if re.search(pat, text or '', re.I):
                seen.add(concept_id)
                hits.append({
                    'conceptId': concept_id,
                    'domain': domain,
                    'match': pat,
                    'query': hints.get('query'),
                    'keyword': hints.get('keyword'),
                })
                break
    return hits


def build_semantic_map(transcript: list | None, locale: str | None = None) -> dict[str, Any]:
    """Map spoken segments → stable concept IDs with provenance."""
    segments = _segment_rows(transcript, locale)
    concept_hits: list[dict[str, Any]] = []
    domain_scores = {'investment': 0, 'immigration': 0, 'generic': 0}
    for seg in segments:
        matched = _match_concepts(seg['text'])
        for m in matched:
            domain_scores[m['domain']] = domain_scores.get(m['domain'], 0) + 1
            concept_hits.append({
                **m,
                'segmentId': seg['id'],
                'start': seg['start'],
                'end': seg['end'],
                'evidence': seg['text'],
            })
    # Domain decision: speech evidence wins; mixed when both ≥1.
    inv, imm = domain_scores['investment'], domain_scores['immigration']
    if inv and imm:
        primary = 'mixed'
    elif inv:
        primary = 'investment'
    elif imm:
        primary = 'immigration'
    else:
        primary = 'generic'

    unique_concepts = []
    seen_c: set[str] = set()
    for h in concept_hits:
        if h['conceptId'] not in seen_c:
            seen_c.add(h['conceptId'])
            unique_concepts.append(h['conceptId'])

    return {
        'version': 'v11',
        'locale': locale,
        'primaryDomain': primary,
        'domainScores': domain_scores,
        'segments': segments,
        'concepts': concept_hits,
        'conceptIds': unique_concepts,
        'bannedWithoutEvidence': list(_IMMIGRATION_KEYWORDS) if primary == 'investment' else [],
    }


def detect_topic_domain(transcript: list | None, locale: str | None = None) -> str:
    return build_semantic_map(transcript, locale)['primaryDomain']


def _criteria_for_domain(domain: str, locale: str | None) -> list[dict[str, str]]:
    bucket = locale_bucket(locale)
    pack = _CRITERIA_PACKS.get(domain) or _CRITERIA_PACKS.get('immigration')
    if domain == 'mixed':
        # Prefer investment cards when both present (origin1-class); immigration needs explicit evidence elsewhere.
        pack = _CRITERIA_PACKS['investment']
    elif domain == 'generic':
        return []
    cards = pack.get(bucket) or pack.get('en') or ()
    return [dict(c) for c in cards]


def _steps_for_domain(domain: str, locale: str | None) -> dict[str, Any] | None:
    bucket = locale_bucket(locale)
    if domain == 'generic':
        return None
    key = 'investment' if domain in ('investment', 'mixed') else 'immigration'
    pack = _STEPS_PACKS[key]
    return dict(pack.get(bucket) or pack['en'])


def _query_is_immigration(query: Any) -> bool:
    q = ' '.join(query) if isinstance(query, (list, tuple)) else str(query or '')
    low = q.lower()
    return any(m in low for m in _IMMIGRATION_QUERY_MARKERS)


def _card_is_immigration(card: dict) -> bool:
    blob = f"{card.get('title', '')} {card.get('explanation', '')}".lower()
    return any(m in blob for m in _IMMIGRATION_CARD_MARKERS)


def _asset_is_immigration(blob: str) -> bool:
    low = (blob or '').lower()
    return any(m in low for m in _IMMIGRATION_ASSET_MARKERS)


def _concepts_for_scene(
    scene_id: str,
    semantic_map: dict[str, Any],
) -> list[dict[str, Any]]:
    prefs = _BEAT_CONCEPT_PREF.get(scene_id) or ()
    by_id = {}
    for hit in semantic_map.get('concepts') or []:
        by_id.setdefault(hit['conceptId'], hit)
    chosen = []
    for cid in prefs:
        if cid in by_id:
            chosen.append(by_id[cid])
    if not chosen:
        # Fall back to any concept in primary domain order.
        domain = semantic_map.get('primaryDomain')
        for hit in semantic_map.get('concepts') or []:
            if domain == 'mixed' or hit['domain'] == domain or hit['domain'] == 'generic':
                chosen.append(hit)
                if len(chosen) >= 2:
                    break
    return chosen


def _allowed_keyword_ids(semantic_map: dict[str, Any]) -> set[str]:
    allowed = set()
    for hit in semantic_map.get('concepts') or []:
        kw = hit.get('keyword')
        if kw:
            allowed.add(str(kw))
    # Always allow generic process keywords when spoken.
    for hit in semantic_map.get('concepts') or []:
        if hit['domain'] == 'generic' and hit.get('keyword'):
            allowed.add(str(hit['keyword']))
    domain = semantic_map.get('primaryDomain')
    if domain == 'investment':
        allowed -= _IMMIGRATION_KEYWORDS
    return allowed


def validate_semantic_alignment(plan: dict, semantic_map: dict[str, Any]) -> dict[str, Any]:
    """Reject visuals that lack transcript evidence for the active domain."""
    domain = semantic_map.get('primaryDomain')
    issues: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for scene in plan.get('scenes') or []:
        sid = scene.get('sceneId')
        query = scene.get('query')
        if query and _query_is_immigration(query) and domain == 'investment':
            issues.append({'sceneId': sid, 'type': 'query_mismatch', 'value': query})
            rejected.append({'sceneId': sid, 'reason': 'immigration_query_on_investment', 'query': query})
        cards = (scene.get('typography') or {}).get('cards') or []
        for card in cards:
            if _card_is_immigration(card) and domain == 'investment':
                issues.append({'sceneId': sid, 'type': 'card_mismatch', 'value': card})
                rejected.append({'sceneId': sid, 'reason': 'immigration_card_on_investment', 'card': card})
        sm = scene.get('semanticMotion') or {}
        blob = f"{sm.get('file', '')} {sm.get('keyword', '')} {sm.get('assetId', '')}"
        if _asset_is_immigration(blob) and domain == 'investment':
            issues.append({'sceneId': sid, 'type': 'motion_mismatch', 'value': blob})
            rejected.append({'sceneId': sid, 'reason': 'immigration_motion_on_investment', 'asset': blob})
        flo = ((scene.get('composition') or {}).get('floatObject') or {})
        fblob = f"{flo.get('file', '')} {flo.get('keyword', '')} {flo.get('silhouette', '')}"
        if _asset_is_immigration(fblob) and domain == 'investment':
            issues.append({'sceneId': sid, 'type': 'float_mismatch', 'value': fblob})
            rejected.append({'sceneId': sid, 'reason': 'immigration_float_on_investment', 'asset': fblob})
        # Accepted speech-backed concept stamps
        for c in (scene.get('semanticConcepts') or []):
            accepted.append({'sceneId': sid, 'conceptId': c.get('conceptId'), 'evidence': c.get('evidence')})

    # Hero passport on investment speech
    if domain == 'investment' and plan.get('heroObject') == 'passport':
        issues.append({'sceneId': 'plan', 'type': 'hero_mismatch', 'value': 'passport'})
        rejected.append({'sceneId': 'plan', 'reason': 'passport_hero_on_investment'})

    return {
        'ok': not issues,
        'primaryDomain': domain,
        'issueCount': len(issues),
        'issues': issues,
        'accepted': accepted,
        'rejected': rejected,
        'conceptIds': semantic_map.get('conceptIds') or [],
    }


def apply_semantic_intelligence(
    plan: dict,
    transcript: list | None = None,
    *,
    locale: str | None = None,
) -> dict:
    """Speech-first visual alignment. Call after V9, before premium 3D."""
    locale = locale or plan.get('language') or 'en-US'
    rows = transcript if transcript is not None else plan.get('transcript')
    semantic_map = build_semantic_map(rows, locale)
    domain = semantic_map['primaryDomain']
    allowed_kw = _allowed_keyword_ids(semantic_map)
    criteria = _criteria_for_domain(domain, locale)
    steps = _steps_for_domain(domain, locale)

    out = dict(plan)
    scenes_out: list[dict] = []
    asset_selection: list[dict[str, Any]] = []
    scrubbed: list[dict[str, Any]] = []

    for scene in out.get('scenes') or []:
        scene = dict(scene)
        sid = scene.get('sceneId') or ''
        concepts = _concepts_for_scene(sid, semantic_map)
        scene['semanticConcepts'] = [
            {
                'conceptId': c['conceptId'],
                'domain': c['domain'],
                'evidence': c.get('evidence'),
                'segmentId': c.get('segmentId'),
                'start': c.get('start'),
                'end': c.get('end'),
            }
            for c in concepts[:3]
        ]

        # Prefer evidence-backed queries; always scrub immigration queries off non-immigration speech.
        old_q = scene.get('query')
        new_q = concepts[0].get('query') if concepts else None
        must_scrub = bool(old_q) and _query_is_immigration(old_q) and domain != 'immigration'
        # Investment: replace beat defaults (document desk, consult stock) when speech has a concept.
        upgrade = bool(
            new_q and domain in ('investment', 'mixed')
            and (not old_q or must_scrub or _query_is_immigration(old_q)
                 or any(m in str(old_q).lower() for m in (
                     'document review', 'residence permit', 'paperwork',
                     'consultation meeting', 'phone consultation',
                 )))
        )
        if concepts and (not old_q or must_scrub or upgrade):
            if new_q and new_q != old_q:
                scrubbed.append({'sceneId': sid, 'field': 'query', 'from': old_q, 'to': new_q})
                scene['query'] = new_q
                bg = dict(scene.get('background') or {})
                for k in ('assetId', 'file', 'staged', 'conceptId'):
                    bg.pop(k, None)
                scene['background'] = bg
        elif must_scrub:
            scrubbed.append({'sceneId': sid, 'field': 'query', 'from': old_q, 'to': None})
            scene['query'] = None
            bg = dict(scene.get('background') or {})
            for k in ('assetId', 'file', 'staged', 'conceptId'):
                bg.pop(k, None)
            scene['background'] = bg

        # Criteria cards
        if sid == 'beside' and criteria:
            typ = dict(scene.get('typography') or {})
            old_cards = typ.get('cards') or []
            if any(_card_is_immigration(c) for c in old_cards) or not old_cards or domain in ('investment', 'mixed'):
                if any(_card_is_immigration(c) for c in old_cards):
                    scrubbed.append({'sceneId': sid, 'field': 'cards', 'from': old_cards, 'to': criteria})
                typ['cards'] = criteria
                typ['cardMode'] = typ.get('cardMode') or 'progressive_one'
                scene['typography'] = typ
                exe = dict(scene.get('execution') or {})
                exe['cardText'] = ' | '.join(c['title'] for c in criteria)
                exe['headline'] = criteria[0]['title']
                scene['execution'] = exe

        # Steps
        if sid == 'steps' and steps:
            typ = dict(scene.get('typography') or {})
            typ['stepsTitle'] = steps['title']
            typ['steps'] = list(steps['steps'])
            scene['typography'] = typ
            exe = dict(scene.get('execution') or {})
            exe['headline'] = steps['title']
            exe['cardText'] = ' → '.join(steps['steps'])
            scene['execution'] = exe

        # Strip immigration semantic motion / floats without evidence
        sm = dict(scene.get('semanticMotion') or {})
        if domain == 'investment':
            kw = str(sm.get('keyword') or '')
            blob = f"{sm.get('file', '')} {kw} {sm.get('assetId', '')}"
            if kw in _IMMIGRATION_KEYWORDS or _asset_is_immigration(blob):
                scrubbed.append({'sceneId': sid, 'field': 'semanticMotion', 'from': sm, 'to': None})
                scene['semanticMotion'] = {}
                shot = dict(scene.get('shotPlan') or {})
                shot.pop('semanticMotion', None)
                # Filter keywords on shot plan
                kws = []
                for k in shot.get('keywords') or []:
                    kid = k.get('id') if isinstance(k, dict) else k
                    if kid not in _IMMIGRATION_KEYWORDS:
                        kws.append(k)
                shot['keywords'] = kws
                if concepts:
                    shot['keywordPref'] = [c.get('keyword') for c in concepts if c.get('keyword')][:2]
                scene['shotPlan'] = shot
            comp = dict(scene.get('composition') or {})
            flo = dict(comp.get('floatObject') or {})
            fblob = f"{flo.get('file', '')} {flo.get('keyword', '')} {flo.get('silhouette', '')}"
            if flo and (flo.get('keyword') in _IMMIGRATION_KEYWORDS or _asset_is_immigration(fblob)):
                scrubbed.append({'sceneId': sid, 'field': 'floatObject', 'from': flo, 'to': None})
                comp['floatObject'] = None
                scene['composition'] = comp

        # Stamp evidence-backed keyword prefs for downstream bindings
        if concepts:
            shot = dict(scene.get('shotPlan') or {})
            prefs = [c.get('keyword') for c in concepts if c.get('keyword')]
            if prefs:
                shot['keywordPref'] = prefs[:2]
                # Ensure shot keywords include speech-backed ids
                existing = shot.get('keywords') or []
                existing_ids = {
                    (k.get('id') if isinstance(k, dict) else k) for k in existing
                }
                for p in prefs[:2]:
                    if p not in existing_ids and (domain != 'investment' or p not in _IMMIGRATION_KEYWORDS):
                        existing.append({'id': p, 'preset': 'speech_concept', 'match': 'v11'})
                        existing_ids.add(p)
                # Drop immigration keywords when investment-only
                if domain == 'investment':
                    existing = [
                        k for k in existing
                        if (k.get('id') if isinstance(k, dict) else k) not in _IMMIGRATION_KEYWORDS
                    ]
                shot['keywords'] = existing
            scene['shotPlan'] = shot

        if scene.get('query'):
            asset_selection.append({
                'sceneId': sid,
                'query': scene.get('query'),
                'conceptIds': [c['conceptId'] for c in concepts],
                'evidence': [c.get('evidence') for c in concepts],
                'domain': domain,
            })

        scenes_out.append(scene)

    if domain == 'investment' and out.get('heroObject') == 'passport':
        scrubbed.append({'sceneId': 'plan', 'field': 'heroObject', 'from': 'passport', 'to': None})
        out.pop('heroObject', None)

    out['scenes'] = scenes_out
    out['semanticMap'] = {
        'version': semantic_map['version'],
        'primaryDomain': domain,
        'domainScores': semantic_map['domainScores'],
        'conceptIds': semantic_map['conceptIds'],
        'segmentCount': len(semantic_map['segments']),
    }
    out['semanticIntelligence'] = {
        'version': 'v11',
        'primaryDomain': domain,
        'scrubbed': scrubbed,
        'allowedKeywords': sorted(allowed_kw),
        'criteriaTitles': [c['title'] for c in criteria],
    }
    validation = validate_semantic_alignment(out, semantic_map)
    out['semanticValidation'] = validation
    out['assetSelection'] = asset_selection
    # Keep full map on plan for artifact export (not huge).
    out['_semanticMapFull'] = semantic_map
    return out


def export_semantic_artifacts(plan: dict, out_dir) -> dict[str, str]:
    """Write semantic-map / asset-selection / semantic-validation JSON next to renders."""
    from pathlib import Path
    import json

    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    sm = plan.get('_semanticMapFull') or plan.get('semanticMap') or {}
    artifacts = {
        'semantic-map.json': sm,
        'asset-selection.json': {
            'primaryDomain': (plan.get('semanticIntelligence') or {}).get('primaryDomain'),
            'selections': plan.get('assetSelection') or [],
            'scrubbed': (plan.get('semanticIntelligence') or {}).get('scrubbed') or [],
        },
        'semantic-validation.json': plan.get('semanticValidation') or {},
    }
    written = {}
    for name, payload in artifacts.items():
        dest = path / name
        dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        written[name] = str(dest)
    return written
