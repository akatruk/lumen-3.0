# Deployment

## CURRENT STATE — Lumen 3.0 (confirmed)

| Item | Value |
| --- | --- |
| **Production/test host** | `root@142.93.248.163` — hostname `lumen-fix` |
| **Public origin** | `https://lumen-fix.universalgravity.org` |
| **App directory** | `/opt/lumen-rebuild` |
| **Services** | `lumen-web.service` (uvicorn `:8018`), `lumen-worker.service` |
| **Data / media volume** | `/mnt/volume_nyc1_1791446889637/` (100 GB) — `lumen/`, `app-library/`, `hypit-home/`, `lumen-motion/`, `cache/` |
| **Library symlink** | `/opt/lumen-rebuild/media/library/out` → `app-library` |
| **Deploy marker** | `/opt/lumen-rebuild/DEPLOY_SHA.txt` |
| **Backups** | `/opt/lumen-rebuild/backups/` |

**Not this product:** SSH `Host lumen` → `188.166.244.242` runs MorcaLabs **strom-v2** (lumen.universalgravity.org / test.lumen…). Do **not** deploy lumen-3.0 code there.

## Method

1. Local: `git archive` / rsync of `backend/`, `frontend/dist/`, `motion/` (as needed), docs/skills.
2. Remote backup: `tar` of `/opt/lumen-rebuild/{backend,frontend/dist,motion}` → `backups/`.
3. Sync files; write `DEPLOY_SHA.txt`.
4. Ensure env flags (names only — never commit secrets):
   - `FAST_PROJECT_CREATION_ENABLED=1`
   - `LLM_PROVIDER=none` (or `openrouter` for LLM Director at **Create video** only)
   - `TRANSCRIPT_PROVIDER=auto`
5. `systemctl restart lumen-web lumen-worker` only.
6. Health: `curl http://127.0.0.1:8018/api/health`
7. **Do not** restart RunPod / GPU pods for app deploys.
8. Experience memory stays on the existing PostgreSQL 16 + `postgresql-16-pgvector` `0.6.0-1`. Do not start `deploy/docker-compose.memory-test.yml` here. `VISUAL_EXPERIENCE_MEMORY_ENABLED=0`. Dumps: `deploy/postgres/backup_lumen_db.sh` → volume `lumen-db-backups/`. See `docs/architecture/AI_MEMORY.md`.
9. Premium Media Factory V5: deploy code + recipe/manifest rows only; atomic publish under volume `app-library/` — never overwrite `status=approved` binary masters. Generative masters require explicit GPU spend auth (`reports/PREMIUM_GPU_SELECTION.md`).

## Environment requirements

- Python venv at `/opt/lumen-rebuild/venv`
- FFmpeg with ASS
- Volume mounts via systemd drop-ins (`data-volume.conf`, `volume.conf`)
- Optional: `OPENROUTER_API_KEY` only if `LLM_PROVIDER=openrouter`
- Director V4 (non-OpenRouter): requires `MODEL_ACCESS_KEY` or `GRADIENT_MODEL_ACCESS_KEY` for `https://inference.do-ai.run/v1` — **not present** on lumen-test as of 2026-10-12 (`reports/LUMEN_DIRECTOR_V4.md`)
- RunPod keys only for Hypit GPU picture jobs

## Rollback

1. Restore previous tree from `backups/<stamp>.tar.gz`
2. Or set `FAST_PROJECT_CREATION_ENABLED=0` + `LLM_PROVIDER=openrouter` (funded key) for legacy enqueue-on-create
3. `systemctl restart lumen-web lumen-worker`
4. Confirm `DEPLOY_SHA.txt` / health

## Practices

- Prefer lumen-test for verification before any other host
- Never `docker compose down -v` on strom-v2 for lumen-3.0 work
- Rollback Remotion: `REMOTION_ENGINE_ENABLED=false` (Hypit fallback)
