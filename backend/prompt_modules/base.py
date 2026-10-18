"""Attachable Hypit prompt modules.

Main body stays in ``backend/assembly_prompt.txt``. Modules only refine their
declared domain and must not rewrite core QUALITY ENFORCEMENT rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ModuleAttachment:
    """One module's contribution to the assembled prompt."""

    id: str
    version: str
    domain: str
    instructions: str
    conflicts: tuple[str, ...] = ()
    run_params: dict[str, Any] = field(default_factory=dict)


class PromptModule(Protocol):
    id: str
    version: str
    domain: str

    def applicable(self, manual: dict) -> bool:
        """True when this module should attach for the current run."""

    def attach(self, manual: dict) -> ModuleAttachment:
        """Build the instruction block + structured params for this domain."""


@dataclass
class PromptAssembly:
    """Full Hypit prompt plus reproducibility metadata."""

    text: str
    main_prompt_version: str
    modules: list[dict[str, Any]]
    run_params: dict[str, Any]
    conflicts: list[str]

    def job_fields(self) -> dict[str, Any]:
        """Fields to store on the create-video / render job payload."""
        return {
            'promptAssembly': {
                'mainPromptVersion': self.main_prompt_version,
                'modules': self.modules,
                'conflicts': self.conflicts,
                'runParams': self.run_params,
            }
        }
