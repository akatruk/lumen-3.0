"""Director V9 — premium clean motion: composition intelligence + container reduction.

Builds on V8 long60 plans. Prefer transparent SVG/PNG floating objects over
opaque yuv420p webm plates wrapped in Remotion black boxes. One primary visual
idea per scene; simplify when complexity exceeds budget.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# Transparent (or intentional SVG) foreground objects — NOT opaque webm plates.
# keyword → (rel path under media/library/out, silhouette, concept)
OBJECT_BINDINGS: tuple[tuple[str, str, str, str], ...] = (
    ('relocation', 'static/immigration/imm_obj_suitcase.svg', 'suitcase', 'mobility'),
    ('relocation', 'static/decorative/route-arc-gold.svg', 'route', 'mobility'),
    ('relocation', 'static/immigration/imm_obj_pin.svg', 'pin', 'mobility'),
    ('residency', 'static/icons/passport.svg', 'passport', 'residency'),
    ('passport', 'static/v2/fg_passport.svg', 'passport_alt', 'passport'),
    ('documents', 'static/documents/doc_folder_001.png', 'folder', 'documents'),
    ('documents', 'static/documents/doc_seal_001.png', 'seal', 'documents'),
    ('program', 'static/icons/checklist.svg', 'checklist', 'program'),
    ('consult', 'static/icons/consultation.svg', 'consult', 'consult'),
    ('family', 'static/icons/family.svg', 'family', 'family'),
    ('budget', 'static/icons/budget.svg', 'budget', 'budget'),
    ('goals', 'static/icons/goal.svg', 'target', 'goals'),
)

# Scenes where a floating object is allowed (speaker-led, not already media-heavy).
FLOAT_OK = frozenset({'hook', 'problem', 'payoff', 'return', 'context'})
# Scenes where opaque webm may appear only as ambient full-bleed (never boxed).
CUTAWAY_OK = frozenset({'consult', 'proof'})
# Infographic / card scenes — no competing float objects.
INFO_OWNED = frozenset({'beside', 'residency'})

COMPLEXITY_BUDGET = {
    'speaker': 2.2,
    'broll': 2.0,
    'infographic': 1.8,
    'default': 2.0,
}


def _library_root() -> Path:
    return Path(__file__).resolve().parent.parent / 'media' / 'library' / 'out'


def _object_for(keyword_ids: list[str], *, used_silhouettes: set[str], used_assets: set[str]) -> dict | None:
    for kid, rel, sil, concept in OBJECT_BINDINGS:
        if kid not in keyword_ids:
            continue
        if sil in used_silhouettes or rel in used_assets:
            continue
        path = _library_root() / rel
        if not path.is_file():
            continue
        return {
            'assetId': Path(rel).stem,
            'file': rel,
            'silhouette': sil,
            'concept': concept,
            'keyword': kid,
            'background': 'transparent',
            'display': 'float',
        }
    # Second pass: allow silhouette reuse only if no alternative file exists.
    for kid, rel, sil, concept in OBJECT_BINDINGS:
        if kid not in keyword_ids:
            continue
        if rel in used_assets:
            continue
        path = _library_root() / rel
        if not path.is_file():
            continue
        return {
            'assetId': Path(rel).stem,
            'file': rel,
            'silhouette': sil,
            'concept': concept,
            'keyword': kid,
            'background': 'transparent',
            'display': 'float',
        }
    return None


def _keywords_for_scene(scene: dict) -> list[str]:
    shot = scene.get('shotPlan') or {}
    keys = shot.get('keywords') or []
    ids = []
    for k in keys:
        if isinstance(k, dict) and k.get('id'):
            ids.append(str(k['id']))
        elif isinstance(k, str):
            ids.append(k)
    sm = scene.get('semanticMotion') or {}
    if sm.get('keyword'):
        ids.append(str(sm['keyword']))
    pref = (scene.get('shotPlan') or {}).get('keywordPref') or ()
    ids.extend(list(pref))
    # Stable order, unique
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _primary_role(scene: dict) -> str:
    framing = ((scene.get('speaker') or {}).get('framing')
               or (scene.get('execution') or {}).get('speakerFraming')
               or '')
    sid = scene.get('sceneId') or ''
    if sid in ('beside', 'steps') or (scene.get('typography') or {}).get('cardMode') == 'progressive_one':
        return 'infographic'
    if framing == 'pip' or sid in ('consult', 'proof'):
        return 'broll'
    if framing == 'split' and (scene.get('background') or {}).get('assetId'):
        return 'speaker_media'
    return 'speaker'


def score_scene_complexity(scene: dict) -> dict[str, Any]:
    """Deterministic salience-weighted complexity (not DOM count)."""
    role = scene.get('primaryVisualRole') or _primary_role(scene)
    score = 1.0  # primary always present
    reasons: list[str] = []
    bg = scene.get('background') or {}
    fg = scene.get('foreground') or {}
    sm = scene.get('semanticMotion') or {}
    typ = scene.get('typography') or {}
    comp = scene.get('composition') or {}

    if bg.get('assetId') or bg.get('staged'):
        score += 0.7
        reasons.append('media_plate')
    if fg.get('staged') or fg.get('file') or (comp.get('floatObject') or {}).get('file'):
        area = float((comp.get('floatObject') or {}).get('areaShare') or 0.12)
        score += 0.5 + min(0.6, area * 2)
        reasons.append('foreground_object')
    if sm.get('staged') and sm.get('display') != 'omit':
        # Opaque webm plates are high contrast / high area
        if sm.get('display') == 'cutaway':
            score += 0.4
            reasons.append('motion_cutaway')
        else:
            score += 1.1
            reasons.append('motion_box')
    if typ.get('headline') and not comp.get('suppressHeadline'):
        score += 0.55
        reasons.append('headline')
    if typ.get('cards') or typ.get('cardMode') == 'progressive_one':
        score += 0.65
        reasons.append('cards')
    if typ.get('steps') or typ.get('stepsTitle'):
        score += 0.7
        reasons.append('steps')
    if scene.get('heroObject'):
        score += 0.45
        reasons.append('hero')

    budget = COMPLEXITY_BUDGET.get(role if role in COMPLEXITY_BUDGET else 'default', 2.0)
    if role == 'speaker_media':
        budget = 2.0
    return {
        'score': round(score, 2),
        'budget': budget,
        'overBudget': score > budget,
        'reasons': reasons,
        'role': role,
    }


def simplify_scene_composition(scene: dict, *, used_silhouettes: set[str], used_assets: set[str]) -> dict:
    """Reduce competing layers until within budget. Never strip factual card/step content."""
    scene = dict(scene)
    sid = scene.get('sceneId') or ''
    role = _primary_role(scene)
    scene['primaryVisualRole'] = role
    typ = dict(scene.get('typography') or {})
    sm = dict(scene.get('semanticMotion') or {})
    fg = dict(scene.get('foreground') or {})
    composition: dict[str, Any] = {
        'containerPolicy': 'minimal',
        'speakerProtection': True,
        'captionRegion': 'safe_lower_center',
        'visualComplexity': 'low',
        'suppressHeadline': False,
        'suppressHero': True,
        'suppressConcepts': True,
        'floatObject': None,
    }

    # Steps: keep as speaker-led process (not a dark card wall).
    if sid == 'steps':
        role = 'speaker'
        scene['primaryVisualRole'] = 'speaker'
        scene['speaker'] = {
            **dict(scene.get('speaker') or {}),
            'layout': 'speaker_medium',
            'framing': 'fullscreen',
            'visibility': 'primary',
        }

    # Infographic owns the frame — no float, no webm box, no headline duplicate.
    if role == 'infographic' or sid in INFO_OWNED:
        sm['display'] = 'omit'
        sm.pop('staged', None)
        composition['suppressHeadline'] = True
        composition['floatObject'] = None
        if sid == 'residency' and role == 'speaker_media':
            # Split media is the secondary visual; keep speaker primary.
            composition['secondaryVisual'] = 'media_plate'
        else:
            composition['secondaryVisual'] = 'none'
        composition['primarySubject'] = 'infographic' if role == 'infographic' else 'speaker'
    elif role == 'broll' or sid in CUTAWAY_OK:
        # Media is primary; speaker PIP is secondary. No floating box.
        composition['primarySubject'] = 'media'
        composition['secondaryVisual'] = 'speaker_pip'
        composition['suppressHeadline'] = True
        if sm.get('file') and sid in CUTAWAY_OK:
            sm['display'] = 'omit'  # plate already from background; avoid second motion layer
        else:
            sm['display'] = 'omit'
        composition['floatObject'] = None
    else:
        # Speaker-led: one transparent float object when allowed.
        composition['primarySubject'] = 'speaker'
        composition['secondaryVisual'] = 'none'
        kids = _keywords_for_scene(scene)
        obj = None
        # Steps already has progressive type as the secondary visual — no float.
        if sid != 'steps' and (sid in FLOAT_OK or role == 'speaker'):
            obj = _object_for(kids, used_silhouettes=used_silhouettes, used_assets=used_assets)
        if obj:
            used_silhouettes.add(obj['silhouette'])
            used_assets.add(obj['file'])
            obj['placement'] = 'speaker_right_lower' if sid in ('hook', 'problem') else 'speaker_left_lower'
            obj['areaShare'] = 0.14 if sid == 'hook' else 0.12
            composition['floatObject'] = obj
            composition['secondaryVisual'] = 'float_object'
            fg['assetId'] = obj['assetId']
            fg['file'] = obj['file']
            fg['treatment'] = 'scale_reveal'
            fg['background'] = 'transparent'
        # Never mount opaque webm as a bordered box on speaker scenes.
        sm['display'] = 'omit'
        sm.pop('staged', None)
        # Hook keeps kinetic headline; problem/payoff rely on captions.
        if sid != 'hook':
            composition['suppressHeadline'] = True
        else:
            composition['suppressHeadline'] = False

    # Drop hero globe/passport when float object already present or scene is media-led.
    if composition.get('floatObject') or role in ('broll', 'infographic', 'speaker_media'):
        scene['heroObject'] = None
        composition['suppressHero'] = True

    scene['typography'] = typ
    scene['semanticMotion'] = sm
    scene['foreground'] = fg
    scene['containerPolicy'] = 'minimal'
    scene['speakerProtection'] = True
    scene['captionRegion'] = 'safe_lower_center'
    scene['composition'] = composition

    # Iterative simplify by score.
    for _ in range(4):
        metrics = score_scene_complexity(scene)
        scene['visualComplexityScore'] = metrics
        if not metrics['overBudget']:
            break
        reasons = set(metrics['reasons'])
        comp = dict(scene.get('composition') or {})
        if 'motion_box' in reasons:
            sm = dict(scene.get('semanticMotion') or {})
            sm['display'] = 'omit'
            sm.pop('staged', None)
            scene['semanticMotion'] = sm
            continue
        if 'headline' in reasons and (sid != 'hook' or 'foreground_object' in reasons):
            comp['suppressHeadline'] = True
            typ = dict(scene.get('typography') or {})
            # Keep headline text for plan provenance but Remotion won't mount it.
            scene['typography'] = typ
            scene['composition'] = comp
            continue
        if 'hero' in reasons:
            scene['heroObject'] = None
            comp['suppressHero'] = True
            scene['composition'] = comp
            continue
        if 'foreground_object' in reasons and role in ('broll', 'speaker_media', 'infographic'):
            comp['floatObject'] = None
            comp['secondaryVisual'] = 'media_plate' if role != 'infographic' else 'none'
            fg = dict(scene.get('foreground') or {})
            fg['file'] = None
            fg['assetId'] = None
            scene['foreground'] = fg
            scene['composition'] = comp
            continue
        if 'foreground_object' in reasons and sid in ('payoff', 'return', 'context'):
            # Prefer cleaner speaker over decoration when still over budget.
            comp['floatObject'] = None
            comp['secondaryVisual'] = 'none'
            scene['composition'] = comp
            break
        break

    metrics = score_scene_complexity(scene)
    scene['visualComplexityScore'] = metrics
    level = 'low' if metrics['score'] <= 1.6 else 'medium' if metrics['score'] <= metrics['budget'] else 'high'
    scene['visualComplexity'] = level
    comp = dict(scene.get('composition') or {})
    comp['visualComplexity'] = level
    scene['composition'] = comp
    return scene


def apply_composition_intelligence(plan: dict) -> dict:
    """V9 pass over an expanded V8 plan — clean composition without changing duration/story."""
    out = dict(plan)
    used_silhouettes: set[str] = set()
    used_assets: set[str] = set()
    scenes = []
    reports = []
    for raw in out.get('scenes') or []:
        scene = simplify_scene_composition(
            dict(raw), used_silhouettes=used_silhouettes, used_assets=used_assets,
        )
        scenes.append(scene)
        fo = (scene.get('composition') or {}).get('floatObject') or {}
        reports.append({
            'sceneId': scene.get('sceneId'),
            'primaryVisualRole': scene.get('primaryVisualRole'),
            'visualComplexity': scene.get('visualComplexity'),
            'score': (scene.get('visualComplexityScore') or {}).get('score'),
            'budget': (scene.get('visualComplexityScore') or {}).get('budget'),
            'overBudget': (scene.get('visualComplexityScore') or {}).get('overBudget'),
            'floatObject': fo.get('assetId'),
            'silhouette': fo.get('silhouette'),
            'semanticMotionDisplay': (scene.get('semanticMotion') or {}).get('display'),
            'suppressHeadline': (scene.get('composition') or {}).get('suppressHeadline'),
            'containerPolicy': scene.get('containerPolicy'),
        })

    out['scenes'] = scenes
    out['shotPlanVersion'] = 'v9'
    out['compositionPolicy'] = 'v9_clean'
    out['conceptTriggers'] = False  # captions + one float — no competing concept stack
    out['heroObject'] = None
    # Plan-level anti-repetition on silhouettes / float assets
    floats = [((s.get('composition') or {}).get('floatObject') or {}).get('assetId') for s in scenes]
    sils = [((s.get('composition') or {}).get('floatObject') or {}).get('silhouette') for s in scenes]
    out['compositionAudit'] = {
        'scenes': reports,
        'uniqueFloatAssets': len({x for x in floats if x}),
        'uniqueSilhouettes': len({x for x in sils if x}),
        'overBudgetCount': sum(1 for r in reports if r.get('overBudget')),
        'opaqueMotionBoxes': sum(
            1 for s in scenes
            if (s.get('semanticMotion') or {}).get('display') not in (None, 'omit', 'cutaway')
            and (s.get('semanticMotion') or {}).get('staged')
        ),
        'pass': all(not r.get('overBudget') for r in reports),
    }
    anti = dict(out.get('antiRepetition') or {})
    anti['floatAssets'] = [x for x in floats if x]
    anti['silhouettes'] = [x for x in sils if x]
    anti['maxSameSilhouetteStreak'] = _max_same_streak([x for x in sils if x])
    anti['pass'] = anti.get('pass', True) and anti['maxSameSilhouetteStreak'] < 3
    out['antiRepetition'] = anti
    return out


def dedupe_looping_captions(captions: list | None) -> list:
    """Drop verbatim caption loops (same text restarting mid-timeline).

    Source takes sometimes repeat the intro; remounting it at ~40s reads as a
    broken empty plate over the steps beat.
    """
    rows = []
    seen: set[str] = set()
    for row in captions or []:
        if not isinstance(row, dict):
            continue
        text = ' '.join(str(row.get('text') or '').split())
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows


def stage_float_objects(plan: dict, public_dir: Path, library: Path | None = None) -> dict:
    """Copy transparent float assets into Remotion public/picked and stamp staged paths."""
    root = Path(library or _library_root())
    picked = Path(public_dir) / 'picked'
    picked.mkdir(parents=True, exist_ok=True)
    out = dict(plan)
    scenes = []
    for scene in out.get('scenes') or []:
        scene = dict(scene)
        comp = dict(scene.get('composition') or {})
        fo = dict(comp.get('floatObject') or {})
        rel = fo.get('file')
        if rel:
            src = root / rel
            if src.is_file():
                dest = picked / src.name
                if not dest.exists() or dest.stat().st_size != src.stat().st_size:
                    dest.write_bytes(src.read_bytes())
                fo['staged'] = f'picked/{dest.name}'
                fo['background'] = 'transparent'
                comp['floatObject'] = fo
                scene['composition'] = comp
                fg = dict(scene.get('foreground') or {})
                fg['staged'] = fo['staged']
                fg['assetId'] = fo.get('assetId')
                fg['file'] = rel
                fg['background'] = 'transparent'
                scene['foreground'] = fg
        # Ensure omitted motion is not staged for boxed display
        sm = dict(scene.get('semanticMotion') or {})
        if sm.get('display') == 'omit':
            sm.pop('staged', None)
            scene['semanticMotion'] = sm
        scenes.append(scene)
    out['scenes'] = scenes
    return out


def _max_same_streak(items: list[str]) -> int:
    best = cur = 0
    prev = None
    for x in items:
        if x == prev:
            cur += 1
        else:
            cur = 1
            prev = x
        best = max(best, cur)
    return best
