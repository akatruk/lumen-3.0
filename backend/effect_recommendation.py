"""One visual treatment for the next picture render.

The choice is local. A push, a grade, a vignette, or a glow softens a small
frame, so this does not apply them. Card motion is the slider the editor
already saves. It does not call a model and does not invent a property fact.
"""
import copy

# A centered push. These ends are not one of the staged pushes the renderer drops.
PUSH_END = 1.26
GRADE = {
    'brightness': 0.02,
    'contrast': 1.08,
    'saturation': 1.1,
    'gamma': 0.98,
    'rs': 0.03,
    'gs': 0.0,
    'bs': -0.02,
}
VIGNETTE = 0.55
GLOW = 0.6
CARD_MOTION = 70


def _length(clip):
    try:
        return max(0.08, float(clip['end']) - float(clip['start']))
    except (KeyError, TypeError, ValueError):
        return 0.08


def _num(value, default):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:
        return default
    return number


def _open(edit):
    rows = []
    for clip in edit.get('clips') or []:
        if not isinstance(clip, dict) or not clip.get('id'):
            continue
        if clip.get('approved') is False or clip.get('locked'):
            continue
        rows.append(clip)
    return rows


def _share(clips, predicate):
    total = sum(_length(clip) for clip in clips) or 1.0
    return sum(_length(clip) for clip in clips if predicate(clip)) / total


def _moving(clip):
    start = _num(clip.get('zoom'), 1)
    end = clip.get('zoom_end')
    end = start if end is None else _num(end, start)
    return abs(end - start) >= 0.04 or max(start, end) >= 1.08


def _grade_of(clip):
    grade = clip.get('grade')
    if not isinstance(grade, dict):
        return None
    keys = ('brightness', 'contrast', 'saturation', 'gamma', 'rs', 'gs', 'bs')
    parsed = {}
    for key in keys:
        default = 1.0 if key in ('contrast', 'saturation', 'gamma') else 0.0
        parsed[key] = _num(grade.get(key), default)
    identity = all(abs(parsed[key] - (1.0 if key in ('contrast', 'saturation', 'gamma') else 0.0)) <= 0.01 for key in keys)
    return None if identity else parsed


def _vignette(clip):
    return bool(clip.get('shadow')) and _num(clip.get('shade'), 0) >= 0.2


def _glow(clip):
    return bool(clip.get('glow')) and _num(clip.get('glow_amount'), 0) >= 0.2


def _graphics(edit):
    if edit.get('presentation'):
        return True
    return any(isinstance(clip, dict) and clip.get('card') for clip in edit.get('clips') or [])


def _measured_grade(edit):
    for clip in edit.get('clips') or []:
        if isinstance(clip, dict):
            grade = _grade_of(clip)
            if grade:
                return grade
    return None


def _push(clips):
    total = sum(_length(clip) for clip in clips) or 1.0
    cursor = 0.0
    patches = {}
    for clip in clips:
        length = _length(clip)
        start = cursor / total
        stop = (cursor + length) / total
        zoom = round(1 + (PUSH_END - 1) * start, 3)
        zoom_end = round(1 + (PUSH_END - 1) * stop, 3)
        if zoom_end <= zoom:
            zoom_end = round(min(3, zoom + 0.02), 3)
        patches[clip['id']] = {
            'zoom': zoom,
            'zoom_end': zoom_end,
            'x': 0.5,
            'y': 0.5,
            'x_end': 0.5,
            'y_end': 0.5,
            'motion_seconds': round(length, 3),
        }
        cursor += length
    return {'id': 'punch', 'clips': patches, 'edit': {}}


def _same(clips, patch):
    kind = 'grade' if 'grade' in patch else 'vignette' if 'shadow' in patch else 'glow'
    return {'id': kind, 'clips': {clip['id']: copy.deepcopy(patch) for clip in clips}, 'edit': {}}


def recommend(edit):
    """Pick one treatment the next render will execute. Raises when none will change the picture.

    A centered push, a grade, a vignette, and a glow are not offered. Accepting
    the first suggestion used to write zoom 1.00→1.26, and the picture path
    resampled the footage.
    """
    if not isinstance(edit, dict):
        raise ValueError('effect_unavailable')
    clips = _open(edit)
    if not clips:
        raise ValueError('no_open_picture')
    motion = edit.get('card_motion')
    motion = 100 if motion is None else _num(motion, 100)
    if _graphics(edit) and motion >= 95:
        return {'id': 'card_motion', 'clips': {}, 'edit': {'card_motion': CARD_MOTION}}
    intensity = edit.get('animation_intensity')
    intensity = 100 if intensity is None else _num(intensity, 100)
    if _graphics(edit) and intensity >= 95:
        return {'id': 'intensity', 'clips': {}, 'edit': {'animation_intensity': 50}}
    density = edit.get('animation_density')
    density = 100 if density is None else _num(density, 100)
    if _graphics(edit) and density >= 95:
        return {'id': 'density', 'clips': {}, 'edit': {'animation_density': 60}}
    raise ValueError('effect_unavailable')


def apply_recommendation(edit, recommendation):
    shaped = copy.deepcopy(edit)
    patches = (recommendation or {}).get('clips') or {}
    for clip in shaped.get('clips') or []:
        if not isinstance(clip, dict):
            continue
        patch = patches.get(clip.get('id'))
        if isinstance(patch, dict):
            clip.update(patch)
    extra = (recommendation or {}).get('edit') or {}
    for key in ('card_motion', 'animation_intensity', 'animation_density'):
        if key in extra:
            shaped[key] = extra[key]
    return shaped


def proposal(edit):
    """The recommendation, after checking the patched cut still validates."""
    from .manual import Edit

    result = recommend(edit)
    Edit.model_validate(apply_recommendation(edit, result))
    return result
