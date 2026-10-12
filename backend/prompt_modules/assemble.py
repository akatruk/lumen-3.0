"""Assemble main Hypit prompt + applicable modules + structured run params."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .base import PromptAssembly
from .editing_controls import EditingControlsModule
from .localization import LocalizationModule

_ASSEMBLY = Path(__file__).resolve().parent.parent / 'assembly_prompt.txt'

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


def assemble_hypit_prompt(manual=None) -> PromptAssembly:
    """Main prompt + modules + run params. Instructions stay separate from user content.

    The main ``assembly_prompt.txt`` body is never rewritten here. Modules may only
    refine their domain; conflicts with core constraints are listed explicitly.
    """
    data = _as_dict(manual)
    main_body = _ASSEMBLY.read_text(encoding='utf-8').strip()
    main_ver = main_prompt_version(main_body)
    parts = [main_body, _studio_levels(data)]

    attached = []
    conflicts: list[str] = []
    run_params: dict = {
        'mainPromptVersion': main_ver,
        'modules': [],
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
    # User / transcript content is authored into SVML separately (author_source).
    parts.append(
        "--- USER CONTENT ---\n"
        "Viewer transcript lines and timed captions are supplied in the author "
        "markup picture blocks for this run — not duplicated here.\n"
        "--- END USER CONTENT ---"
    )

    return PromptAssembly(
        text="\n\n".join(parts),
        main_prompt_version=main_ver,
        modules=[{'id': m.id, 'version': m.version, 'domain': m.domain} for m in attached],
        run_params=run_params,
        conflicts=list(conflicts),
    )
