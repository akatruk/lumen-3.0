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
- Rollback create: `FAST_PROJECT_CREATION_ENABLED=0` + funded OpenRouter only if that track is allowed
- Rollback Remotion: disable `REMOTION_ENGINE_ENABLED`
- **Never** deploy this tree to SSH `Host lumen` (188.166.244.242 / strom-v2)
- Heuristic Director at generation (`LLM_PROVIDER=none`) is **local_baseline** — never report as AI-directed quality
- **RunPod Director:** `LLM_PROVIDER=runpod` + `RUNPOD_LLM_MODEL=qwen2.5:7b-instruct`; Ollama on `lumen-hypit-4090` must be up. Fail-closed. See `reports/RUNPOD_DIRECTOR_V1.md`. Do not use DO Inference / OpenRouter for that track.

See `docs/architecture/DEPLOYMENT.md` and `reports/LUMEN_FAST_CREATE_PRODUCTION.md`.
