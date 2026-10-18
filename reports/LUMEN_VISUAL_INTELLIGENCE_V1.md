# Lumen visual intelligence V1

**Date:** 2026-10-14  
**Host:** lumen-fix `142.93.248.163` (`/opt/lumen-rebuild`)  
**Branch:** `feat/media-library-cleanup-v1`  
**Production flags:** `VISUAL_INTELLIGENCE_ENABLED=0`, `VISUAL_EXPERIENCE_MEMORY_ENABLED=0`, `FAST_PROJECT_CREATION_ENABLED=1`

pgvector stores and retrieves vectors. It does not train the embedding model. The Director reads a bounded advisory slice. Production search stays on the keyword ranker until the flag is turned on.

## Infrastructure

| Item | Measured |
| --- | --- |
| PostgreSQL | 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1) |
| `SELECT extversion FROM pg_extension WHERE extname='vector'` | **0.6.0** |
| Database | existing `lumen` on `/var/lib/postgresql/16/main` |
| Listen | `127.0.0.1:5432` and `::1` only |
| App health | `status=ok`, `fast_project_creation=true`, `visual_intelligence=false`, `pgvector=0.6.0` |
| Database size | 24 MB (`pg_database_size`) |
| `asset_embeddings` relation | 6528 kB |
| Migrations | `001_experience_memory`, `002_media_embeddings` |

No second database. Docker was not installed. strom-v2 and RunPod were not touched.

`media_embeddings` is a view over `asset_embeddings` (`embedding_version`, `created_at`, `frame_seconds`). Vectors are not duplicated.

## Embedding model

Verified cards, already cached on the volume:

| Modality | Model | Revision | Dim |
| --- | --- | --- | --- |
| Text (card lists `ru`, `en`, `zh-cn`, `zh-tw`) | `sentence-transformers/clip-ViT-B-32-multilingual-v1` | `58edf8cada9e` | 512 |
| Image and video keyframes | `sentence-transformers/clip-ViT-B-32` vision encoder | `327ab6726d33` | 512 |

These two models share one CLIP space. Other models are not queried together. Text vectors are not stored as image embeddings.

## Index

`scripts/index_experience_assets.py --approved` on the live library. Original files were not modified. Rejected, quarantined, held, low-quality, and `l3d_*` / `premium_3d` assets were skipped. Rerun skips rows that already have the same content hash and model.

| Modality | Rows |
| --- | --- |
| image | 273 |
| video_keyframe | 102 (all have `frame_seconds`) |
| text | 696 |
| **total** | **1071** |

Index job: 102.58 s, peak RSS 1355.8 MB, 0 errors. A generation request does not load these weights unless `VISUAL_INTELLIGENCE_ENABLED=1`. The render script drops the weights before Remotion starts.

## Retrieval benchmark

30 queries (10 concepts × en-US / ru-RU / zh-CN), including `family planning relocation`, `семья планирует переезд`, and `家庭计划移居国外`.

A hit counts as relevant when the asset's own `tags`, `tags_ru`, `tags_zh`, `situations`, or `actions` contain one of the concept tokens. That is the library's tag set, not a separate human rating and not a fabricated score.

| | Keyword | Hybrid |
| --- | ---: | ---: |
| Precision@5 | 0.8267 | **0.8400** |
| en-US | 0.80 | 0.80 |
| ru-RU | 0.78 | **0.90** |
| zh-CN | **0.90** | 0.82 |
| Diversity (unique `visualFamily` / top 5) | 0.3133 | 0.3267 |
| Duplicate asset rate | 0 | 0 |
| Cold latency | 0.34 s | 6.70 s (model load) |
| Warm median | 0.160 s | 0.244 s |

Vector-only SQL on `asset_embeddings`: 7.2 ms. Director context for `director_v5_original1` / "family planning relocation": 8 items, 1887 characters, 66 ms. Those items are library assets. There are no user-rated scenes to retrieve.

The three relocation queries were precision@5 = 1.0 in both modes. Hybrid changed which photos ranked under the same tags (Russian in particular).

Chinese precision fell. The production flag stays off.

## Hybrid search

