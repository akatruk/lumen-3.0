"""Resolve one visual plan before Remotion runs.

Meaning stays fixed. A seed chooses compatible treatments inside one
art-direction profile. The renderer does not roll dice.
"""
import json
import random
from pathlib import Path

LIBRARY = Path(__file__).resolve().parent.parent / 'media' / 'library' / 'out'

PROFILES = (
    'cinematic_editorial',
    'dynamic_social',
    'premium_motion_graphics',
    'documentary',
    'modern_explainer',
    'luxury_minimal',
)

ENERGY = {'calm': 'low', 'balanced': 'medium', 'dynamic': 'high'}

PROFILE_WEIGHTS = {
    'calm': {
        'documentary': 5, 'luxury_minimal': 4, 'cinematic_editorial': 3,
        'modern_explainer': 1, 'premium_motion_graphics': 1, 'dynamic_social': 0,
    },
    'balanced': {
        'cinematic_editorial': 4, 'modern_explainer': 3, 'premium_motion_graphics': 3,
        'documentary': 2, 'luxury_minimal': 2, 'dynamic_social': 1,
    },
    'dynamic': {
        'dynamic_social': 5, 'modern_explainer': 3, 'premium_motion_graphics': 2,
        'cinematic_editorial': 1, 'documentary': 0, 'luxury_minimal': 0,
    },
}

SCENES = (
    {'id': 'hook', 'intent': 'hook', 'kind': 'speaker', 'base': 'high'},
    {'id': 'residency', 'intent': 'document', 'kind': 'speaker_object', 'base': 'medium', 'query': (
        'passport document approval', 'document review desk', 'residence permit application',
    )},
    {'id': 'consult', 'intent': 'proof', 'kind': 'broll', 'base': 'medium', 'query': (
        'consultation meeting', 'advisor client documents', 'phone consultation office',
    )},
    {'id': 'beside', 'intent': 'criteria', 'kind': 'speaker_text', 'base': 'medium'},
    {'id': 'steps', 'intent': 'process', 'kind': 'infographic', 'base': 'low'},
    {'id': 'return', 'intent': 'payoff', 'kind': 'speaker', 'base': 'low'},
)

SPEAKER = {
    'speaker': ('speaker_fullscreen', 'speaker_closeup', 'speaker_medium', 'speaker_punch_in'),
    'speaker_object': ('speaker_split_left', 'speaker_split_right', 'speaker_with_foreground'),
    'speaker_text': ('speaker_split_left', 'speaker_split_right', 'speaker_with_diagram'),
    'broll': ('speaker_with_media',),
    'infographic': ('speaker_with_diagram',),
}

BACKGROUND = {
    'speaker': ('slow_zoom_in', 'slow_zoom_out', 'static_editorial', 'cinematic_crop', 'subtle_drift', 'vertical_pan'),
    'speaker_object': ('slow_zoom_in', 'static_editorial', 'cinematic_crop', 'subtle_drift'),
    'speaker_text': ('static_editorial', 'subtle_drift', 'slow_zoom_in'),
    'broll': ('ambient_loop',),
    'infographic': ('static_editorial', 'gradient_reveal', 'mask_reveal'),
    'photo': ('slow_zoom_in', 'slow_zoom_out', 'horizontal_pan', 'vertical_pan', 'subtle_drift', 'cinematic_crop', 'parallax_depth', 'mask_reveal'),
    'motion': ('ambient_loop',),
}

FOREGROUND = {
    'speaker_object': ('scale_reveal', 'slide_up', 'slide_left', 'mask_reveal', 'reveal_and_hold'),
    'speaker_text': ('slide_up', 'fade_stagger', 'reveal_and_hold'),
    'infographic': ('type_build', 'reveal_and_hold'),
    'speaker': ('reveal_and_hold',),
    'broll': ('reveal_and_hold',),
}

