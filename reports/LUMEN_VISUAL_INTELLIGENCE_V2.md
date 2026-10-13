# Visual Intelligence V2

Semantic reranking and human quality feedback. PostgreSQL 16.15 and pgvector 0.6.0 were left in place. Embeddings were not regenerated. RunPod was not restarted. No new library media was generated.

Both production flags stay off:

- `VISUAL_INTELLIGENCE_ENABLED=0`
- `VISUAL_EXPERIENCE_MEMORY_ENABLED=0`
- `FAST_PROJECT_CREATION_ENABLED=1`

Health after deploy: `status=ok`, `fast_project_creation=true`, `visual_experience_memory.enabled=false`, `visual_intelligence=false`, `pgvector=0.6.0`.

## Chinese regression

The V1 drop (zh-CN tag Precision@5 0.90 → 0.82) was not a broken multilingual encoder. The model card already lists `zh-cn`. Two separate things were mixed together.

1. Cosine overweight. Hybrid search added `bonus * 3` on a keyword hit and `bonus * 4` on a vector-only hit above 0.28. For `税务居民`, that replaced consultation and residency photographs with deadline and capital-investment motion. Russian keyword coverage was weaker, so the same bonus raised ru-RU (0.78 → 0.90). English stayed 0.80.

2. A bad relevance token. For `签证居留`, keyword search returned unapproved `l3d_*` plates. The legacy scorer counts those as relevant. The assets that actually match a visa/residence line are tagged `residency application`. Search expands that to `residence` / `permit` (confirmed on `rp_photo_035`). The legacy scorer looks for the raw substring `residence` and does not match `residency`, so it scores those photographs as misses.

V2 does not add cosine onto the keyword score, and it drops a vector-only neighbor. Unapproved 3D stays out of the intelligence path only.

## Retrieval

Legacy tag overlap, same 30 queries as V1. This is not ground truth.

| | Precision@5 | en-US | ru-RU | zh-CN | median latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| Keyword | 0.8267 | 0.80 | 0.78 | 0.90 | 0.154s |
| Rerank | 0.8333 | 0.80 | 0.84 | 0.86 | 0.212s |

zh-CN is still 0.86 against 0.90 on that scorer. The visa query is the gap: keyword top-5 are `l3d_*` (legacy score 0.6); rerank returns `rp_photo_035`, `rp_photo_036`, `rp_photo_065`, `rp_photo_066`, `rp_detail_023` (legacy score 0.0). Those photographs are the residency-application plates. Duplicate rate 0 either way. Diversity 0.2898 → 0.2798.

Reviewed labels are in `media/library/relevance/intents_v2.json` (30 intents, en-US / ru-RU / zh-CN, grades `highly_relevant` / `relevant` / `weakly_relevant` / `irrelevant`). They are catalog inspections, not user scores. Unlabeled hits are excluded. 43 of the top-5 slots were labeled.

| | Precision@5 | nDCG@5 | en-US | ru-RU | zh-CN |
| --- | ---: | ---: | ---: | ---: | ---: |
| Keyword | 0.6313 | 0.7023 | 0.6154 | 0.6667 | 0.6167 |
| Rerank | 0.8118 | 0.8467 | 0.7500 | 0.9000 | 0.7963 |

nDCG@5 by locale, keyword → rerank: en 0.7308 → 0.8011, ru 0.7024 → 0.9206, zh 0.6651 → 0.8256.

That reviewed gain is real on the labeled subset and too thin to turn the flag on. `scripts/label_relevance.py` records another judgment. It does not write `generation_reviews`.

## Domain label `residency`

`residency` is an internal beat id in `visual_variation.SCENES`. On `director_v5_original1` the search string after V11 is `corporate boardroom shareholders meeting`. The id is not the query. The template defaults (`family home doorway relocation`, `residence permit application desk`) are immigration text. V11 already replaces them when the transcript is investment. `query_respecting_source` is a second check at fill time: if those concepts are investment and the query is still an immigration template, the spoken evidence replaces it.

## Rerank

Stage 1: up to 24 keyword hits, plus vector-only neighbors when the keyword list is short. Stage 2 drops a neighbor with no keyword overlap, drops a passport / suitcase / empty-apartment asset on shareholder or capital speech, then keeps keyword order. Quality, scene role, composition, text-safe area, and recent use stay inside that keyword score.

An asset penalty of 0.35 applies only after `irrelevant_media` on two different generation ids. One low video score does not move an asset. `caption_problem`, `poor_animation`, `visual_clutter`, `face_overlap`, `weak_composition`, and `factual_error` do not either. Production feedback tables were empty, so this term was zero during the benchmark.

## Human feedback

`generation_reviews.user_quality_rating` is 1–10. Optional `dimension_ratings`: story, media relevance, motion, captions, composition, audio, overall. A scene row can store `scene_id`, `timestamp_seconds`, `asset_ids`, motion treatment, and one of the issue categories above with a null rating. Migration `003_quality_feedback`. The player form posts to `POST /api/projects/{id}/memory/reviews` and `POST /api/projects/{id}/memory/scenes`. Both require a real `generation_history` id. No synthetic reviews were inserted into `lumen`.

`bounded_context` prefers verified reviews and scene flags for the same project, drops a scene match below cosine 0.30, and still will not override the transcript. Retrieval stays off while the flags are off. The review endpoints stay available.

## A/B

`director_v5_original1`, en-US, seed 42, 60s, same transcript, same scene queries, Remotion. A is keyword. B refilled backgrounds on A's frozen plan with intelligence on in that process only.

| | SHA-256 prefix | size | duration | captions |
| --- | --- | ---: | ---: | ---: |
| A `v2-keyword.mp4` | `19b46668496b4920` | 28894016 | 60.053s | 28 |
| B `v2-rerank.mp4` | `ddb4e0b7ae3d8fc5` | 29363030 | 60.053s | 28 |

Both 1080×1920, h264 + aac, 30 fps. A matches the V1 keyword file hash. Queries are identical. Three background ids changed:

| Scene | Query | A | B |
| --- | --- | --- | --- |
| residency | corporate boardroom shareholders meeting | `i2v_consult_001` | `rp_fg_018` |
| consult | financial analysis spreadsheet desk | `people_review_001` | `i2v_review_001` |
| beside | corporate ownership structure diagram desk | `i2v_review_001` | `pm_scene_approval_001` |

Frames at 18s and 24s, caption "The shareholder responsibility…" / "Ordinary Thai companies usually need at least three": A shows two people at a table under the shareholder diagram. B shows an empty glass boardroom under the same diagram. The empty room is a worse match. `rp_fg_018` is tagged `investor meeting foreground`; the picture is an empty room. Frames at 28s and 33s are the same desk and the same "less than 49%" caption; the consult swap is the still and the motion of that desk, not a new subject.

This is not a visual win. The flag stays off.

## Tests

Server, `lumen_qa`: 25 passed (`test_experience_memory`, `test_semantic_rerank`, `test_visual_intelligence_search`, `test_director_v11`). The rating and scene-flag rows are in the test schema only.

## Deploy

Host `142.93.248.163`, app `/opt/lumen-rebuild`. `lumen-web` and `lumen-worker` restarted. Postgres, RunPod, strom-v2, and media binaries were not touched.

Git SHA: `42e1a022a22de1c8880b91e5a83128402fa050cb` on `feat/media-library-cleanup-v1`.
