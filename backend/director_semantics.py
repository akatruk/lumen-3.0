"""Speech-driven Director enrichment: headlines, cards, queries, layout diversity.

Does not invent facts. Headlines/cards come from transcript segments (complete ideas),
never from raw ultra-short caption crumbs.
"""
from __future__ import annotations

import re
from typing import Any

from .locale_consistency import locale_bucket, prefer_locale_field, text_matches_locale

# Keyword (any locale script) → English library search queries.
_QUERY_TRIGGERS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (re.compile(r'паспорт|passport|护照', re.I), (
        'passport document object', 'residence permit document',
    )),
    (re.compile(r'переезд|relocati|搬家|搬迁', re.I), (
        'family home doorway relocation', 'family new home arrival residence',
    )),
    (re.compile(r'документ|document|文件|заявлен', re.I), (
        'document review desk paperwork', 'residence permit application desk',
    )),
    (re.compile(r'консульт|consult|咨询', re.I), (
        'consultation meeting advisor', 'advisor client meeting trust',
    )),
    (re.compile(r'недвижим|property|квартир|housing|房产', re.I), (
        'apartment interior living room', 'condo exterior daytime',
    )),
    (re.compile(r'бюджет|budget|预算', re.I), (
        'budget planning desk paperwork',
    )),
)

_CRITERIA_RU = (
    {'title': 'Цели', 'explanation': 'куда и зачем вы переезжаете'},
    {'title': 'Семья', 'explanation': 'кто едет с вами и в какие сроки'},
    {'title': 'Бюджет', 'explanation': 'какой бюджет программы реалистичен'},
)
_CRITERIA_EN = (
    {'title': 'Goals', 'explanation': 'where you are going and why'},
    {'title': 'Family', 'explanation': 'who travels with you and when'},
    {'title': 'Budget', 'explanation': 'what the program can realistically cost'},
)
_CRITERIA_ZH = (
    {'title': '目标', 'explanation': '迁往哪里以及为何出发'},
    {'title': '家庭', 'explanation': '同行家人与时间安排'},
    {'title': '预算', 'explanation': '项目费用是否可承受'},
)

_STEPS_RU = {'title': 'Сопровождение', 'steps': ['Консультация', 'Программа', 'Документы']}
_STEPS_EN = {'title': 'Guided process', 'steps': ['Consult', 'Program', 'Documents']}
_STEPS_ZH = {'title': '全程陪同', 'steps': ['咨询', '方案', '文件']}

_LAYOUT_CYCLE = (
    'speaker_closeup',
    'speaker_split_right',
    'speaker_with_media',
    'speaker_split_left',
    'speaker_with_diagram',
    'speaker_fullscreen',
)


def _segment_texts(transcript: list | None, locale: str | None) -> list[dict]:
    rows = []
    for row in transcript or []:
        if hasattr(row, 'model_dump'):
            row = row.model_dump()
        if not isinstance(row, dict):
            continue
        text = prefer_locale_field(row, locale)
        if not text:
            continue
        try:
            start = float(row.get('start') or 0)
            end = float(row.get('end') or 0)
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        rows.append({'start': start, 'end': end, 'text': text, 'id': row.get('id')})
    return rows


def _headline_from(text: str, locale: str | None) -> str:
    """Short complete idea for kinetic type — not a mid-sentence crumb."""
    bucket = locale_bucket(locale)
    cleaned = ' '.join(text.split())
    if bucket == 'zh':
        return cleaned[:18]
    # Prefer first clause up to comma / question / ~8 words.
    parts = re.split(r'[,，?？!！;；:]', cleaned)
    clause = (parts[0] or cleaned).strip()
    words = clause.split()
    limit = 6 if bucket == 'ru' else 7
    if len(words) > limit:
        clause = ' '.join(words[:limit])
    return clause


def _criteria_for(locale: str | None, transcript_text: str) -> list[dict]:
    bucket = locale_bucket(locale)
    base = {'ru': _CRITERIA_RU, 'zh': _CRITERIA_ZH}.get(bucket, _CRITERIA_EN)
    cards = [dict(c) for c in base]
    # If speech names goals/family/budget, keep stock cards (already aligned).
    # If speech is about investment/China, still keep criteria that match immigration
    # consulting offers — do not invent new statistics.
    return cards


def _steps_for(locale: str | None) -> dict:
    bucket = locale_bucket(locale)
    return dict({'ru': _STEPS_RU, 'zh': _STEPS_ZH}.get(bucket, _STEPS_EN))


