# Visual experience memory V1

Date: 2026-10-14. Host: `lumen-fix` (`142.93.248.163`) `/opt/lumen-rebuild`.

## Decision

PostgreSQL **16.15** was already the application database (`dbname=lumen`, peer auth, data directory `/var/lib/postgresql/16/main`, listen `localhost` only). Docker is not installed on this host. A second PostgreSQL would split the app data and was not created.

pgvector came from the distro package `postgresql-16-pgvector` **0.6.0-1**. `CREATE EXTENSION vector` ran on `lumen` and `lumen_qa`.

`deploy/docker-compose.memory-test.yml` pins `pgvector/pgvector:0.6.0-pg16` for a localhost test stack (`127.0.0.1:55432`). It was not started here. Colima was down on the laptop, so the suite ran on `lumen_qa`.

## Runtime

| Item | Value |
| --- | --- |
| PostgreSQL | 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1) |
| pgvector | 0.6.0 |
| Service | `postgresql.service` (not a container) |
| Database | `lumen` on the local socket |
| Migration | `001_experience_memory` applied |
| Flag | `VISUAL_EXPERIENCE_MEMORY_ENABLED=0` |
| Text model | `sentence-transformers/clip-ViT-B-32-multilingual-v1` @ `58edf8cada9e398793dca955574a48cbb7f18be2` |
| Vision model | `sentence-transformers/clip-ViT-B-32` @ `327ab6726d33c0e22f920c83f2ff9e4bd38ca37f` |
| Dimension | 512 |
| Weights | `/mnt/volume_nyc1_1791446889637/embedding-models` |

Text, including ru / en / zh-cn / zh-tw, uses the multilingual student model. Images and video keyframes use the CLIP vision encoder. Those are the models named on the Hugging Face cards.

## Records

| Table | Rows |
| --- | --- |
| asset_embeddings | 42 (text 40, image 1, video_keyframe 1) |
| engineering_memory | 1 persistence canary |
| prompt_versions | 1 |
| model_configs | 1 |
| architecture_decisions, incidents, generation_history, generation_reviews, scene_feedback, scene_embeddings | 0 |

Indexed library sample: `icon_growth` and nearby tags, one raster image, one video keyframe. Binaries stayed on the media volume.

## Retrieval

Controlled test on `lumen_qa` (`test_experience_embeddings.py`): equivalent en-US / ru-RU / zh-CN queries for a profit arrow ranked that memory above a passport memory. A red keyframe embedded with the vision encoder was closer to a red image than to a blue image.

Live library query, flag still off, read-only:

| Locale | Top asset | Score |
| --- | --- | --- |
| en-US `rising profit arrow growth` | `icon_growth` | 0.8445 |
| ru-RU `стрелка роста прибыли` | `icon_growth` | 0.8529 |
| zh-CN `利润上升箭头` | `icon_success` | 0.8389 |

The Chinese query’s next hits were `icon_business` and `icon_entrepreneur`. `overridesSourceFacts` and `overridesSafetyRules` were false.

## Tests

`LUMEN_TEST_POSTGRES_URL=dbname=lumen_qa user=lumen host=/var/run/postgresql`

- `backend/tests/test_experience_memory.py` — 8 passed (migration, pgvector, write/read, separate user vs automated ratings, project isolation, bounded Director context, `pg_dump`/`pg_restore` of the test schema, RunPod prompt preamble)
- `backend/tests/test_experience_embeddings.py` — 2 passed

## Backup

| Item | Value |
| --- | --- |
| Script | `deploy/postgres/backup_lumen_db.sh` |
| Cron | `/etc/cron.d/lumen-pg-backup` at 03:15 UTC |
| Location | `/mnt/volume_nyc1_1791446889637/lumen-db-backups/` mode `750` `lumen:postgres` |
| Dump | `lumen-20261013T171254Z.dump` mode `640` (earlier `lumen-20261013T170850Z.dump` also restored) |
| Retention | 14 days |
| Restore drill | `lumen_restore_drill` had `vector 0.6.0`, `engineering_memory`, and 42 asset rows, then the database was dropped |
| Git | no dumps |

Extension restore uses the `postgres` superuser. The `lumen` role cannot `CREATE EXTENSION`.

## Persistence

`systemctl restart postgresql` kept `persistence-canary` and the 42 asset rows. Port 5432 stayed on `127.0.0.1` and `::1`. After `systemctl restart lumen-web lumen-worker`, health returned:

`visual_experience_memory.enabled=false`, `pgvector=0.6.0`, `llm_provider=none`, `fast_project_creation=true`.

No queued or running jobs. RunPod was not restarted. strom-v2 was not touched.

## Git

Commit SHA is stamped in the follow-up docs commit on `feat/media-library-cleanup-v1`.
