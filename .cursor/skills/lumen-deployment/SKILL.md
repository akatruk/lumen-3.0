---
name: lumen-deployment
description: >-
  DigitalOcean Lumen deploy, testing stack, media volume safety, rollback via
  REMOTION_ENGINE_ENABLED. Do not restart GPU jobs for Remotion deploys.
---

# Deployment

- SSH: `ssh lumen` (see personal skill `lumen-prod-ssh`)
- Testing: `strom-v2-testing` / test.lumen.universalgravity.org
- Volume: `/mnt/volume_nyc1_1791446889637/`
- Rollback: disable `REMOTION_ENGINE_ENABLED`; for create flow set `FAST_PROJECT_CREATION_ENABLED=0` + `LLM_PROVIDER=openrouter` (funded key)
- Env: `FAST_PROJECT_CREATION_ENABLED` (default true), `LLM_PROVIDER` (default `none`)
- Never mutate production without confirmation; prefer testing verify first
