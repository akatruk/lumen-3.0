"""Measurable Director media rules shared by planner + Remotion validator.

Docs brief: docs/prompts/cinematic-director-v3-quality-recovery.md (humans/agents).
Hypit model brief: backend/assembly_prompt.txt via hypit_prompt.py.
Remotion plan path: visual_variation.resolve_plan → remotion_engine.resolve_scene_plan.
"""
from __future__ import annotations

import re
from pathlib import Path

# Strip library family prefixes / numeric suffixes so still + i2v of one plate match.
_PREFIX = re.compile(r'^(?:people_|i2v_|still_|re_|imm_|hypit_|v2_|rp_|doc_)')
_SUFFIX = re.compile(r'_\d+$')


def canonical_media_identity(asset_id: str | None) -> str | None:
    """Stable identity for same-source detection. Derivatives share one key."""
    if not asset_id:
        return None
    raw = str(asset_id).strip().lower()
    if not raw:
        return None
    if raw in ('passport.png', 'passport') or raw.endswith('/passport.png'):
        return 'passport'
    stem = Path(raw).stem
    stem = _PREFIX.sub('', stem)
    stem = _SUFFIX.sub('', stem)
    return stem or raw


def same_media_source(a: str | None, b: str | None) -> bool:
    ca, cb = canonical_media_identity(a), canonical_media_identity(b)
    return bool(ca and cb and ca == cb)


def sanitize_scene_layers(scene: dict) -> dict:
    """Ban accidental same-source as main plate AND optional inset/foreground.

    Clears foreground when it shares canonical identity with background.
    Preserves scene schema keys; records rejection reason.
    """
    out = dict(scene)
    background = dict(out.get('background') or {})
    foreground = dict(out.get('foreground') or {})
    rejected = list(out.get('rejected') or [])
    bg_id = background.get('assetId')
    fg_id = foreground.get('assetId')
    if same_media_source(bg_id, fg_id):
        foreground['assetId'] = None
        foreground['file'] = None
        if 'staged' in foreground:
            foreground['staged'] = None
        if 'same_source_inset' not in rejected:
            rejected.append('same_source_inset')
    out['background'] = background
    out['foreground'] = foreground
    out['rejected'] = rejected
    # Representation must stay present for schema consumers.
    if 'representation' not in out:
        out['representation'] = scene.get('representation') or 'presenter'
    return out


def sanitize_plan_scenes(scenes: list) -> list:
    return [sanitize_scene_layers(scene) for scene in scenes or []]
