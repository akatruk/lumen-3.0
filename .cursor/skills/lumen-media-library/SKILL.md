---
name: lumen-media-library
description: >-
  Lumen media library search, manifest fields, provenance, and quarantine.
  Use when resolving assets for Remotion or Director plans.
---

# Media library

- Search: `media/library/search.py` (additive changes only)
- Concepts: `concepts.py`, `concept_triggers.py`
- Manifest: `media/library/out/manifest.json` or DO `app-library`
- Prefer `search_assets` over hardcoded filenames
- Fields: `qualityScore`, `sceneRoles`, `textSafeAreas`, `visualFamily`, `conceptId`
- Quarantine before delete (ADR-008). Do not wipe approved media.
