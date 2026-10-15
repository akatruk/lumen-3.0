---
name: lumen-deployment
description: >-
  Lumen 3.0 deploy on DigitalOcean lumen-test (not strom-v2). Media volume
  safety; rollback via FAST_PROJECT_CREATION / LLM_PROVIDER / REMOTION flags.
  Do not restart GPU jobs for app deploys.
---

# Deployment

## Lumen 3.0 (this repo)

- Host: `root@142.93.248.163` (`lumen-fix`) — `https://lumen-fix.universalgravity.org`
- App: `/opt/lumen-rebuild`
- Services: `lumen-web`, `lumen-worker` only
- Volume: `/mnt/volume_nyc1_1791446889637/` (100 GB)
- Flags: `FAST_PROJECT_CREATION_ENABLED=1`, `LLM_PROVIDER=none` (default) or `runpod` for local GPU Director
- CPU ASR: `ASR_MODEL=small`, `ASR_MODEL_CACHE=/mnt/volume_nyc1_1791446889637/lumen-asr`. Do not download Whisper weights onto the droplet root disk. Same-language projects keep original speech. No GPU for that path.
- Rollback create: `FAST_PROJECT_CREATION_ENABLED=0` + funded OpenRouter only if that track is allowed
- Remotion default (V5): keep `REMOTION_ENGINE_ENABLED=1` with `FAST_PROJECT_CREATION_ENABLED=1`
- Rollback Remotion: set `REMOTION_ENGINE_ENABLED=0` (Hypit legacy for non-«e»; «e» stays Remotion)
- **Never** deploy this tree to SSH `Host lumen` (188.166.244.242 / strom-v2)
- Heuristic Director at generation (`LLM_PROVIDER=none`) is **local_baseline** — never report as AI-directed quality
- **RunPod Director:** `LLM_PROVIDER=runpod` + `RUNPOD_LLM_MODEL=qwen2.5:7b-instruct`; Ollama on `lumen-hypit-4090` must be up. Fail-closed. See `reports/RUNPOD_DIRECTOR_V1.md`. Do not use DO Inference / OpenRouter for that track.
- **Experience memory:** reuse PostgreSQL 16 on this host with `postgresql-16-pgvector` `0.6.0-1`. Flags `VISUAL_EXPERIENCE_MEMORY_ENABLED=0` and `VISUAL_INTELLIGENCE_ENABLED=0` until en/ru/zh retrieval does not regress. No second Postgres, no Docker on this VM, no public 5432. Dumps: `/mnt/volume_nyc1_1791446889637/lumen-db-backups`. Doc: `docs/architecture/AI_MEMORY.md`.
- **Semantic motion V14:** `SEMANTIC_MOTION_V14_ENABLED=0` on lumen-fix until a visual QA sign-off. Do not flip it in production env as part of a code deploy.
- **Semantic motion V15:** `SEMANTIC_MOTION_V15_ENABLED=0` on lumen-fix. Do not flip it during deploy.
- **Scene composer V16:** `SCENE_COMPOSER_V16_ENABLED=0` on lumen-fix. Do not flip it during deploy.
- **Motion quality V17:** `MOTION_QUALITY_V17_ENABLED=0` on lumen-fix. Do not flip it during deploy. Do not insert synthetic reviews.
- **Motion design V18:** `MOTION_DESIGN_V18_ENABLED=0` on lumen-fix. Deploy the code with the flag unset. Do not turn it on in production env.

See `docs/architecture/DEPLOYMENT.md` and `reports/LUMEN_FAST_CREATE_PRODUCTION.md`.
