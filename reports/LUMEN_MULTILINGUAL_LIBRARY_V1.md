# Universal multilingual media library V1

**Date:** 2026-10-14

## What landed

- One library, one id. Locale text lives in `tags_ru`, `tags_zh`, and `localized.{en-US,ru-RU,zh-CN}`.
- `scripts/backfill_multilingual_metadata.py` writes `media/library/localized_overlay.json` from **existing English tags** via `media/library/localize.py`. It does not invent unseen subjects and does not overwrite tags that are already set.
- `search.load` merges the overlay. `locale` is a ranking signal (no longer discarded). Longer query phrases match before short stems (`инвест` no longer eats `инвесторов`).
- `resolve_plan` / `plan_for_request` pass `language` into `search_assets`.
- New approvals: `media/library/ingest.py` `register_approved`.
- Hybrid / pgvector stay behind `VISUAL_INTELLIGENCE_ENABLED=0`.

## Counts (local manifest)

| | |
| --- | ---: |
| Assets | 692 |
| Overlay rows | 692 |
| Locale-complete after glossary fill | **521** |
| Still missing RU+ZH (tags outside glossary) | **171** |

Smoke (same pool, not a human rating):

| Query | Top ids |
| --- | --- |
| en `business investment meeting` | `re_inv_meeting`, `people_consult_001`, `pmv5_bm_capital_investment` |
| ru `деловая встреча инвесторов` | `re_inv_meeting`, `pmv5_bm_capital_investment`, `pmv5_bm_investment_flow` |
| zh `投资者商务会议` | `pmv5_bm_capital_investment`, `pmv5_bm_investment_flow`, `people_consult_001` |

`re_inv_meeting` is in the top 5 for all three.

## Benchmark

`media/library/relevance/intents_v2.json` has **33** catalog-inspection intents × 3 locales, not an independent 50×3 human panel. No new judgments were invented. Precision@5 / nDCG were **not** recomputed as human scores. Chinese hybrid stays off until a separate labeled eval recovers zh-CN.

## Gaps

- 171 assets have tags the glossary does not translate.
- Most rows have no `status: approved`; search still returns active/unset rows under existing gates.
- Embeddings were not rebuilt.
- origin1 three-locale media plans were not re-rendered (no paid dub).
- RunPod was not resumed.

## Deploy / git

Code + overlay sync to lumen-test `/opt/lumen-rebuild`. No strom-v2. No pod restart. SHA recorded in the commit.
