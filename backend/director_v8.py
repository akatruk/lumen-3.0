"""Director V8 — 60s semantic motion activation + long-form beat expansion.

Expands the 6-beat V7 template into a 10-beat narrative for ≥45s renders,
binds premium motion clips to spoken concepts, and filters non-locale speech.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .director_shot_plan import apply_shot_plans, extract_keywords, motion_usage_report
from .locale_consistency import text_matches_locale, prefer_locale_field

# Premium / library motion files that Remotion can stage under director-v3/picked/.
MOTION_BINDINGS: tuple[tuple[str, str, str], ...] = (
    # keyword id, asset relative file under media/library/out, motion family
    ('relocation', 'motion/premium/pm_scene_mobility_001.webm', 'mobility'),
    ('residency', 'motion/documents/document_approval_001.webm', 'document'),
    ('documents', 'motion/premium/pm_concept_folder_001.webm', 'folder'),
    ('program', 'motion/premium/pm_hero_steps_001.webm', 'steps'),
    ('consult', 'motion/premium/pm_hero_compare_001.webm', 'compare'),
    ('family', 'motion/premium/pm_concept_shield_001.webm', 'shield'),
    ('budget', 'motion/premium/pm_hero_deadline_001.webm', 'deadline'),
    ('goals', 'motion/conceptual/target_hit_001.webm', 'target'),
    ('passport', 'motion/premium/pm_scene_approval_001.webm', 'approval'),
)

# 10-beat long-form structure (weights sum ≈ 1800 @ 60s / 30fps).
LONG_BEATS: tuple[dict[str, Any], ...] = (
    {
        'id': 'hook', 'intent': 'hook', 'kind': 'speaker', 'base': 'high',
        'representation': 'presenter',
        'speakerLayout': 'speaker_punch_in', 'framing': 'fullscreen',
        'backgroundTreatment': 'slow_zoom_in', 'motionFamily': 'camera+kinetic',
        'transition': 'cut', 'cardMode': 'none', 'weight': 90,
        'keywordPref': ('relocation', 'residency'),
        'query': None,
    },
    {
        'id': 'context', 'intent': 'context', 'kind': 'speaker_object', 'base': 'high',
        'representation': 'photo+presenter',
        'speakerLayout': 'speaker_with_foreground', 'framing': 'split',
        'backgroundTreatment': 'mask_reveal', 'motionFamily': 'media+route',
        'transition': 'crossfade', 'cardMode': 'none', 'weight': 180,
        'keywordPref': ('relocation',),
        'query': ('family home doorway relocation', 'family new home arrival residence'),
    },
    {
        'id': 'problem', 'intent': 'tension', 'kind': 'speaker', 'base': 'medium',
        'representation': 'presenter',
        'speakerLayout': 'speaker_closeup', 'framing': 'fullscreen',
        'backgroundTreatment': 'subtle_drift', 'motionFamily': 'camera+kinetic',
        'transition': 'cut', 'cardMode': 'none', 'weight': 210,
        'keywordPref': ('residency', 'passport'),
        'query': None,
    },
    {
        'id': 'residency', 'intent': 'document', 'kind': 'speaker_object', 'base': 'medium',
        'representation': 'photo+presenter',
        'speakerLayout': 'speaker_split_right', 'framing': 'split',
        'backgroundTreatment': 'parallax_depth', 'motionFamily': 'media+document',
        'transition': 'cut', 'cardMode': 'none', 'weight': 300,
        'keywordPref': ('program', 'documents'),
        'query': ('document review desk paperwork', 'residence permit application desk'),
    },
    {
        'id': 'consult', 'intent': 'proof', 'kind': 'broll', 'base': 'medium',
        'representation': 'photo',
        'speakerLayout': 'speaker_with_media', 'framing': 'pip',
        'backgroundTreatment': 'ambient_loop', 'motionFamily': 'broll',
        'transition': 'cut', 'cardMode': 'none', 'weight': 240,
        'keywordPref': ('consult',),
        'query': ('consultation meeting advisor', 'advisor client meeting trust'),
    },
    {
        'id': 'beside', 'intent': 'criteria', 'kind': 'speaker_text', 'base': 'medium',
        'representation': 'typography+presenter',
        'speakerLayout': 'speaker_split_left', 'framing': 'split',
        'backgroundTreatment': 'static_editorial', 'motionFamily': 'info_reveal',
        'transition': 'cut', 'cardMode': 'progressive_one', 'weight': 180,
        'keywordPref': ('goals', 'family', 'budget'),
        'query': None,
    },
    {
        'id': 'steps', 'intent': 'process', 'kind': 'infographic', 'base': 'low',
        'representation': 'diagram',
        'speakerLayout': 'speaker_with_diagram', 'framing': 'pip',
        'backgroundTreatment': 'gradient_reveal', 'motionFamily': 'infographic',
        'transition': 'cut', 'cardMode': 'none', 'weight': 150,
        'keywordPref': ('program', 'documents'),
        'query': None,
    },
    {
        'id': 'proof', 'intent': 'example', 'kind': 'broll', 'base': 'medium',
        'representation': 'photo',
        'speakerLayout': 'speaker_with_media', 'framing': 'pip',
        'backgroundTreatment': 'slow_zoom_in', 'motionFamily': 'broll+object',
        'transition': 'crossfade', 'cardMode': 'none', 'weight': 180,
        'keywordPref': ('documents', 'program'),
        'query': ('phone consultation office advisor', 'document review desk paperwork'),
    },
    {
        'id': 'payoff', 'intent': 'payoff', 'kind': 'speaker', 'base': 'medium',
        'representation': 'presenter',
        'speakerLayout': 'speaker_medium', 'framing': 'fullscreen',
        'backgroundTreatment': 'slow_zoom_out', 'motionFamily': 'camera',
        'transition': 'cut', 'cardMode': 'none', 'weight': 150,
        'keywordPref': (),  # speaker-led payoff — no competing motion plate
        'query': None,
    },
    {
        'id': 'return', 'intent': 'cta', 'kind': 'speaker', 'base': 'low',
        'representation': 'presenter',
        'speakerLayout': 'speaker_fullscreen', 'framing': 'fullscreen',
        'backgroundTreatment': 'static_editorial', 'motionFamily': 'camera',
        'transition': 'crossfade', 'cardMode': 'none', 'weight': 120,
        'keywordPref': (),
        'query': None,
    },
)

# V7 short-form beat IDs kept for ≤40s
SHORT_IDS = ('hook', 'residency', 'consult', 'beside', 'steps', 'return')


def filter_locale_transcript(transcript: list | None, locale: str | None) -> list[dict]:
    """Drop rows whose text does not match the viewer locale (e.g. EN glitch in RU source)."""
    rows = []
    for row in transcript or []:
        if hasattr(row, 'model_dump'):
            row = row.model_dump()
        if not isinstance(row, dict):
            continue
        text = prefer_locale_field(row, locale)
        if not text:
            # Also try raw text field from localization sidecar
            text = ' '.join(str(row.get('text') or '').split())
            if text and not text_matches_locale(text, locale):
                continue
            if not text:
                continue
        if not text_matches_locale(text, locale):
            continue
        out = dict(row)
        bucket = (locale or 'en').lower()
        if bucket.startswith('ru'):
            out['ru'] = text
            out['original'] = text
        elif bucket.startswith('zh'):
            out['zh'] = text
            out['original'] = text
        else:
            out['en'] = text
            out['original'] = text
        rows.append(out)
    return rows


def _binding_for(keyword_ids: list[str]) -> dict[str, str] | None:
    for kid, rel, family in MOTION_BINDINGS:
        if kid in keyword_ids:
            return {'assetId': Path(rel).stem, 'file': rel, 'motionFamily': family, 'keyword': kid}
    return None


def _scene_from_beat(beat: dict, *, keywords: list[dict], seed_layout: dict | None = None) -> dict:
    pref = list(beat.get('keywordPref') or ())
    kid_list = [k['id'] for k in keywords if k['id'] in pref] or [k['id'] for k in keywords[:1]]
    motion = _binding_for(kid_list)
    query = beat.get('query')
    if isinstance(query, tuple):
        query = query[0]
    layout = beat['speakerLayout']
    framing = beat['framing']
    return {
        'sceneId': beat['id'],
        'semanticPurpose': beat['intent'],
        'query': query,
        'representation': beat['representation'],
        'speaker': {
            'layout': layout,
            'treatment': layout,
            'framing': framing,
            'visibility': 'primary' if framing in ('fullscreen', 'split') else 'pip',
        },
        'background': {
            'assetId': (seed_layout or {}).get('background', {}).get('assetId'),
            'file': (seed_layout or {}).get('background', {}).get('file'),
            'treatment': beat['backgroundTreatment'],
        },
        'foreground': {
            'treatment': 'scale_reveal' if motion else 'reveal_and_hold',
            'assetId': None,
            'file': None,
        },
        'typography': {
            'treatment': 'phrase_reveal',
            'animate': 'pop' if beat['id'] in ('hook', 'problem') else 'fade',
            'cardMode': beat.get('cardMode') or 'none',
        },
        'execution': {
            'scenePurpose': beat['intent'],
            'speakerFraming': framing,
            'speakerVisibility': 'primary' if framing in ('fullscreen', 'split') else 'pip',
            'mediaRole': 'supporting' if query or motion else 'none',
            'captionMode': 'speech',
            'motionPreset': beat['motionFamily'],
            'cardMode': beat.get('cardMode') or 'none',
        },
        'transition': beat['transition'],
        'motionIntensity': 'high' if beat['base'] == 'high' else 'medium' if beat['base'] == 'medium' else 'low',
        'semanticMotion': motion,
        'shotPlan': {
            'narrativePurpose': beat['intent'],
            'speakerLayout': layout,
            'speakerFraming': framing,
            'motionFamily': beat['motionFamily'],
            'cardMode': beat.get('cardMode') or 'none',
            'backgroundTreatment': beat['backgroundTreatment'],
            'transition': beat['transition'],
            'keywords': [k for k in keywords if k['id'] in kid_list][:2],
            'semanticMotion': motion,
            'weight': beat['weight'],
            'choreography': [
                {'at': 0.0, 'action': 'establish'},
                {'at': 0.25, 'action': 'motion_enter' if motion else 'hold'},
                {'at': 0.55, 'action': 'emphasis'},
                {'at': 0.85, 'action': 'exit_prepare'},
            ],
        },
    }


def _topic_aware_beat(beat: dict, *, domain: str, keywords: list[dict]) -> dict:
    """Strip hardcoded immigration prefs/queries when speech is not immigration."""
    beat = dict(beat)
    if domain not in ('investment', 'mixed'):
        return beat
    # Investment / mixed: never force relocation/residency defaults.
    imm_prefs = {'relocation', 'residency', 'passport', 'family'}
    pref = tuple(p for p in (beat.get('keywordPref') or ()) if p not in imm_prefs)
    # Prefer speech-backed corporate keywords when available.
    speech_ids = [k['id'] for k in keywords if k['id'] not in imm_prefs]
    corp = [k for k in speech_ids if k in (
        'investment', 'shareholder', 'capital', 'thailand', 'ownership', 'control',
        'documents', 'consult', 'program', 'budget', 'goals',
    )]
    if not pref:
        pref = tuple(corp[:2]) if corp else ()
    beat['keywordPref'] = pref
    query = beat.get('query')
    if isinstance(query, tuple):
        q0 = query[0] if query else None
    else:
        q0 = query
    if q0 and any(m in str(q0).lower() for m in (
        'relocation', 'residence permit', 'passport', 'family home', 'family new home',
        'document review desk', 'application desk',
    )):
        beat['query'] = None
    return beat


def expand_plan_for_duration(
    plan: dict,
    *,
    duration_seconds: int,
    transcript: list | None = None,
    locale: str | None = None,
) -> dict:
    """For ≥45s builds a 10-beat narrative; shorter keeps existing V7 scenes."""
    locale = locale or plan.get('language') or 'ru-RU'
    cleaned = filter_locale_transcript(transcript, locale)
    joined = ' '.join(prefer_locale_field(r, locale) or r.get('text') or '' for r in cleaned)
    keywords = extract_keywords(joined, locale)
    try:
        from .director_v11 import detect_topic_domain
        domain = detect_topic_domain(cleaned, locale)
    except Exception:
        domain = 'immigration'  # legacy default only if v11 unavailable

    out = dict(plan)
    out['language'] = locale
    out['durationSeconds'] = float(duration_seconds)
    out['keywords'] = keywords
    out['topicDomain'] = domain

    if float(duration_seconds) < 45:
        out['form'] = 'short'
        # Still stamp semantic motion onto existing scenes.
        scenes = []
        for scene in out.get('scenes') or []:
            scene = dict(scene)
            shot = dict(scene.get('shotPlan') or {})
            prefs = [k['id'] for k in (shot.get('keywords') or keywords[:1])]
            if domain == 'investment':
                prefs = [p for p in prefs if p not in ('relocation', 'residency', 'passport', 'family')]
            motion = _binding_for(prefs) or (
                None if domain == 'investment' else _binding_for([k['id'] for k in keywords])
            )
            if motion and domain == 'investment' and motion.get('keyword') in (
                'relocation', 'residency', 'passport', 'family',
            ):
                motion = None
            if motion:
                scene['semanticMotion'] = motion
                shot['semanticMotion'] = motion
                scene['shotPlan'] = shot
            scenes.append(scene)
        out['scenes'] = scenes
        out = apply_shot_plans(out, locale=locale, transcript_text=joined)
        out['motionUsage'] = motion_usage_report(out)
        return out

    out['form'] = 'long60'
    # Seed media from prior short scenes when present.
    by_old = {s.get('sceneId'): s for s in (plan.get('scenes') or [])}
    scenes = []
    for beat in LONG_BEATS:
        beat = _topic_aware_beat(beat, domain=domain, keywords=keywords)
        # Only reuse media from the same beat id — never clone one interior across the minute.
        seed = by_old.get(beat['id'])
        scene = _scene_from_beat(beat, keywords=keywords, seed_layout=seed)
        # Carry criteria/steps from prior enrichment when present.
        if beat['id'] == 'beside' and by_old.get('beside'):
            typ = dict(by_old['beside'].get('typography') or {})
            if typ.get('cards'):
                scene['typography'] = {**scene['typography'], 'cards': typ['cards'], 'cardMode': 'progressive_one'}
        if beat['id'] == 'steps' and by_old.get('steps'):
            typ = dict(by_old['steps'].get('typography') or {})
            scene['typography'] = {
                **scene['typography'],
                'stepsTitle': typ.get('stepsTitle'),
                'steps': typ.get('steps'),
            }
        if beat['id'] == 'hook':
            scene['typography']['animate'] = 'pop'
            scene['execution']['kineticReveal'] = True
            if cleaned:
                from .director_semantics import _headline_from
                headline = _headline_from(
                    prefer_locale_field(cleaned[0], locale) or cleaned[0].get('text') or '',
                    locale,
                )
                scene['typography']['headline'] = headline
                scene['execution']['headline'] = headline
                scene['headline'] = headline
            elif by_old.get('hook'):
                old_typ = by_old['hook'].get('typography') or {}
                if old_typ.get('headline'):
                    scene['typography']['headline'] = old_typ['headline']
                    scene['execution']['headline'] = old_typ['headline']
                    scene['headline'] = old_typ['headline']
        scenes.append(scene)

    out['scenes'] = scenes
    out['shotPlanVersion'] = 'v8'
    out['beatWeights'] = [b['weight'] for b in LONG_BEATS]
    # Hero for opener — immigration objects only when speech is immigration-domain.
    if domain != 'investment':
        if any(k['id'] in ('residency', 'passport', 'documents') for k in keywords):
            out['heroObject'] = 'passport'
        elif any(k['id'] == 'relocation' for k in keywords):
            out['heroObject'] = 'globe'
    else:
        out.pop('heroObject', None)
    out['antiRepetition'] = {
        'signatures': [
            f"{s['speaker']['framing']}|{s['speaker']['layout']}|{(s.get('shotPlan') or {}).get('motionFamily')}"
            for s in scenes
        ],
        'maxSplitStreak': _max_streak([s['speaker']['framing'] == 'split' for s in scenes]),
        'pass': _max_streak([s['speaker']['framing'] == 'split' for s in scenes]) < 3,
    }
    out['motionUsage'] = motion_usage_report(out)
    # Count semantic motion bindings that resolve to real files.
    library = Path(__file__).resolve().parent.parent / 'media' / 'library' / 'out'
    resolved = []
    missing = []
    for s in scenes:
        sm = s.get('semanticMotion') or {}
        rel = sm.get('file')
        if not rel:
            continue
        path = library / rel
        if path.is_file():
            resolved.append({'sceneId': s['sceneId'], **sm})
        else:
            missing.append({'sceneId': s['sceneId'], **sm})
    out['semanticMotionAudit'] = {
        'resolved': resolved,
        'missing': missing,
        'resolvedCount': len(resolved),
        'pass': len(resolved) >= 3,
    }
    return out


def _max_streak(flags: list[bool]) -> int:
    best = cur = 0
    for f in flags:
        if f:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def query_respecting_source(scene: dict):
    """Transcript evidence wins when a template query is still about immigration."""
    query = scene.get('query')
    concepts = [item for item in (scene.get('semanticConcepts') or []) if isinstance(item, dict)]
    domains = {item.get('domain') for item in concepts}
    if not query or 'investment' not in domains or 'immigration' in domains:
        return query
    from .director_v11 import _query_is_immigration
    if not _query_is_immigration(query):
        return query
    evidence = next((str(item.get('evidence')) for item in concepts if item.get('evidence')), '')
    return evidence or query


def fill_media_for_scenes(plan: dict, *, seed: int | None = None) -> dict:
    """Library search for long-form scenes that have a query but no asset yet."""
    from . import visual_variation as vv

    rng = vv._rng(int(seed or plan.get('visualSeed') or 1))
    used_assets: list = []
    used_concepts: list = []
    used_prefixes: list = []
    recent = []
    scenes = []
    for scene in plan.get('scenes') or []:
        scene = dict(scene)
        bg = dict(scene.get('background') or {})
        source_query = query_respecting_source(scene)
        if source_query and source_query != scene.get('query'):
            scene['query'] = source_query
            for key in ('assetId', 'file', 'staged', 'conceptId'):
                bg.pop(key, None)
        if scene.get('query') and not bg.get('assetId'):
            asset = None
            chosen = None
            if scene.get('visualRole'):
                from .visual_review import picture_supports, select_reviewed
                quote = str(scene.get('passageQuote') or '')
                query = scene['query'] if isinstance(scene['query'], str) else scene['query'][0]
                try:
                    import sys
                    folder = str(vv.LIBRARY.parent)
                    if folder not in sys.path:
                        sys.path.insert(0, folder)
                    from search import search_assets
                    hits = search_assets(query, limit=32)
                except (OSError, ImportError):
                    hits = []
                for hit in hits:
                    rel = str(hit.get('file') or '')
                    if picture_supports(hit.get('id'), quote) and rel and (vv.LIBRARY / rel).is_file():
                        asset = hit
                        break
                if asset is None:
                    picked = select_reviewed(quote, set(used_assets))
                    rel = str((picked or {}).get('file') or '')
                    if picked and rel and (vv.LIBRARY / rel).is_file():
                        asset = {
                            'id': picked['assetId'],
                            'file': picked['file'],
                            'visualGrounding': picked.get('visualGrounding'),
                        }
                chosen = query
            if asset is None and not scene.get('visualRole'):
                asset, chosen = vv._background(
                rng,
                {
                    'query': scene['query'] if isinstance(scene['query'], (list, tuple)) else (scene['query'],),
                    'role': 'hero' if scene.get('sceneId') in ('context', 'residency') else 'supporting_broll',
                },
                used_assets,
                recent,
                used_concepts,
                used_prefixes,
            )
            if asset:
                bg['assetId'] = asset.get('id')
                bg['file'] = asset.get('file')
                bg['conceptId'] = asset.get('conceptId')
                if asset.get('visualGrounding'):
                    bg['visualGrounding'] = asset.get('visualGrounding')
                used_assets.append(asset.get('id'))
                if asset.get('conceptId'):
                    used_concepts.append(asset.get('conceptId'))
            scene['query'] = chosen or scene.get('query')
        scene['background'] = bg
        scenes.append(scene)
    out = dict(plan)
    out['scenes'] = scenes
    return out


def stage_semantic_motion(plan: dict, public_dir: Path, library: Path | None = None) -> dict:
    """Copy bound motion webm/mp4 into director-v3/picked and stamp staged paths."""
    root = Path(library or Path(__file__).resolve().parent.parent / 'media' / 'library' / 'out')
    picked = Path(public_dir) / 'picked'
    picked.mkdir(parents=True, exist_ok=True)
    out = dict(plan)
    scenes = []
    for scene in out.get('scenes') or []:
        scene = dict(scene)
        sm = dict(scene.get('semanticMotion') or {})
        rel = sm.get('file')
        if rel:
            src = root / rel
            if src.is_file():
                dest = picked / src.name
                if not dest.exists() or dest.stat().st_size != src.stat().st_size:
                    dest.write_bytes(src.read_bytes())
                sm['staged'] = f'picked/{dest.name}'
                scene['semanticMotion'] = sm
                shot = dict(scene.get('shotPlan') or {})
                shot['semanticMotion'] = sm
                scene['shotPlan'] = shot
        scenes.append(scene)
    out['scenes'] = scenes
    return out
