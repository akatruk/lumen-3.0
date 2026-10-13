# Lumen motion quality V17

**Date:** 2026-10-14
**Flag:** `MOTION_QUALITY_V17_ENABLED=0` by default.
**Code:** `backend/motion_quality_v17.py`. Runs inside `apply_semantic_motion` after the quote is classified. It does not replace Director and it does not train anything.

`VISUAL_INTELLIGENCE_ENABLED` and `VISUAL_EXPERIENCE_MEMORY_ENABLED` stay 0.

## Gate

| check | result |
| --- | --- |
| components | 15 `componentId` rows in `semantic_motion_v14.json` |
| variants | V14 gallery 15 + V15 gallery 30 |
| composer | `scene_composer_v16.py`, tests pass, origin1 V16 mp4 plays (60.05s) |
| locales | cards for en-US, ru-RU, zh-CN on one component |
| flags | V14, V15, V16, V17 default off |

## What it stores

Same PostgreSQL 16 database. Migration `004_motion_quality`.

| table | role |
| --- | --- |
| `motion_component_index` | purpose, input requirements, concepts, limitations, layouts. `vector(512)` only for `clip-ViT-B-32-multilingual-v1`. Not written into CLIP `asset_embeddings`. |
| `motion_experience` | one row per scene on a real `generation_history` id: component, version, layout, asset, caption box, speaker box, timing. No quality score. |
| `generation_reviews` / `scene_feedback` | existing UI. Not duplicated. |

A render does not load the embedding weights. `index_components(embed=False)` stores the text. Vectors are written only when `embed=True` is called offline.

## Ranking

A user scene flag counts only when `scene_feedback.scene_id` matches `motion_experience.scene_id` on the same generation.

| issue | class | effect after 5 different generations |
| --- | --- | --- |
| `poor_animation`, `visual_clutter` | implementation | that component loses one specificity point |
| `weak_composition`, `face_overlap` | layout | that layout is avoided |
| `irrelevant_media` | selection | listed, component not demoted |
| `caption_problem` | caption | listed, component not demoted |
| `factual_error` | fact | listed, component not demoted |

One review changes nothing. A database error returns `fallback: deterministic` and the video still renders.

## Origin1 technical A/B

Same transcript, en-US, no reviews in the evidence reader.

V16 deterministic and V17 with empty evidence selected the same five components: capital flow, shareholder network, ownership split, business comparison, document workflow. No second MP4 was rendered. A quality-learning A/B is not meaningful: `generation_reviews` user rows on lumen-fix = 0, `scene_feedback` = 0, `asset_feedback` = 0.

Keyword retrieval over the cards: 0.37 ms. `advise` with no rows: under 1 ms. Context on that call was 27 characters plus the preamble. No pgvector query ran, because no motion vectors were embedded.

## Benchmark

Ten scenarios, three locales, `humanJudgment` is null on every row. Lexicon match, not a preference score.

Real-estate and relocation quotes select no component. The Russian registration line mentions capital and does not match the English/Chinese document-step lexer, so it selects capital flow. The other eight scenarios match in en-US, ru-RU, and zh-CN, including China/Thailand once the Russian party names are accepted.

## Feedback UI

`QualityFeedback` is mounted in the Studio player when the project has a result (`frontend/src/main.tsx`). The built bundle contains "Quality feedback", "Save video rating", `poor_animation`, `POST /memory/reviews`, and `POST /memory/scenes`.

https://lumen-fix.universalgravity.org/ opens the sign-in wall. No review was submitted. Production still has zero user reviews.

## Tests

`pytest` `test_motion_quality_v17.py` `test_director_v14.py` `test_director_v15.py` `test_scene_composer_v16.py`: 36 pass.

## Git

Implementation commit recorded after commit on `feat/media-library-cleanup-v1`.

## Deployment

Not deployed in this file yet. Do not set `MOTION_QUALITY_V17_ENABLED`. Do not insert synthetic reviews.
