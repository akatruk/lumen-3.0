"""Director V11.1 — factual grounding + semantic business motion graphics.

Runs after V11 semantic intelligence. Requires source provenance for every
factual visual (numbers, %, legal/ownership claims). Binds Remotion
deterministic business motion presets — never invents percentages or counts.

Does not generate media. Does not hardcode Thailand-only rules into Remotion
components; Thailand facts appear only when the transcript states them.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .locale_consistency import locale_bucket, prefer_locale_field

# Spoken number words → int (locale-aware). Digits still win when present.
_WORD_NUMBERS: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r'\bthree\b|至少三|三名|三位|\bтри\b', re.I), 3),
    (re.compile(r'\btwo\b|两名|两位|\bдва\b', re.I), 2),
    (re.compile(r'\bfour\b|四名|四位|\bчетыре\b', re.I), 4),
    (re.compile(r'\bfive\b|五名|五位|\bпять\b', re.I), 5),
)

_PCT_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s*%')
_DIGIT_RE = re.compile(r'(?<![\d.])(\d{1,3})(?![\d.%])')

# Concept → Remotion business motion component id (generic, not country-locked).
_BUSINESS_MOTION_BINDINGS: dict[str, str] = {
    'thai_shareholder_count': 'shareholder_structure',
    'shareholder_responsibility': 'shareholder_structure',
    'thailand_company_structure': 'company_ownership',
    'foreign_ownership_ratio': 'equity_distribution',
    'capital_investment': 'capital_investment',
    'capital_flow': 'capital_flow',
    'capital_judgment': 'financial_comparison',
    'capital_return': 'investment_flow',
    'company_control': 'company_control',
    'deferred_payment': 'business_process',
    'government_leadership': 'business_process',
}

# Scene beat → preferred business motion when evidence exists.
_BEAT_MOTION_PREF: dict[str, tuple[str, ...]] = {
    'hook': ('capital_investment', 'company_ownership'),
    'context': ('capital_investment', 'investment_flow'),
    'problem': ('business_process', 'financial_comparison'),
    'residency': ('shareholder_structure', 'company_ownership'),
    'consult': ('financial_comparison', 'capital_investment'),
    'beside': ('shareholder_structure', 'equity_distribution', 'company_control'),
    'steps': ('business_process', 'company_control'),
    'proof': ('equity_distribution', 'company_ownership'),
    'payoff': ('company_control', 'investment_flow'),
    'return': ('investment_flow', 'financial_comparison'),
}

_LABELS: dict[str, dict[str, dict[str, Any]]] = {
    'shareholder_structure': {
        'en': {'title': 'Shareholders', 'node': 'Shareholder', 'minPrefix': '≥'},
        'ru': {'title': 'Акционеры', 'node': 'Акционер', 'minPrefix': '≥'},
        'zh': {'title': '股东', 'node': '股东', 'minPrefix': '≥'},
    },
    'equity_distribution': {
        'en': {'title': 'Foreign capital', 'local': 'Local', 'foreign': 'Foreign'},
        'ru': {'title': 'Иностранный капитал', 'local': 'Местный', 'foreign': 'Иностр.'},
        'zh': {'title': '外资比例', 'local': '本地', 'foreign': '外资'},
    },
    'capital_investment': {
        'en': {'title': 'Capital investment', 'from': 'Commit', 'to': 'Company'},
        'ru': {'title': 'Капитал', 'from': 'Вложение', 'to': 'Компания'},
        'zh': {'title': '资本投入', 'from': '出资', 'to': '公司'},
    },
    'capital_flow': {
        'en': {'title': 'Capital flow', 'from': 'Cap', 'via': 'Hold', 'to': 'Co'},
        'ru': {'title': 'Поток капитала', 'from': 'Кап', 'via': 'Холд', 'to': 'Ко'},
        'zh': {'title': '资本流转', 'from': '资本', 'via': '持股', 'to': '公司'},
    },
    'company_ownership': {
        'en': {'title': 'Ownership structure'},
        'ru': {'title': 'Структура владения'},
        'zh': {'title': '股权结构'},
    },
    'investment_flow': {
        'en': {'title': 'Capital rhythm', 'out': 'Deploy', 'back': 'Return'},
        'ru': {'title': 'Ритм капитала', 'out': 'Ввод', 'back': 'Возврат'},
        'zh': {'title': '出资节奏', 'out': '到位', 'back': '回流'},
    },
    'company_control': {
        'en': {'title': 'Control locked', 'lock': 'Control'},
        'ru': {'title': 'Контроль зафиксирован', 'lock': 'Контроль'},
        'zh': {'title': '控制权锁定', 'lock': '控制权'},
    },
    'financial_comparison': {
        'en': {'title': 'Capital judgment', 'left': 'Credit', 'right': 'Risk'},
        'ru': {'title': 'Оценка капитала', 'left': 'Кредит', 'right': 'Риск'},
        'zh': {'title': '资本判断', 'left': '信用', 'right': '风险'},
    },
    'business_process': {
        'en': {'title': 'Formation path', 'steps': ['Capital', 'Structure', 'Control']},
        'ru': {'title': 'Путь создания', 'steps': ['Капитал', 'Структура', 'Контроль']},
        'zh': {'title': '设立路径', 'steps': ['资本', '结构', '控制权']},
    },
}


def extract_spoken_facts(text: str) -> dict[str, Any]:
    """Parse numbers/percentages the source actually stated. Never invent."""
    facts: dict[str, Any] = {'raw': text, 'percentages': [], 'counts': [], 'wordCounts': []}
    if not text:
        return facts
    for m in _PCT_RE.finditer(text):
        try:
            facts['percentages'].append(float(m.group(1).replace(',', '.')))
        except ValueError:
            pass
    for m in _DIGIT_RE.finditer(text):
        try:
            n = int(m.group(1))
            if 1 <= n <= 99:
                facts['counts'].append(n)
        except ValueError:
            pass
    for pat, value in _WORD_NUMBERS:
        if pat.search(text):
            facts['wordCounts'].append(value)
    return facts


def shareholder_count_from_text(text: str) -> int | None:
    """Return spoken shareholder count only when the line states one."""
    low = text or ''
    if not re.search(r'shareholder|акционер|股东', low, re.I):
        # Still allow bare "at least three" near company formation phrasing.
        if not re.search(r'compan|компани|公司|limited|обществ', low, re.I):
            return None
    facts = extract_spoken_facts(low)
    # Prefer word counts tied to shareholders ("three shareholders", "三名股东").
    if facts['wordCounts']:
        return facts['wordCounts'][0]
    if facts['counts']:
        return facts['counts'][0]
    return None


def ownership_ratio_from_text(text: str) -> float | None:
    facts = extract_spoken_facts(text or '')
    if facts['percentages']:
        return facts['percentages'][0]
    return None


def _labels_for(component: str, locale: str | None) -> dict[str, Any]:
    bucket = locale_bucket(locale)
    pack = _LABELS.get(component) or {}
    return dict(pack.get(bucket) or pack.get('en') or {})


def _provenance(hit: dict[str, Any]) -> dict[str, Any]:
    return {
        'sourceSegmentId': hit.get('segmentId'),
        'sourceStart': hit.get('start'),
        'sourceEnd': hit.get('end'),
        'originalSourceText': hit.get('evidence'),
    }


def _claim_ok(component: str, payload: dict[str, Any], evidence: str) -> tuple[bool, str | None]:
    """Fail closed on numbers/legal claims without transcript evidence."""
    if component == 'shareholder_structure' and payload.get('showCount'):
        count = payload.get('nodeCount')
        spoken = shareholder_count_from_text(evidence)
        if count is None or spoken is None:
            return False, 'shareholder_count_without_evidence'
        if int(count) != int(spoken):
            return False, f'shareholder_count_mismatch:{count}!={spoken}'
    if component == 'equity_distribution':
        ratio = payload.get('foreignRatio')
        if ratio is not None:
            spoken = ownership_ratio_from_text(evidence)
            if spoken is None:
                return False, 'ownership_ratio_without_evidence'
            if abs(float(ratio) - float(spoken)) > 0.01:
                return False, f'ownership_ratio_mismatch:{ratio}!={spoken}'
    # Reject invented default "2" whenever a count is shown.
    if (
        payload.get('showCount')
        and payload.get('nodeCount') == 2
        and shareholder_count_from_text(evidence) != 2
    ):
        return False, 'invented_two_shareholders'
    return True, None


def build_business_motion(
    concept_hit: dict[str, Any],
    *,
    locale: str | None,
    component: str | None = None,
) -> dict[str, Any] | None:
    """Build a provenance-stamped business motion payload from one concept hit."""
    cid = concept_hit.get('conceptId') or ''
    component = component or _BUSINESS_MOTION_BINDINGS.get(cid)
    if not component:
        return None
    evidence = str(concept_hit.get('evidence') or '')
    labels = _labels_for(component, locale)
    payload: dict[str, Any] = {
        'component': component,
        'conceptId': cid,
        'labels': labels,
        **_provenance(concept_hit),
    }
    if component == 'shareholder_structure':
        count = shareholder_count_from_text(evidence)
        if count is not None:
            payload['nodeCount'] = count
            payload['topologyNodes'] = count
            payload['showCount'] = True
            payload['countLabel'] = f"{labels.get('minPrefix', '≥')}{count}"
        else:
            # Anonymous ownership nodes — no numeral on screen.
            payload['topologyNodes'] = 3
            payload['showCount'] = False
            payload.pop('nodeCount', None)
    elif component == 'equity_distribution':
        ratio = ownership_ratio_from_text(evidence)
        if ratio is None:
            return None  # never draw a fake %
        payload['foreignRatio'] = ratio
        payload['localRatio'] = max(0.0, 100.0 - float(ratio))
        payload['ratioLabel'] = f'{int(ratio) if float(ratio).is_integer() else ratio}%'
    elif component == 'business_process':
        payload['steps'] = list(labels.get('steps') or ['Capital', 'Structure', 'Control'])

    ok, reason = _claim_ok(component, payload, evidence)
    if not ok:
        return None
    payload['evidenceOk'] = True
    payload['gate'] = reason
    return payload


def validate_factual_grounding(plan: dict) -> dict[str, Any]:
    """Quality gate: unsupported numbers / invented legal claims / contradicting cards."""
    issues: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for scene in plan.get('scenes') or []:
        sid = scene.get('sceneId')
        bm = scene.get('businessMotion') or {}
        if not bm:
            continue
        evidence = str(bm.get('originalSourceText') or '')
        prov = all(bm.get(k) is not None for k in (
            'sourceSegmentId', 'sourceStart', 'sourceEnd', 'originalSourceText',
        ))
        if not prov:
            issues.append({'sceneId': sid, 'type': 'missing_provenance', 'component': bm.get('component')})
        ok, reason = _claim_ok(str(bm.get('component') or ''), bm, evidence)
        if not ok:
            issues.append({'sceneId': sid, 'type': 'unsupported_claim', 'reason': reason, 'component': bm.get('component')})
        else:
            accepted.append({
                'sceneId': sid,
                'component': bm.get('component'),
                'sourceSegmentId': bm.get('sourceSegmentId'),
                'originalSourceText': evidence,
                'nodeCount': bm.get('nodeCount') if bm.get('showCount') else None,
                'foreignRatio': bm.get('foreignRatio'),
            })
        # Contradicting card text vs spoken count
        for card in (scene.get('typography') or {}).get('cards') or []:
            blob = f"{card.get('title', '')} {card.get('explanation', '')}"
            if re.search(r'\b2\s+shareholders?\b|two shareholders|两名股东', blob, re.I):
                spoken = shareholder_count_from_text(evidence) if evidence else None
                if spoken != 2:
                    issues.append({
                        'sceneId': sid,
                        'type': 'contradicting_card',
                        'value': blob,
                        'spoken': spoken,
                    })
    return {
        'ok': not issues,
        'issueCount': len(issues),
        'issues': issues,
        'accepted': accepted,
        'version': 'v11.1',
    }


def apply_factual_business_motion(
    plan: dict,
    transcript: list | None = None,
    *,
    locale: str | None = None,
) -> dict:
    """Stamp evidence-backed businessMotion on scenes; strip unsupported claims."""
    locale = locale or plan.get('language') or 'en-US'
    semantic = plan.get('_semanticMapFull') or plan.get('semanticMap') or {}
    concepts = list(semantic.get('concepts') or [])
    if not concepts and transcript:
        from .director_v11 import build_semantic_map
        semantic = build_semantic_map(transcript, locale)
        concepts = list(semantic.get('concepts') or [])

    by_id: dict[str, dict[str, Any]] = {}
    for hit in concepts:
        by_id.setdefault(hit['conceptId'], hit)

    out = dict(plan)
    scenes_out: list[dict] = []
    usage: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for scene in out.get('scenes') or []:
        scene = dict(scene)
        sid = scene.get('sceneId') or ''
        prefs = _BEAT_MOTION_PREF.get(sid) or ()
        candidates: list[dict[str, Any]] = []
        # Scene-stamped concepts first, then beat preference order.
        seen_comp: set[str] = set()
        ordered_hits: list[tuple[str, dict[str, Any]]] = []
        for c in scene.get('semanticConcepts') or []:
            cid = c.get('conceptId')
            hit = by_id.get(cid) or c
            comp = _BUSINESS_MOTION_BINDINGS.get(cid or '')
            if comp:
                ordered_hits.append((comp, hit))
        for pref_comp in prefs:
            for cid, comp in _BUSINESS_MOTION_BINDINGS.items():
                if comp != pref_comp:
                    continue
                hit = by_id.get(cid)
                if hit:
                    ordered_hits.append((comp, hit))
        for comp, hit in ordered_hits:
            if comp in seen_comp:
                continue
            built = build_business_motion(hit, locale=locale, component=comp)
            if not built:
                continue
            seen_comp.add(comp)
            candidates.append(built)
        # Prefer evidenced numerals over generic topology; then beat preference order.
        pref_list = list(prefs)

        def _rank(m: dict[str, Any]) -> tuple[int, int]:
            hard = 1 if (m.get('foreignRatio') is not None or m.get('showCount')) else 0
            try:
                pref_score = len(pref_list) - pref_list.index(m.get('component'))
            except ValueError:
                pref_score = 0
            return (hard, pref_score)

        chosen = max(candidates, key=_rank) if candidates else None
        # Also stamp evidenced shareholder count onto beside cards even if
        # another hard-fact motion won the primary overlay slot.
        if sid == 'beside':
            count_motion = next(
                (m for m in candidates if m.get('component') == 'shareholder_structure' and m.get('showCount')),
                None,
            )
            if count_motion and (not chosen or chosen.get('component') != 'shareholder_structure'):
                # Keep primary overlay as ranked, but use count_motion for card enrichment below.
                scene['_shareholderCardMotion'] = count_motion
            elif chosen and chosen.get('component') == 'shareholder_structure':
                scene['_shareholderCardMotion'] = chosen

        if chosen:
            scene['businessMotion'] = chosen
            # Enrich criteria card when count is evidenced — never invent "2".
            card_src = scene.pop('_shareholderCardMotion', None) or (
                chosen if chosen.get('component') == 'shareholder_structure' and chosen.get('showCount') else None
            )
            if sid == 'beside' and card_src and card_src.get('showCount') and card_src.get('nodeCount'):
                typ = dict(scene.get('typography') or {})
                cards = [dict(c) for c in (typ.get('cards') or [])]
                for card in cards:
                    title = str(card.get('title') or '')
                    if re.search(r'shareholder|акционер|股东', title, re.I):
                        n = int(card_src['nodeCount'])
                        # Localized title keeps numeral identical across locales.
                        if locale_bucket(locale) == 'zh':
                            card['title'] = f'≥{n}名股东'
                        elif locale_bucket(locale) == 'ru':
                            card['title'] = f'≥{n} акционеров'
                        else:
                            card['title'] = f'≥{n} Shareholders'
                        card['explanation'] = card_src.get('originalSourceText') or card.get('explanation')
                        card['sourceSegmentId'] = card_src.get('sourceSegmentId')
                        card['originalSourceText'] = card_src.get('originalSourceText')
                if cards:
                    typ['cards'] = cards
                    scene['typography'] = typ
                # Prefer shareholder diagram on beside when count is spoken.
                if card_src.get('component') == 'shareholder_structure':
                    scene['businessMotion'] = card_src
                    chosen = card_src
            usage.append({
                'sceneId': sid,
                'component': chosen['component'],
                'conceptId': chosen.get('conceptId'),
                'sourceSegmentId': chosen.get('sourceSegmentId'),
                'sourceStart': chosen.get('sourceStart'),
                'sourceEnd': chosen.get('sourceEnd'),
                'originalSourceText': chosen.get('originalSourceText'),
                'showCount': chosen.get('showCount'),
                'nodeCount': chosen.get('nodeCount') if chosen.get('showCount') else None,
                'foreignRatio': chosen.get('foreignRatio'),
            })
        else:
            scene.pop('businessMotion', None)
            scene.pop('_shareholderCardMotion', None)

        scenes_out.append(scene)

    out['scenes'] = scenes_out
    validation = validate_factual_grounding(out)
    # Strip any motion that failed the gate.
    if not validation['ok']:
        fixed_scenes = []
        bad_ids = {i['sceneId'] for i in validation['issues']}
        for scene in scenes_out:
            scene = dict(scene)
            if scene.get('sceneId') in bad_ids and scene.get('businessMotion'):
                rejected.append({
                    'sceneId': scene.get('sceneId'),
                    'from': scene.get('businessMotion'),
                    'reason': 'factual_gate',
                })
                scene.pop('businessMotion', None)
            fixed_scenes.append(scene)
        out['scenes'] = fixed_scenes
        validation = validate_factual_grounding(out)

    out['factualGrounding'] = validation
    out['businessMotionUsage'] = usage
    out['businessMotionRejected'] = rejected
    out['factualVersion'] = 'v11.1'
    # Soft-enable concept overlays for evidence-backed business motion even under V9 clean.
    # Remotion mounts businessMotion from the scene look; concept stack stays off.
    out['businessMotionEnabled'] = True
    return out


def export_factual_artifacts(plan: dict, out_dir) -> dict[str, str]:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    written = {}
    payloads = {
        'source-fact-validation.json': {
            'version': 'v11.1',
            'factualGrounding': plan.get('factualGrounding') or {},
            'shareholderFinding': _shareholder_finding(plan),
            'rejected': plan.get('businessMotionRejected') or [],
        },
        'business-motion-usage.json': {
            'version': 'v11.1',
            'enabled': plan.get('businessMotionEnabled'),
            'usage': plan.get('businessMotionUsage') or [],
        },
    }
    for name, payload in payloads.items():
        dest = path / name
        dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        written[name] = str(dest)
    return written


def _shareholder_finding(plan: dict) -> dict[str, Any]:
    for row in plan.get('businessMotionUsage') or []:
        if row.get('component') == 'shareholder_structure' and row.get('nodeCount'):
            return {
                'spokenCount': row.get('nodeCount'),
                'sourceSegmentId': row.get('sourceSegmentId'),
                'sourceStart': row.get('sourceStart'),
                'sourceEnd': row.get('sourceEnd'),
                'originalSourceText': row.get('originalSourceText'),
                'verdict': 'at_least_three' if row.get('nodeCount') == 3 else f"count_{row.get('nodeCount')}",
                'rejectedInventedTwo': True,
            }
    # Fall back: scan semantic map
    sm = plan.get('_semanticMapFull') or {}
    for hit in sm.get('concepts') or []:
        n = shareholder_count_from_text(str(hit.get('evidence') or ''))
        if n:
            return {
                'spokenCount': n,
                'sourceSegmentId': hit.get('segmentId'),
                'sourceStart': hit.get('start'),
                'sourceEnd': hit.get('end'),
                'originalSourceText': hit.get('evidence'),
                'verdict': 'at_least_three' if n == 3 else f'count_{n}',
                'rejectedInventedTwo': True,
            }
    return {
        'spokenCount': None,
        'verdict': 'no_count_in_transcript',
        'rejectedInventedTwo': True,
        'note': 'Do not render a shareholder headcount without spoken evidence',
    }