TEXT = ('phrase_reveal', 'word_pop', 'mask_reveal', 'slide_stack', 'minimal_fade', 'fade_stagger')
TRANSITIONS = ('cut', 'crossfade', 'mask_wipe')

# One place the renderer and the selector agree. A treatment outside its row is not chosen.
COMPATIBILITY = {
    'background_speaker': BACKGROUND['speaker'],
    'background_photo': BACKGROUND['photo'],
    'background_motion': BACKGROUND['motion'],
    'background_abstract': ('subtle_drift', 'gradient_reveal', 'mask_reveal', 'static_editorial'),
    'speaker_address': SPEAKER['speaker'],
    'speaker_with_object': SPEAKER['speaker_object'],
    'typography': TEXT,
    'transition': TRANSITIONS,
}

PROFILE_TEXT = {
    'luxury_minimal': ('minimal_fade', 'phrase_reveal'),
    'documentary': ('minimal_fade', 'phrase_reveal', 'fade_stagger'),
    'dynamic_social': ('word_pop', 'slide_stack', 'mask_reveal', 'phrase_reveal'),
    'premium_motion_graphics': ('mask_reveal', 'phrase_reveal', 'scale_punch'),
    'cinematic_editorial': ('phrase_reveal', 'minimal_fade', 'mask_reveal'),
    'modern_explainer': ('phrase_reveal', 'fade_stagger', 'slide_stack'),
}

TEXT_TO_ANIMATE = {
    'phrase_reveal': 'fade',
    'word_pop': 'pop',
    'mask_reveal': 'mask',
    'slide_stack': 'slide',
    'minimal_fade': 'fade',
    'fade_stagger': 'fade',
    'scale_punch': 'pop',
    'editorial_reveal': 'mask',
    'type_build': 'fade',
    'keyword_highlight': 'fade',
}


def _rng(seed):
    return random.Random(int(seed) % (2 ** 32))


def _pick(rng, options, blocked=()):
    pool = [item for item in options if item not in blocked]
    if not pool:
        pool = list(options)
    return rng.choice(pool)


def _weighted_profile(rng, energy):
    weights = PROFILE_WEIGHTS[energy]
    bag = [name for name, weight in weights.items() for _ in range(weight) if weight]
    return rng.choice(bag)


def _intensity(base, energy):
    order = ('low', 'medium', 'high')
    cap = {'calm': 1, 'balanced': 2, 'dynamic': 2}[energy]
    floor = {'calm': 0, 'balanced': 0, 'dynamic': 1}[energy]
    index = order.index(base)
    if energy == 'dynamic' and base == 'high':
        index = 2
    if energy == 'calm' and base == 'high':
        index = 1
    return order[min(cap, max(floor, index))]


