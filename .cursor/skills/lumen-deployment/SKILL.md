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
- Flags: `FAST_PROJECT_CREATION_ENABLED=1`, `LLM_PROVIDER=none` (default)
- Rollback create: `FAST_PROJECT_CREATION_ENABLED=0` + `LLM_PROVIDER=openrouter` (funded)
- Rollback Remotion: disable `REMOTION_ENGINE_ENABLED`
- **Never** deploy this tree to SSH `Host lumen` (188.166.244.242 / strom-v2)
- Heuristic Director at generation (`LLM_PROVIDER=none`) is **local_baseline** — never report as AI-directed quality
- **Director V4:** needs DO Inference `MODEL_ACCESS_KEY` (or `GRADIENT_MODEL_ACCESS_KEY`) on lumen-test before `LLM_PROVIDER=digitalocean`. OpenRouter key alone is insufficient when OpenRouter is forbidden. See `reports/LUMEN_DIRECTOR_V4.md`.

See `docs/architecture/DEPLOYMENT.md` and `reports/LUMEN_FAST_CREATE_PRODUCTION.md`.