def _queries_from_text(text: str) -> list[str]:
    hits = []
    for pattern, queries in _QUERY_TRIGGERS:
        if pattern.search(text or ''):
            hits.extend(queries)
    return hits


def diversify_speaker_layouts(scenes: list[dict]) -> list[dict]:
    """Avoid identical framing for consecutive beats; keep V4 PIP floors intact."""
    out = []
    prev_framing = None
    cycle_i = 0
    for scene in scenes:
        scene = dict(scene)
        speaker = dict(scene.get('speaker') or {})
        layout = speaker.get('layout') or 'speaker_fullscreen'
        framing = speaker.get('framing') or 'fullscreen'
        kind = scene.get('semanticPurpose') or scene.get('sceneId')
        # Force hook close-up / punch for retention.
        if scene.get('sceneId') == 'hook' and layout not in (
            'speaker_closeup', 'speaker_punch_in', 'speaker_fullscreen', 'speaker_medium',
        ):
            layout = 'speaker_closeup'
            framing = 'fullscreen'
        # Consult: prefer media-forward with PIP, not another split.
        if scene.get('sceneId') == 'consult' and framing == prev_framing == 'split':
            layout = 'speaker_with_media'
            framing = 'pip'
        # Consecutive same framing → rotate.
        if framing == prev_framing:
            layout = _LAYOUT_CYCLE[cycle_i % len(_LAYOUT_CYCLE)]
            cycle_i += 1
            framing = (
                'fullscreen' if layout in (
                    'speaker_fullscreen', 'speaker_closeup', 'speaker_medium', 'speaker_punch_in',
                ) else 'split' if 'split' in layout else 'pip'
            )
        speaker['layout'] = layout
        speaker['treatment'] = layout
        speaker['framing'] = framing
        speaker['visibility'] = 'primary' if framing in ('fullscreen', 'split') else 'pip'
        scene['speaker'] = speaker
        execution = dict(scene.get('execution') or {})
        execution['speakerFraming'] = framing
        execution['speakerVisibility'] = speaker['visibility']
        scene['execution'] = execution
        out.append(scene)
        prev_framing = framing
        _ = kind
    return out