def _candidates(query, exclude, recent=()):
    import sys
    folder = str(LIBRARY.parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    from search import search_assets
    found = []
    for asset in search_assets(
        query, limit=12, preferred_scene_role='explanation', path=LIBRARY / 'manifest.json', recent_ids=recent,
    ):
        if asset.get('id') in exclude:
            continue
        family = asset.get('visualFamily')
        if family not in ('photography', 'generative_motion', 'deterministic_motion'):
            continue
        file_name = str(asset.get('file') or '')
        if file_name.endswith('.svg'):
            continue
        found.append(asset)
        if len(found) == 8:
            break
    fresh = [asset for asset in found if asset.get('id') not in set(recent or ())]
    return fresh or found


def _background(rng, scene, exclude, recent=()):
    if not scene.get('query'):
        return None, None
    options = scene['query']
    query = _pick(rng, options) if isinstance(options, (list, tuple)) else options
    found = _candidates(query, exclude, recent)
    if not found:
        return None, query
    recent_set = set(recent or ())
    weights = []
    for asset in found:
        weight = max(1, int((asset.get('qualityScore') or 1) * 10))
        if asset.get('id') in recent_set:
            weight = 1
        weights.append(weight)
    bag = [asset for asset, weight in zip(found, weights) for _ in range(weight)]
    return rng.choice(bag), query


def _motion_file(asset):
    file_name = str((asset or {}).get('file') or '')
    return (asset or {}).get('type') == 'video' or file_name.endswith(('.mp4', '.webm', '.mov'))


def _budget(kind, text, background, foreground, motion_file=False):
    """One dominant motion. Complex type quiets the background. A moving plate gets no second camera."""
    rejected = []
    if motion_file and background != 'ambient_loop':
        rejected.append(background)
        background = 'ambient_loop'
    if text in ('word_pop', 'mask_reveal', 'slide_stack') and background not in ('static_editorial', 'ambient_loop', 'gradient_reveal'):
        rejected.append(background)
        background = 'static_editorial' if kind != 'broll' else 'ambient_loop'
    if foreground in ('slide_up', 'slide_left', 'mask_reveal') and background in ('horizontal_pan', 'vertical_pan', 'parallax_depth'):
        rejected.append(background)
        background = 'slow_zoom_in'
    return background, foreground, rejected


def recent_asset_ids(data_dir, limit=6):
    """Asset ids from the newest stored plans. Missing history is an empty set."""
    root = Path(data_dir)
    if not root.is_dir():
        return []
    files = []
    for path in root.glob('*/visual-history/gen_*.json'):
        files.append(path)
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    seen = []
    for path in files[:limit]:
        try:
            plan = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        for scene in plan.get('scenes') or []:
            asset_id = (scene.get('background') or {}).get('assetId')
            if asset_id and asset_id not in seen:
                seen.append(asset_id)
    return seen


def resolve_plan(seed, energy='balanced', variation='automatic', recent_ids=()):
    """One coherent plan. The same seed and energy always return the same choices."""
    if energy not in ENERGY:
        raise ValueError('visual_energy')
    if variation not in ('automatic', 'keep', 'remix'):
        raise ValueError('visual_variation')
    rng = _rng(seed)
    profile = _weighted_profile(rng, energy)
    scenes = []
    used_backgrounds = []
    used_layouts = []
    used_text = []
    used_transitions = []
    used_camera = []
    for scene in SCENES:
        kind = scene['kind']
        layout = _pick(rng, SPEAKER[kind], blocked=used_layouts[-2:])
        if scene.get('query'):
            asset, chosen_query = _background(rng, scene, used_backgrounds[-1:], recent_ids)
        else:
            asset, chosen_query = None, None
        motion_file = _motion_file(asset)
        if motion_file:
            media_kind = 'motion'
        elif asset and asset.get('type') == 'image':
            media_kind = 'photo'
        elif kind == 'broll':
            media_kind = 'broll'
        else:
            media_kind = kind
        options = BACKGROUND[media_kind if media_kind in BACKGROUND else kind]
        background = _pick(rng, options, blocked=used_camera[-2:])
        foreground = _pick(rng, FOREGROUND[kind])
        allowed_text = PROFILE_TEXT.get(profile, TEXT)
        text = _pick(rng, allowed_text, blocked=used_text[-2:])
        background, foreground, rejected = _budget(kind, text, background, foreground, motion_file)
        if used_transitions[-2:] == ['crossfade', 'crossfade']:
            transition = 'cut'
        elif profile in ('documentary', 'luxury_minimal') and rng.random() < 0.75:
            transition = 'cut'
        else:
            transition = _pick(rng, TRANSITIONS, blocked=used_transitions[-1:] if used_transitions[-1:] == ['mask_wipe'] else ())
        record = {
            'sceneId': scene['id'],
            'semanticPurpose': scene['intent'],
            'query': chosen_query,
            'speaker': {'layout': layout, 'treatment': 'speaker_punch_in' if layout == 'speaker_punch_in' else layout},
            'background': {
                'assetId': asset.get('id') if asset else None,
                'file': asset.get('file') if asset else None,
                'treatment': background,
            },
            'foreground': {'treatment': foreground, 'assetId': 'passport.png' if kind == 'speaker_object' else None},
            'typography': {'treatment': text, 'animate': TEXT_TO_ANIMATE.get(text, 'fade')},
            'transition': transition,
            'motionIntensity': _intensity(scene['base'], energy),
            'rejected': rejected,
        }
        scenes.append(record)
        used_layouts.append(layout)
        used_text.append(text)
        used_transitions.append(transition)
        used_camera.append(background)
        if asset:
            used_backgrounds.append(asset.get('id'))
    return {
        'visualSeed': int(seed),
        'visualStyle': profile,
        'artDirection': profile,
        'visualEnergy': energy,
        'motionIntensity': ENERGY[energy],
        'scenes': scenes,
    }


def new_seed():
    return random.SystemRandom().randrange(1, 1_000_000_000)


def history_dir(data_dir, project_id):
    folder = Path(data_dir) / project_id / 'visual-history'
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def load_latest(data_dir, project_id):
    pointer = history_dir(data_dir, project_id) / 'latest.json'
    if not pointer.is_file():
        return None
    ref = json.loads(pointer.read_text(encoding='utf-8'))
    plan_file = history_dir(data_dir, project_id) / f"{ref['generationId']}.json"
    if not plan_file.is_file():
        return None
    return json.loads(plan_file.read_text(encoding='utf-8'))


def store_plan(data_dir, project_id, plan):
    folder = history_dir(data_dir, project_id)
    dest = folder / f"{plan['generationId']}.json"
    if not dest.exists():
        dest.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'latest.json').write_text(json.dumps({
        'generationId': plan['generationId'],
        'visualSeed': plan['visualSeed'],
    }), encoding='utf-8')
    return dest


