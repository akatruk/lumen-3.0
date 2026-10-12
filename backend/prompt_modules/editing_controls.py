"""Editing-controls prompt module (Calm/Balanced/Dynamic + four sliders).

Refines montage preferences only. Does not rewrite QUALITY ENFORCEMENT,
localization, face/caption safety, or media-selection rules.
"""
from __future__ import annotations

from .base import ModuleAttachment

ID = 'editing_controls'
VERSION = '1.0.0'
DOMAIN = 'editing'

# Calm / Balanced / Dynamic — coherent slider bundles. Manual drift → custom.
PRESETS = {
    'calm': {'animation': 40, 'intensity': 40, 'motion': 40, 'density': 40},
    'balanced': {'animation': 60, 'intensity': 60, 'motion': 80, 'density': 70},
    'dynamic': {'animation': 85, 'intensity': 85, 'motion': 90, 'density': 85},
}

_RULES = """--- MODULE EDITING CONTROLS RULES ---

Treat project editing settings as bounded montage preferences, not quotas.

- Animation: share of suitable elements and scenes that receive meaningful
  motion graphics. High values do not invent irrelevant plates or text.
- Intensity: strength of visual accents and transition expressiveness.
- Motion: speed and amplitude of element and camera movement — never speech rate.
- Density: how much additional information is shown at once (cards, insets,
  concept overlays). High density still prefers relevance over clutter.

Calm / Balanced / Dynamic set coherent combinations of the four values.
Manual slider changes move the state to Custom while keeping the same rules.

Priority order (never inverted by a high slider):
speech meaning → host visibility → readability → relevant visuals → style.

No slider value cancels face protection, caption safe zones, readable type
size, minimum scene duration, asset quality gates, or the ban on random
duplicate plates / same-source insets.

Do not post-process a finished MP4 to fake these settings. Prefer replan +
Remotion parameters. Slider moves alone must not start paid GPU/TTS work.

--- END MODULE EDITING CONTROLS RULES ---"""


