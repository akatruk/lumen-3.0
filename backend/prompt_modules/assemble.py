"""Assemble main Hypit prompt + applicable modules + structured run params."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .base import PromptAssembly
from .editing_controls import EditingControlsModule
from .localization import LocalizationModule

_ASSEMBLY = Path(__file__).resolve().parent.parent / 'assembly_prompt.txt'
_PLACEHOLDER = re.compile(r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}')

# Ordered registry. Add future modules here; each must declare a unique domain.
_REGISTRY = (
    EditingControlsModule(),
    LocalizationModule(),
)


def main_prompt_version(text: str | None = None) -> str:
    """Stable short hash of the on-disk main prompt body (content-addressed)."""
    body = text if text is not None else _ASSEMBLY.read_text(encoding='utf-8')
    digest = hashlib.sha256(body.encode('utf-8')).hexdigest()[:12]
    return f'assembly:{digest}'


def _studio_levels(manual: dict) -> str:
    """Mirror hypit_prompt._levels (kept local to avoid circular import)."""

    def read(name, default, low=0):
        if name not in manual or manual.get(name) is None:
            return default
        try:
            value = int(manual.get(name))
        except (TypeError, ValueError):
            return default
        value = max(low, min(100, value))
        value -= value % 5
        return max(low, value)

    animation = read('card_motion', 60)
    intensity = read('animation_intensity', 60, 5)
    motion = read('animation_motion', 80)
    density = read('animation_density', 70)
    line = (
        f"Доля анимации — {animation}% каждой минуты. "
        f"Интенсивность — {intensity}. "
        f"Движение — {motion}%. "
        f"Визуальная плотность — {density}%."
    )
    return f"--- STUDIO LEVELS ---\n{line}\n--- END STUDIO LEVELS ---"


def _as_dict(manual) -> dict:
    if manual is None:
        return {}
    if isinstance(manual, dict):
        return manual
    if hasattr(manual, 'model_dump'):
        return manual.model_dump()
    return dict(manual)


def _read_level(manual: dict, name: str, default: int, low: int = 0) -> int:
    if name not in manual or manual.get(name) is None:
        return default
    try:
        value = int(manual.get(name))
    except (TypeError, ValueError):
        return default
    value = max(low, min(100, value))
    value -= value % 5
    return max(low, value)


def _duration_s(manual: dict) -> float:
    if manual.get('duration') is not None:
        try:
            return max(0.0, float(manual['duration']))
        except (TypeError, ValueError):
            pass
    clips = manual.get('clips') or []
    end = 0.0
    for clip in clips:
        if isinstance(clip, dict):
            try:
                end = max(end, float(clip.get('end') or 0))
            except (TypeError, ValueError):
                continue
        else:
            try:
                end = max(end, float(getattr(clip, 'end', 0) or 0))
            except (TypeError, ValueError):
                continue
    return end


def _caption_rows(manual: dict) -> list[dict]:
    rows = []
    for caption in manual.get('captions') or []:
        if hasattr(caption, 'model_dump'):
            rows.append(caption.model_dump())
        elif isinstance(caption, dict):
            rows.append(caption)
    return rows


def _aligned_transcript(manual: dict) -> str:
    lang = _target_language(manual)
    prefer = {'en': ('en', 'original'), 'ru': ('ru', 'original', 'en'), 'zh': ('zh', 'original', 'en')}.get(
        lang, ('original', 'en', 'ru', 'zh')
    )
    lines = []
    for row in _caption_rows(manual):
        try:
            start = float(row.get('start') or 0)
            end = float(row.get('end') or 0)
        except (TypeError, ValueError):
            continue
        text = ''
        for key in prefer:
            candidate = ' '.join(str(row.get(key) or '').split())
            if candidate:
                text = candidate
                break
        if not text or end <= start:
            continue
        lines.append(f"{start:.2f}-{end:.2f}s  {text}")
    return '\n'.join(lines) if lines else '(transcript supplied in author markup for this run)'


def _voice_settings(manual: dict) -> str:
    parts = []
    if manual.get('voice_cleanup'):
        parts.append('voice cleanup on')
    if manual.get('normalize'):
        parts.append('loudness normalize on')
    voice = manual.get('voice') or manual.get('voiceId')
    if voice:
        parts.append(f'voice={voice}')
    mode = (manual.get('voice_resolution') or {}).get('mode') if isinstance(manual.get('voice_resolution'), dict) else None
    if mode:
        parts.append(f'mode={mode}')
    if not parts:
        parts.append('preserve original speech when language matches')
    return '; '.join(parts)


def _caption_settings(manual: dict) -> str:
    if manual.get('subtitles') is False:
        return 'captions off'
    size = manual.get('font_size') or 'medium'
    position = manual.get('position') or 'bottom'
    color = manual.get('color') or 'white'
    return f'on; size={size}; position={position}; color={color}'


def _music_settings(manual: dict) -> str:
    music = manual.get('music')
    if not music:
        return 'music off'
    if isinstance(music, dict):
        asset = music.get('asset_id') or music.get('id') or 'track'
        gain = music.get('gain_db')
        duck = music.get('duck')
        return f'on; asset={asset}; gain_db={gain}; duck={duck}'
    if hasattr(music, 'asset_id'):
        return f'on; asset={music.asset_id}; gain_db={getattr(music, "gain_db", None)}; duck={getattr(music, "duck", None)}'
    return 'music on'


def _picture_notes(manual: dict) -> str:
    for key in ('picture_notes', 'notes', 'direction', 'user_direction'):
        raw = manual.get(key)
        if raw:
            return ' '.join(str(raw).split())
    return '(none)'


def _target_language(manual: dict) -> str:
    raw = manual.get('language') or manual.get('host_language') or ''
    if not raw:
        return 'en'
    try:
        from ..language import resolve_locale, short_code
        return short_code(resolve_locale(raw))
    except Exception:
        return str(raw)


def prompt_bindings(manual=None, *, extras: dict | None = None) -> dict[str, str]:
    """Values for assembly_prompt.txt placeholders."""
    data = _as_dict(manual)
    width = int((extras or {}).get('width') or data.get('width') or 1080)
    height = int((extras or {}).get('height') or data.get('height') or 1920)
    duration = float((extras or {}).get('duration') or _duration_s(data) or 0)
    aspect = data.get('aspect') or (extras or {}).get('aspect_ratio')
    if not aspect or str(aspect).strip().lower() in {'original', 'source', 'auto'}:
        aspect = '9:16' if height > width else ('16:9' if width > height else '1:1')
    coverage = _read_level(data, 'card_motion', 60)
    intensity = _read_level(data, 'animation_intensity', 60, 5)
    bindings = {
        'aspect_ratio': str(aspect),
        'output_resolution': f'{width}x{height}',
        'target_language': _target_language(data),
        'output_duration': f'{duration:.3f}s' if duration else 'from source',
        'graphics_coverage_percent': str(coverage),
        'graphics_intensity': str(intensity),
        'voice_settings': _voice_settings(data),
        'caption_settings': _caption_settings(data),
        'music_settings': _music_settings(data),
        'picture_notes': _picture_notes(data),
        'source_video_reference': str((extras or {}).get('source_video_reference') or './source.mp4'),
        'speech_audio_reference': str(
            (extras or {}).get('speech_audio_reference')
            or './source.mp4 (embedded speech track; host-cleaned when voice cleanup runs)'
        ),
        'aligned_transcript': str((extras or {}).get('aligned_transcript') or _aligned_transcript(data)),
        'staged_asset_manifest': str(
            (extras or {}).get('staged_asset_manifest')
            or '(library assets are staged as ./motion/N.mp4 after selection; see STAGED LIBRARY FILES when present)'
        ),
    }
    if extras:
        for key, value in extras.items():
            if key in bindings and value is not None:
                bindings[key] = str(value)
    return bindings


def fill_assembly_template(body: str, manual=None, *, extras: dict | None = None) -> str:
    """Replace {{placeholders}} from Studio + staged extras. Unknown keys stay visible."""
    bindings = prompt_bindings(manual, extras=extras)

    def repl(match: re.Match) -> str:
        key = match.group(1)
        if key in bindings:
            return bindings[key]
        return match.group(0)

    return _PLACEHOLDER.sub(repl, body)


def assemble_hypit_prompt(manual=None, *, extras: dict | None = None) -> PromptAssembly:
    """Main prompt + modules + run params. Instructions stay separate from user content.

    The main ``assembly_prompt.txt`` body is the editorial contract. Modules may only
    refine their domain; conflicts with core constraints are listed explicitly.
    """
    data = _as_dict(manual)
    raw_body = _ASSEMBLY.read_text(encoding='utf-8').strip()
    main_ver = main_prompt_version(raw_body)
    main_body = fill_assembly_template(raw_body, data, extras=extras)
    parts = [main_body, _studio_levels(data)]

    attached = []
    conflicts: list[str] = []
    run_params: dict = {
        'mainPromptVersion': main_ver,
        'modules': [],
        'promptBindings': {
            k: prompt_bindings(data, extras=extras)[k]
            for k in (
                'aspect_ratio', 'output_resolution', 'target_language', 'output_duration',
                'graphics_coverage_percent', 'graphics_intensity',
            )
        },
    }
    for module in _REGISTRY:
        if not module.applicable(data):
            continue
        attachment = module.attach(data)
        attached.append(attachment)
        parts.append(attachment.instructions)
        conflicts.extend(attachment.conflicts)
        run_params['modules'].append({'id': attachment.id, 'version': attachment.version, 'domain': attachment.domain})
        run_params.update(attachment.run_params)

    module_index = (
        "--- PROMPT MODULES ---\n"
        f"mainPromptVersion: {main_ver}\n"
        "attached: "
        + (", ".join(f"{m.id}@{m.version}" for m in attached) if attached else "none")
        + "\n--- END PROMPT MODULES ---"
    )
    # Insert index after studio levels (parts[0]=main, parts[1]=levels).
    parts.insert(2, module_index)

    conflict_block = (
        "--- MODULE CONFLICTS ---\n"
        + ("none\n" if not conflicts else "\n".join(conflicts) + "\n")
        + "--- END MODULE CONFLICTS ---"
    )
    parts.append(conflict_block)

    # Structured params for the runtime — not freeform instructions.
    parts.append(
        "--- RUN PARAMS ---\n"
        + json.dumps(run_params, ensure_ascii=False, indent=2)
        + "\n--- END RUN PARAMS ---"
    )
    parts.append(
        "--- USER CONTENT ---\n"
        "Aligned transcript lines and staged library paths are filled into the "
        "OUTPUT / SOURCE MATERIAL placeholders above when available; author markup "
        "also carries timed speech for this run.\n"
        "--- END USER CONTENT ---"
    )

    return PromptAssembly(
        text="\n\n".join(parts),
        main_prompt_version=main_ver,
        modules=[{'id': m.id, 'version': m.version, 'domain': m.domain} for m in attached],
        run_params=run_params,
        conflicts=list(conflicts),
    )
