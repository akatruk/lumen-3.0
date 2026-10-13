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
| Flag | `VISUAL_EXPERIENCE_MEMORY_ENABLED=0` and `VISUAL_INTELLIGENCE_ENABLED=0` until retrieval is turned on |
| Weights | `/mnt/volume_nyc1_1791446889637/embedding-models` (not in Git) |
| Dumps | `/mnt/volume_nyc1_1791446889637/lumen-db-backups` mode `0640` `lumen:postgres`, 14 days |

A second PostgreSQL was not added. Docker is not installed on this host. `deploy/docker-compose.memory-test.yml` is a localhost test stack (`pgvector/pgvector:0.6.0-pg16` on `127.0.0.1:55432`) and must not be started on lumen-fix.

## Tables

Created in the current schema (`public` in production) by migration `001_experience_memory`. Migration `002_media_embeddings` adds `frame_seconds` on `asset_embeddings`, generation seed/output path columns, `asset_feedback`, and the `media_embeddings` view (`embedding_version`, `created_at`). It does not create a second vector table. Existing application tables are not altered.

`engineering_memory`, `architecture_decisions`, `incidents`, `prompt_versions`, `model_configs`, `generation_history`, `generation_reviews`, `scene_feedback`, `asset_embeddings`, `scene_embeddings`.

`generation_reviews.review_source` is `user` or `automated`. A user row stores `user_quality_rating` (1–5) and a null QA score. An automated row stores `automated_qa_score` and a null user rating.

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

`VISUAL_INTELLIGENCE_ENABLED` also switches `media/library/search.py` to hybrid ranking: keyword and tag score, plus a cosine bonus from precomputed vectors, plus the existing `qualityScore`, `sceneRoles`, composition, `textSafeAreas`, and recent-use penalty. Rejected, quarantined, and held assets stay out. Unapproved experimental 3D is dropped only while this flag is on, so production keyword search is unchanged while it is off. If the model or database is unavailable, search returns the keyword ranking.

Index approved rasters and video keyframes with `scripts/index_experience_assets.py --approved`. That job is offline. A video generation request does not load the embedding weights unless the intelligence flag is on, and then the process keeps one copy. Embeddings are skipped when `(asset_id, modality, content_hash, embedding_model)` is already stored. Reindex after a model change by using a different `embedding_model` value; do not mix those vectors in one query.

## Backups

`deploy/postgres/backup_lumen_db.sh` writes `pg_dump -Fc` onto the media volume. `deploy/postgres/restore_drill.sh` restores into `lumen_restore_drill` and drops that database. It does not replace `lumen`. Dumps are not committed.

## API

Authenticated:

- `GET /api/memory/status`
- `GET /api/projects/{id}/memory/context`
- `POST /api/projects/{id}/memory/reviews` (user ratings only)

`GET /api/health` reports the flag and the pgvector version. It does not report credentials.