`media/library/search.py` still runs the keyword, tag, `qualityScore`, `sceneRoles`, composition, `textSafeAreas`, and recent-use ranker. With the flag on it adds a cosine bonus from the precomputed vectors and drops unapproved experimental 3D. Rejected and quarantined assets stay out in both modes. If the model or database fails, the keyword list is returned.

## Generation memory and feedback

`generation_history` stores generation id, project id, director version, prompt version, model config, visual seed, selected assets, motion treatments, and a render **path**. The MP4 is not stored in PostgreSQL.

The enhanced render wrote `ordinary_director_60s`, seed `42`, path `/mnt/volume_nyc1_1791446889637/lumen-vi-work/pgvector-enhanced.mp4`.

`generation_reviews`, `scene_feedback`, and `asset_feedback` are empty. No ratings were invented. User rows and automated rows cannot share a score (check constraint).

## Director A/B

Source `director_v5_original1`, locale `en-US`, duration 60, seed 42, same transcript. Version B set `VISUAL_INTELLIGENCE_ENABLED=1` only in that process.

Both files: 60.053 s, 1080×1920, H.264, AAC, 30 fps, 28 `source_transcript` captions.

| Scene | Baseline plate | Enhanced plate |
| --- | --- | --- |
| hook | `people_consult_001` | `i2v_consult_001` |
| context | `rp_photo_055` | `rp_photo_082` |
| problem | `people_apartment_001` | `people_apartment_001` |
| residency | `i2v_consult_001` | `people_consult_001` |
| consult | `people_review_001` | `people_review_001` |
| beside | `i2v_review_001` | `rp_detail_034` |
| steps | none | `i2v_couple_001` |
| proof | `rp_detail_039` | `rp_object_043` |
| payoff | none | `pm_hero_deadline_001` |
| return | `people_door_001` | `pm_hero_growth_001` |

Six background plates changed. No `l3d_*` plate was selected. Baseline's premium-3D gate bound 0 variants (`not_production_ready`).

Frames at 8s, 18s, 28s, 40s, and 52s:

- 8s, speech about the company / capital investment: baseline shows a glass residential tower; enhanced shows an empty concrete interior. Both keep the Commit → Company arrow. The tower is the closer picture of a building. The empty room is a weaker match for that line.
- 18s, shareholder speech: both show a meeting and a three-node shareholder diagram. Baseline is the motion clip; enhanced is the still of a similar meeting.
- 28s, "foreign capital ratio … 49%": both use the same desk plate, Credit/Risk cards, and the same caption. The spoken 49% is on screen.
- 40s and 52s: speaker full frame in both, captions "Thailand requires paid-in capital" and "Thailand weights director authority…". Same lock graphic at 52s.

Local copies: `output/visual-intelligence/baseline.mp4`, `output/visual-intelligence/pgvector-enhanced.mp4`. They are not in Git.

## Tests

On lumen-fix against `lumen_qa`: `test_visual_intelligence_search.py`, `test_experience_memory.py`, `test_experience_embeddings.py` — 14 passed. Hybrid tests check that rejected and quarantined assets stay out, and that experimental 3D is dropped only when the flag is on.

`media/library/search.test.py` has two failures on the current manifest (`people_consult_001` still wins when marked recent; a route query returns suitcase 3D before a route clip). Those two fail on the previous `search.py` as well.

## Deployment

Web and worker restarted on lumen-fix after the code sync. Health stayed ok with both memory flags false and fast project creation on. Postgres was not rebuilt. Port 5432 stayed on localhost.

## Git

Implementation: `46af2eef1474a458bd67478c2e29b5cc601c35f5`  
Weights, dumps, `.env`, and the MP4s are not in the commit. The code running on lumen-fix matches that commit. This report's SHA line was added in the following docs commit.

## Limitations

- Chinese precision@5 on this tag set got worse (0.90 → 0.82). Overall precision rose only because Russian rose.
- The 60s A/B changes plates. The sampled frames do not show a clear picture-quality win. The 8s plate got less specific.
- No human ratings exist, so "successful scene" retrieval has nothing to return yet.
- CLIP loads on the first hybrid search in a process (~6.7 s, ~1.4 GB). Later searches in that process reuse it. Production does not load it while the flag is off.
- Root disk on the VM was about 5.1 GB free. Embedding weights stay on the 100 GB volume.
