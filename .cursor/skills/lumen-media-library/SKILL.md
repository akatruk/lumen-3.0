---
name: lumen-media-library
description: >-
  Lumen media library search, manifest fields, provenance, and quarantine.
  Use when resolving assets for Remotion or Director plans.
---

# Media library

- Search: `media/library/search.py` (additive changes only) — includes `tags_ru` / `tags_zh`
- Concepts: `concepts.py`, `concept_triggers.py`
- Manifest: `media/library/out/manifest.json` or DO `app-library` (authoritative on volume)
- Premium motion V4: `motion/premium/pm_*.webm`, recipes `recipes/premium-motion-v4-calibration.json`, report `reports/PREMIUM_MOTION_LIBRARY_V4.md`
- Prefer `search_assets` over hardcoded filenames
- Fields: `qualityScore`, `sceneRoles`, `textSafeAreas`, `visualFamily`, `conceptId`, `tags_ru`, `tags_zh`
- Quarantine before delete (ADR-008). Do not wipe approved media.
- Alpha: VP9 `yuva420p` only; never claim H.264 has alpha.
- Premium 3D V1: `motion/premium3d/`, `models/premium3d/`, factory `media/library/3d_factory/`, index via `index_3d_assets.py --publish-binaries`. Family `premium_3d`.

Implemented selection gates (2026-10-11):
- Default search skips `quarantined` / `rejected` / `duplicate` / `corrupt` and holds `needs_review` / `unreviewed` / `restricted`.
- Blocks LOW/LEGACY/UNCERTAIN tiers and `motion/src/*.tsx` stubs before ranking.
- Semantic rank: situations/actions/relationships; query modes situational/literal/conceptual/decorative; eligibility before score.
- Same-source ban: `backend/director_media_rules.canonical_media_identity` — still + i2v of one plate cannot be main + inset together.
- No `passport.png` placeholder fallback in Director plans — empty FG → clean photo/typography; record `mediaGap`.
- Cleanup CLI: `scripts/media_library_cleanup_v1.py` (apply-quarantine / restore). Audits: `output/director-v3/media-quality-audit.md`, `semantic-selection-r4.md`, `preview-v3-r5-qa.md`.