def snap_percent(value, default=60, low=0):
    """Clamp to 0–100 (or low–100) in steps of 5."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    number = max(low, min(100, number))
    number -= number % 5
    return max(low, number)


def levels_from_manual(manual: dict | None) -> dict:
    data = manual or {}
    return {
        'animation': snap_percent(data.get('card_motion', data.get('animation', 60)), 60),
        'intensity': snap_percent(data.get('animation_intensity', data.get('intensity', 60)), 60, 5),
        'motion': snap_percent(data.get('animation_motion', data.get('motion', 80)), 80),
        'density': snap_percent(data.get('animation_density', data.get('density', 70)), 70),
    }


def detect_preset(levels: dict) -> str:
    """Return calm|balanced|dynamic when levels match a preset, else custom."""
    for name, preset in PRESETS.items():
        if all(int(levels.get(key, -1)) == int(preset[key]) for key in preset):
            return name
    return 'custom'


def band(percent: int) -> str:
    if percent <= 35:
        return 'low'
    if percent <= 70:
        return 'medium'
    return 'high'


def _merge_band(base: str, motion_band: str, intensity_band: str) -> str:
    order = ('low', 'medium', 'high')
    if base not in order:
        base = 'medium'
    # Motion dominates amplitude; intensity nudges one step toward itself.
    index = order.index(motion_band)
    if intensity_band == 'high' and index < 2:
        index += 1
    if intensity_band == 'low' and index > 0:
        index -= 1
    # Never jump more than one step away from planner base without motion support.
    base_i = order.index(base)
    if abs(index - base_i) > 1:
        index = base_i + (1 if index > base_i else -1)
    return order[index]


def apply_editing_controls(plan: dict | None, controls: dict | None) -> dict:
    """Stamp structured editing prefs onto a Director visual plan.

    Safe to call on a reused (keep) plan — only overlays preferences; does not
    re-roll seeds or invent assets.
    """
    source = dict(plan or {})
    levels = levels_from_manual({
        'card_motion': (controls or {}).get('animation', source.get('editingControls', {}).get('animation', 60)),
        'animation_intensity': (controls or {}).get('intensity', source.get('editingControls', {}).get('intensity', 60)),
        'animation_motion': (controls or {}).get('motion', source.get('editingControls', {}).get('motion', 80)),
        'animation_density': (controls or {}).get('density', source.get('editingControls', {}).get('density', 70)),
    })
    requested_energy = (controls or {}).get('visualEnergy') or source.get('visualEnergy') or 'balanced'
    if requested_energy not in ('calm', 'balanced', 'dynamic', 'custom'):
        requested_energy = 'balanced'
    preset = detect_preset(levels)
    energy_label = preset if requested_energy == 'custom' else (
        'custom' if preset == 'custom' and requested_energy in PRESETS else requested_energy
    )
    if requested_energy in PRESETS and preset == requested_energy:
        energy_label = requested_energy
    elif requested_energy in PRESETS and preset != requested_energy:
        energy_label = 'custom'

    motion_band = band(levels['motion'])
    intensity_band = band(levels['intensity'])
    scenes_in = list(source.get('scenes') or [])
    total = max(1, len(scenes_in))
    scenes_out = []
    for index, scene in enumerate(scenes_in):
        row = dict(scene)
        base = row.get('motionIntensity') or 'medium'
        row['motionIntensity'] = _merge_band(base, motion_band, intensity_band)
        # Animation share: first N% of scene order keep purposeful graphics motion.
        row['animateGraphics'] = (index / total) < (levels['animation'] / 100.0)
        density = levels['density']
        if density < 25:
            row['overlayBudget'] = 0
        elif density < 55:
            row['overlayBudget'] = 1
        elif density < 80:
            row['overlayBudget'] = 2
        else:
            row['overlayBudget'] = 3
        # Low density: prefer quieter typography motion.
        if density < 40 and (row.get('typography') or {}).get('animate') in ('pop', 'mask'):
            typography = dict(row.get('typography') or {})
            typography['animate'] = 'fade'
            row['typography'] = typography
        scenes_out.append(row)

    out = dict(source)
    out['scenes'] = scenes_out
    out['editingControls'] = {
        'animation': levels['animation'],
        'intensity': levels['intensity'],
        'motion': levels['motion'],
        'density': levels['density'],
        'visualEnergy': energy_label,
        'preset': preset,
    }
    # Seeded profile energy stays calm|balanced|dynamic for resolve_plan weights.
    if requested_energy in PRESETS:
        out['visualEnergy'] = requested_energy
    elif source.get('visualEnergy') in PRESETS:
        out['visualEnergy'] = source['visualEnergy']
    else:
        out['visualEnergy'] = 'balanced'
    out['motionIntensity'] = motion_band
    # Density gates concept overlays globally; planner may still set True.
    out['conceptTriggers'] = levels['density'] >= 30 and source.get('conceptTriggers', True) is not False
    return out


class EditingControlsModule:
    id = ID
    version = VERSION
    domain = DOMAIN

    def applicable(self, manual: dict) -> bool:
        # Always attach — defaults match Balanced when sliders are omitted.
        del manual
        return True

    def attach(self, manual: dict) -> ModuleAttachment:
        levels = levels_from_manual(manual)
        energy = (manual or {}).get('visual_energy') or (manual or {}).get('visualEnergy') or 'balanced'
        if energy not in ('calm', 'balanced', 'dynamic', 'custom'):
            energy = 'balanced'
        preset = detect_preset(levels)
        if energy in PRESETS and preset != energy:
            energy_label = 'custom'
        else:
            energy_label = energy if energy != 'custom' else preset
        summary = (
            f"Preset: {energy_label} (matched: {preset}). "
            f"Animation {levels['animation']}%. "
            f"Intensity {levels['intensity']}. "
            f"Motion {levels['motion']}%. "
            f"Density {levels['density']}%."
        )
        instructions = "\n\n".join((
            f"--- MODULE: {ID} @{VERSION} ---",
            _RULES,
            f"--- EDITING CONTROLS VALUES ---\n{summary}\n--- END EDITING CONTROLS VALUES ---",
            f"--- END MODULE: {ID} ---",
        ))
        return ModuleAttachment(
            id=ID,
            version=VERSION,
            domain=DOMAIN,
            instructions=instructions,
            conflicts=(),
            run_params={
                'editingControls': {
                    'animation': levels['animation'],
                    'intensity': levels['intensity'],
                    'motion': levels['motion'],
                    'density': levels['density'],
                    'visualEnergy': energy_label,
                    'preset': preset,
                },
            },
        )
