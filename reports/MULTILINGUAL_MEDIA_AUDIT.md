# Multilingual media audit

**Date:** 2026-10-14  
**Manifest:** local `media/library/out/manifest.json` (production volume may be ahead; this count is the file in the repo).

| Metric | Value |
| --- | ---: |
| Assets | **692** |
| Images / video / motion / untyped | 614 / 35 / 28 / 15 |
| `conceptId` present before backfill | 240 |
| `tags_ru` present before backfill | 56 |
| `tags_zh` present before backfill | 56 |
| `localized` object before backfill | 0 |
| Status `approved` | 8 |
| Status unset | 668 |
| `needs_review` | 15 |

pgvector: `asset_embeddings` already exists. `VISUAL_INTELLIGENCE_ENABLED` stays **off**. Hybrid zh-CN Precision@5 previously dropped 0.90 → 0.82; this change does not turn hybrid on.

Director previously called `search_assets` without `locale` (`del locale`). `resolve_plan(..., language=)` now passes `project` language into retrieval.

Canonical ids are filenames/ids already in the manifest. No per-language media copies.
