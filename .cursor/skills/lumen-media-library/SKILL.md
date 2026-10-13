---
name: lumen-media-library
description: >-
  Lumen media library search, manifest fields, provenance, and quarantine.
  Use when resolving assets for Remotion or Director plans.
---

# Media library

Contract: [ADR-010](docs/architecture/adr/ADR-010-universal-multilingual-media-contract.md). Locales `en-US`, `ru-RU`, `zh-CN`. One `id`, one library. ADR-004 stays the retrieval decision.

New asset workflow: generate → quality review → canonical `id` → `conceptId` + semantic tags → RU/EN/ZH `localized` → embedding only if missing (`VISUAL_INTELLIGENCE_ENABLED` stays 0) → `scripts/validate_media_library.py --multilingual` → `ingest.register_approved` → Director. Failure sets `qualityStatus=PENDING_LOCALIZATION`. Do not publish. Retry updates the same id.

`validate_asset` is strict only when `multilingualContract=required` or `qualityStatus=production_ready`. Legacy rows are reported. Do not overwrite human `tags_ru` / `tags_zh`. Do not copy binaries per language. Quarantine: ADR-008. `premium_3d` needs `qualityGateApproved` before production. Motion presets are components, not image files.

- Search: `media/library/search.py` (additive changes only) — includes `tags_ru` / `tags_zh` and `locale`. Overlay: `localized_overlay.json`. Every approved asset must be discoverable in en-US / ru-RU / zh-CN. Do not duplicate files per language.
- Concepts: `concepts.py`, `concept_triggers.py`
- Manifest: `media/library/out/manifest.json` or DO `app-library` (authoritative on volume)
- Premium motion V4: `motion/premium/pm_*.webm`, recipes `recipes/premium-motion-v4-calibration.json`, report `reports/PREMIUM_MOTION_LIBRARY_V4.md`
- Premium Media Factory V5 batch1: `recipes/premium-media-factory-v5-batch1.json`, `scripts/index_premium_media_v5_batch1.py`, contact `media/library/out/contact-sheets/premium-media-v5-batch1.html`, report `reports/LUMEN_PREMIUM_MEDIA_FACTORY_V5.md`. GPU: `reports/PREMIUM_GPU_SELECTION.md` — do not resume EXITED pods without spend auth. **V5 `pmv5_bg_*` abstract plates are NOT environmental cinema** — keep files, do not promote as real-world backgrounds.
- **Cinematic Env Factory V6 batch1:** photoreal env stills + SVD I2V clips — plans `media/library/plans/cinematic-env-v6-*.jsonl`, recipe `recipes/cinematic-env-factory-v6-batch1.json`, indexer `scripts/index_cinematic_env_v6_batch1.py`, pod runner `scripts/run_cinematic_env_v6_on_pod.sh`, family `cinematic_environment`, storage `motion/cinematic-env-v6/{stills,clips}/`, reports `reports/CINEMATIC_ENV_FACTORY_V6*.md`. GPU: resume only `dznvwn90el5au4`. No OpenRouter image APIs.
- **Capital cinematic V7:** same family and ingest. Plans `media/library/plans/cinematic-env-v7-*.jsonl`, recipe `recipes/cinematic-env-factory-v7-batch1.json`, indexer `scripts/index_cinematic_env_v7_batch1.py` (calls `ingest.register_approved`). Store `visualGrounding` from reviewed frames, separate from `intent`. SVD-XT duration is ffprobe of the native frames (about 25 frames at 7 fps, ~3.6s), not a setpts 6s claim. Index only approved clips. Incomplete locales stay `PENDING_LOCALIZATION`. Do not overwrite V6 ids or human `tags_ru` / `tags_zh`. Report `reports/LUMEN_CAPITAL_CINEMATIC_V7.md`.
- Prefer `search_assets` over hardcoded filenames
- Fields: `qualityScore`, `sceneRoles`, `textSafeAreas`, `visualFamily`, `conceptId`, `tags_ru`, `tags_zh`
- Quarantine before delete (ADR-008). Do not wipe approved media.
- Alpha: VP9 `yuva420p` only; never claim H.264 has alpha.
- Premium 3D V1: `motion/premium3d/`, `models/premium3d/`, factory `media/library/3d_factory/`, index via `index_3d_assets.py --publish-binaries`. Family `premium_3d`.
- Experience embeddings: text (`tags` / `tags_ru` / `tags_zh`) via multilingual CLIP text model; images and video keyframes via CLIP vision, with `frame_seconds` on video rows. Stored in PostgreSQL `asset_embeddings` (view `media_embeddings`), not in the manifest file. `scripts/index_experience_assets.py --approved`. `VISUAL_INTELLIGENCE_ENABLED` (default off) runs keyword retrieval, then `media/library/rerank.py`. Cosine does not outrank a keyword hit. Reviewed intents: `media/library/relevance/intents_v2.json`. Do not treat tag overlap as ground truth.
- **Semantic motion V14 registry:** `media/library/catalogs/semantic_motion_v14.json` + `semantic_motion_registry.search_motion_components`. Motion components are not files and are not embedded into `asset_embeddings` (different vector space from CLIP). Deterministic en/ru/zh tag match is the selector while `VISUAL_INTELLIGENCE_ENABLED=0`. Recipes: `recipes/semantic-motion-v14.json`. V15 appends ten components to that same catalog (not a second database). Recipes: `recipes/semantic-motion-v15.json`. Quality gate: evidence on every graphic, face/caption safe layouts, no invented figures. CPU Remotion only.

Implemented selection gates (2026-10-11):
- Default search skips `quarantined` / `rejected` / `duplicate` / `corrupt` and holds `needs_review` / `unreviewed` / `restricted`.
- Blocks LOW/LEGACY/UNCERTAIN tiers and `motion/src/*.tsx` stubs before ranking.
- Semantic rank: situations/actions/relationships; query modes situational/literal/conceptual/decorative; eligibility before score.
- Same-source ban: `backend/director_media_rules.canonical_media_identity` — still + i2v of one plate cannot be main + inset together.
- No `passport.png` placeholder fallback in Director plans — empty FG → clean photo/typography; record `mediaGap`.
- Cleanup CLI: `scripts/media_library_cleanup_v1.py` (apply-quarantine / restore). Audits: `output/director-v3/media-quality-audit.md`, `semantic-selection-r4.md`, `preview-v3-r5-qa.md`.