def plan_for_request(data_dir, project_id, variation, energy, language=None):
    """New generations get a new seed. Keep, a language switch, and a retry reuse the last plan."""
    if variation not in ('automatic', 'keep', 'remix'):
        raise ValueError('visual_variation')
    if energy not in ENERGY:
        raise ValueError('visual_energy')
    previous = load_latest(data_dir, project_id)
    if variation == 'keep' and previous:
        return previous
    if (
        variation == 'automatic'
        and previous
        and language
        and previous.get('language')
        and previous.get('language') != language
    ):
        return previous
    seed = new_seed()
    plan = resolve_plan(seed, energy, variation, recent_asset_ids(data_dir))
    plan['generationId'] = f"gen_{seed}"
    if language:
        plan['language'] = language
    store_plan(data_dir, project_id, plan)
    return plan


def _manifest_ids(library: Path):
    path = library / 'manifest.json'
    if not path.is_file():
        return set()
    manifest = json.loads(path.read_text(encoding='utf-8'))
    return {item.get('id') for item in manifest.get('assets') or []}


def stage_backgrounds(plan, public_dir: Path, library: Path | None = None):
    """Copy chosen stills next to the Remotion public files.

    A still is staged only when its id is already in the library manifest.
    Newly generated files have to be indexed first.
    """
    root = Path(library) if library is not None else LIBRARY
    indexed = _manifest_ids(root)
    picked = public_dir / 'picked'
    picked.mkdir(parents=True, exist_ok=True)
    for scene in plan.get('scenes') or []:
        background = scene.get('background') or {}
        relative = background.get('file')
        asset_id = background.get('assetId')
        if not relative or not asset_id or asset_id not in indexed:
            if relative:
                background['staged'] = None
            continue
        source = root / relative
        if not source.is_file():
            background['staged'] = None
            continue
        dest = picked / f"{asset_id}{source.suffix.lower()}"
        if not dest.exists() or dest.stat().st_size != source.stat().st_size:
            dest.write_bytes(source.read_bytes())
        background['staged'] = f"picked/{dest.name}"
    return plan
