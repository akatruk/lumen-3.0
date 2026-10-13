# Visual experience memory

PostgreSQL stores structured memory. pgvector retrieves it. The media volume stores binary assets. Director receives a bounded advisory slice. RunPod stays GPU compute.

## Where it runs

| Item | Value |
| --- | --- |
| Host | `lumen-fix` `142.93.248.163` |
| Database | Existing PostgreSQL **16.15** database `lumen` |
| Data directory | `/var/lib/postgresql/16/main` |
| Role | `lumen` (NOSUPERUSER, peer auth on the local socket) |
| Extension | `vector` **0.6.0** from `postgresql-16-pgvector` `0.6.0-1` |
| Listen | `localhost` only. Port 5432 is not public |
| Flag | `VISUAL_EXPERIENCE_MEMORY_ENABLED=0` and `VISUAL_INTELLIGENCE_ENABLED=0` until retrieval passes the locale gate (ADR-010). Do not rebuild unchanged embeddings. |
| Weights | `/mnt/volume_nyc1_1791446889637/embedding-models` (not in Git) |
| Dumps | `/mnt/volume_nyc1_1791446889637/lumen-db-backups` mode `0640` `lumen:postgres`, 14 days |

A second PostgreSQL was not added. Docker is not installed on this host. `deploy/docker-compose.memory-test.yml` is a localhost test stack (`pgvector/pgvector:0.6.0-pg16` on `127.0.0.1:55432`) and must not be started on lumen-fix.

## Tables

Created in the current schema (`public` in production) by migration `001_experience_memory`. Migration `002_media_embeddings` adds `frame_seconds` on `asset_embeddings`, generation seed/output path columns, `asset_feedback`, and the `media_embeddings` view (`embedding_version`, `created_at`). Migration `003_quality_feedback` adds optional 1–10 dimension scores on `generation_reviews` and scene id, timestamp, asset ids, and issue category on `scene_feedback`. It does not create a second vector table. Existing application tables are not altered.

`engineering_memory`, `architecture_decisions`, `incidents`, `prompt_versions`, `model_configs`, `generation_history`, `generation_reviews`, `scene_feedback`, `asset_embeddings`, `scene_embeddings`.

Migration `004_motion_quality` adds `motion_component_index` and `motion_experience` in the same database. Motion text uses `vector(512)` and `sentence-transformers/clip-ViT-B-32-multilingual-v1` only. Those rows are not written into `asset_embeddings`, so they are not queried as CLIP image neighbors. A render does not load the embedding weights. `MOTION_QUALITY_V17_ENABLED` defaults to 0. Five agreeing user scene flags are required before a component or a layout is demoted. A caption miss or a fact mismatch does not demote the component. No review means the deterministic selector is unchanged.

`generation_reviews.review_source` is `user` or `automated`. A user row stores `user_quality_rating` (1–10) and a null QA score. Optional `dimension_ratings` may hold story, media relevance, motion, captions, composition, audio, and overall. An automated row stores `automated_qa_score` and a null user rating. A scene flag (`irrelevant_media`, `poor_animation`, `visual_clutter`, `caption_problem`, `face_overlap`, `weak_composition`, `factual_error`) can be stored with a null rating. Only `irrelevant_media` on two generations applies an asset penalty. A low video score does not downrank an asset.

Rows are project-scoped. Library asset embeddings use `scope=library` and a null `project_id`. Retrieval never returns another project's rows.

## Embeddings

| Modality | Model | Dimension |
| --- | --- | --- |
| Text, including ru-RU, en-US, zh-CN | `sentence-transformers/clip-ViT-B-32-multilingual-v1` | 512 |
| Images | `sentence-transformers/clip-ViT-B-32` (CLIP vision encoder) | 512 |
| Video | Sampled keyframes through the same CLIP vision encoder, with `frame_seconds` | 512 |

The multilingual model is a DistilBERT student aligned into CLIP space. Its card lists `ru`, `en`, `zh-cn`, and `zh-tw`. It is not used as an image encoder. Each stored vector records `embedding_model`, `model_version`, `vector_dimension`, `asset_id` or memory id, and `content_hash`.

## Director

When either flag is on, `plan_for_request` and the RunPod/OpenRouter director prompts call `bounded_context`. The payload is at most 8 items and 3500 characters. Hits can include a successful user-rated scene, a failed user-rated scene, an incident, and a library asset. Unrated generations are not labeled successful. The preamble says memory is untrusted, must not override source transcript facts or production safety rules, and must not copy an unrelated scene. Scene records are not rewritten from memory. `l3d_*` embeddings are not retrieved. When both flags are off, those call sites do not read or write memory.

`VISUAL_INTELLIGENCE_ENABLED` switches search to two stages. Stage 1 retrieves up to 24 keyword hits and may also pass vector-only neighbors. Stage 2 (`media/library/rerank.py`) drops a neighbor that does not match the spoken words, drops a domain clash, then orders by the keyword score. Cosine does not add or outrank a hit. Quality, scene role, composition, text-safe area, and recent use stay inside the keyword score. A repeated `irrelevant_media` flag is a small extra penalty. Rejected, quarantined, and held assets stay out. Unapproved experimental 3D is dropped only while this flag is on, so production keyword search is unchanged while it is off. If the model or database is unavailable, search returns the keyword ranking.

Before planning, `bounded_context` prefers verified user reviews and scene flags for the same project. A scene match below cosine 0.30 is dropped. Memory stays advisory and does not replace the source transcript. The scene id `residency` is an internal beat name. Investment speech replaces its immigration default query before search.

Index approved rasters and video keyframes with `scripts/index_experience_assets.py --approved`. That job is offline. A video generation request does not load the embedding weights unless the intelligence flag is on, and then the process keeps one copy. Embeddings are skipped when `(asset_id, modality, content_hash, embedding_model)` is already stored. Reindex after a model change by using a different `embedding_model` value; do not mix those vectors in one query.

## Backups

`deploy/postgres/backup_lumen_db.sh` writes `pg_dump -Fc` onto the media volume. `deploy/postgres/restore_drill.sh` restores into `lumen_restore_drill` and drops that database. It does not replace `lumen`. Dumps are not committed.

## API

Authenticated:

- `GET /api/memory/status`
- `GET /api/projects/{id}/memory/context` (empty unless a retrieval flag is on)
- `GET /api/projects/{id}/memory/generations`
- `POST /api/projects/{id}/memory/reviews` (user rating 1–10, optional dimensions; requires a real generation id)
- `POST /api/projects/{id}/memory/scenes` (scene flag; requires a real generation id)

Review and scene writes stay available while retrieval flags are off. They do not insert a generation.

`GET /api/health` reports the flag and the pgvector version. It does not report credentials.
