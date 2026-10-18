"""Extensible Hypit prompt modules (main body + attachable domain refinements)."""

from .assemble import assemble_hypit_prompt, main_prompt_version
from .base import PromptAssembly
from .editing_controls import (
    PRESETS,
    apply_editing_controls,
    detect_preset,
    levels_from_manual,
)

__all__ = [
    'PromptAssembly',
    'assemble_hypit_prompt',
    'main_prompt_version',
    'PRESETS',
    'apply_editing_controls',
    'detect_preset',
    'levels_from_manual',
]