def enrich_plan_from_transcript(
    plan: dict,
    transcript: list | None,
    *,
    locale: str | None = None,
) -> dict:
    """Stamp speech-backed headlines/cards/queries; diversify layouts."""
    locale = locale or plan.get('language') or 'en-US'
    segments = _segment_texts(transcript, locale)
    scenes = [dict(s) for s in (plan.get('scenes') or [])]
    joined = ' '.join(s['text'] for s in segments)
    queries = _queries_from_text(joined)
    criteria = _criteria_for(locale, joined)
    steps = _steps_for(locale)

    # Map early segments onto fixed beat ids for 20s previews.
    by_id = {s.get('sceneId'): s for s in scenes}
    if 'hook' in by_id and segments:
        hook = by_id['hook']
        headline = _headline_from(segments[0]['text'], locale)
        typ = dict(hook.get('typography') or {})
        typ['headline'] = headline
        typ['treatment'] = typ.get('treatment') or 'phrase_reveal'
        typ['animate'] = 'pop'
        hook['typography'] = typ
        exe = dict(hook.get('execution') or {})
        exe['headline'] = headline
        exe['kineticReveal'] = True
        exe['captionMode'] = 'speech'
        hook['execution'] = exe
        hook['motionIntensity'] = 'high'
        sp = dict(hook.get('speaker') or {})
        sp['layout'] = 'speaker_closeup'
        sp['treatment'] = 'speaker_closeup'
        sp['framing'] = 'fullscreen'
        sp['visibility'] = 'primary'
        hook['speaker'] = sp

    if 'beside' in by_id:
        beside = by_id['beside']
        typ = dict(beside.get('typography') or {})
        typ['cards'] = criteria
        beside['typography'] = typ
        exe = dict(beside.get('execution') or {})
        exe['cardText'] = ' | '.join(c['title'] for c in criteria)
        exe['headline'] = criteria[0]['title'] if criteria else ''
        # Cards are structural — not transcript crumbs.
        exe['captionMode'] = 'speech'
        beside['execution'] = exe

    if 'steps' in by_id:
        step_scene = by_id['steps']
        typ = dict(step_scene.get('typography') or {})
        typ['stepsTitle'] = steps['title']
        typ['steps'] = list(steps['steps'])
        step_scene['typography'] = typ
        exe = dict(step_scene.get('execution') or {})
        exe['headline'] = steps['title']
        exe['cardText'] = ' → '.join(steps['steps'])
        step_scene['execution'] = exe

    if 'residency' in by_id and queries:
        res = by_id['residency']
        # Prefer relocation/document queries from speech.
        speech_q = [q for q in queries if 'reloc' in q or 'family' in q or 'document' in q or 'permit' in q]
        if speech_q:
            res['query'] = speech_q[0]
        exe = dict(res.get('execution') or {})
        if segments:
            exe['headline'] = _headline_from(segments[min(1, len(segments) - 1)]['text'], locale)
        res['execution'] = exe

    if 'consult' in by_id:
        consult = by_id['consult']
        consult_q = [q for q in queries if 'consult' in q or 'advisor' in q]
        if consult_q:
            consult['query'] = consult_q[0]
        exe = dict(consult.get('execution') or {})
        exe['mediaRole'] = 'supporting'
        consult['execution'] = exe

    # Preserve original scene order, then apply V7 shot plans (replaces ad-hoc diversify).
    order = [s.get('sceneId') for s in (plan.get('scenes') or [])]
    indexed = {s.get('sceneId'): s for s in by_id.values()} if by_id else {s.get('sceneId'): s for s in scenes}
    ordered = [indexed[i] for i in order if i in indexed]

    out = dict(plan)
    out['language'] = locale
    out['scenes'] = ordered
    out['semanticEnrichment'] = {
        'segmentCount': len(segments),
        'queryTriggers': queries[:6],
        'criteriaTitles': [c['title'] for c in criteria],
        'locale': locale,
    }
    from .director_shot_plan import apply_shot_plans
    out = apply_shot_plans(out, locale=locale, transcript_text=joined)
    # Hook hero: prefer passport/document object when speech mentions residency/passport.
    if any(k in joined.lower() for k in ('паспорт', 'жительств', 'passport', 'residenc')):
        out.setdefault('heroObject', 'passport')
    elif any(k in joined.lower() for k in ('переезд', 'reloc', '搬')):
        out.setdefault('heroObject', 'globe')
    # Reject plans where we could not get locale-matching speech at all.
    if transcript and not segments:
        out['localeGate'] = {
            'ok': False,
            'reason': 'transcript_locale_mismatch',
            'locale': locale,
        }
    else:
        out['localeGate'] = {'ok': True, 'locale': locale}
    return out


def motion_diversity_summary(scenes: list[dict]) -> dict[str, Any]:
    layouts = []
    backgrounds = []
    transitions = []
    for scene in scenes or []:
        layouts.append(((scene.get('speaker') or {}).get('layout')))
        backgrounds.append(((scene.get('background') or {}).get('treatment')))
        transitions.append(scene.get('transition'))
    consecutive_layout = sum(
        1 for i in range(1, len(layouts)) if layouts[i] and layouts[i] == layouts[i - 1]
    )
    return {
        'layouts': layouts,
        'uniqueLayouts': len(set(x for x in layouts if x)),
        'backgroundTreatments': backgrounds,
        'uniqueBackgrounds': len(set(x for x in backgrounds if x)),
        'transitions': transitions,
        'consecutiveLayoutRepeats': consecutive_layout,
        'pass': consecutive_layout == 0 and len(set(x for x in layouts if x)) >= 3,
    }


def validate_scene_semantics(plan: dict, locale: str | None = None) -> dict[str, Any]:
    """Light semantic gate before Remotion."""
    locale = locale or plan.get('language')
    issues = []
    for scene in plan.get('scenes') or []:
        exe = scene.get('execution') or {}
        headline = exe.get('headline') or (scene.get('typography') or {}).get('headline')
        if headline and not text_matches_locale(headline, locale):
            issues.append(f"{scene.get('sceneId')}:headline_locale")
        cards = (scene.get('typography') or {}).get('cards') or []
        for card in cards:
            for key in ('title', 'explanation'):
                if card.get(key) and not text_matches_locale(card[key], locale):
                    issues.append(f"{scene.get('sceneId')}:card_locale")
        # Transcript crumbs as cardText alone are invalid if they look like subtitle leftovers.
        card_text = str(exe.get('cardText') or '')
        if card_text and len(card_text.split()) <= 2 and locale_bucket(locale) != 'zh':
            # Short card titles like "Цели" are OK (single lexical item with capital).
            if card_text.islower():
                issues.append(f"{scene.get('sceneId')}:fragment_card")
    return {'ok': not issues, 'issues': issues}
