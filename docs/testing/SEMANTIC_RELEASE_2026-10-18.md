# Semantic deployment acceptance — 2026-10-18

## Current supported path

New upload → source transcript → explicit SemanticOpenRouterDirectorProvider → absolute passage bounds → Remotion → playback/download. Production activation uses SEMANTIC_PLANNER_REQUIRED=1 with the existing OpenRouter key. LLM_PROVIDER remains unchanged; it is not the semantic override. No local text model or GPU is started.

Corrections: old heuristic analysis cannot satisfy semantic activation; semantic passages bypass heuristic ordinal retiming; requested duration clips later passages rather than extending or truncating the whole video from the last passage; short cuts use the uploaded source instead of speaker.mp4; optional card explanations typecheck.

## Evidence

- Local and isolated Linux backend selection: 76 passed, 2 skipped. Asset-selection unit tests now provide their own file-presence fixture rather than depending on the server's mounted media inventory.
- Frontend build and Russian localization passed.
- Motion TypeScript passed; 112 motion tests passed using existing local media fixtures.
- Real browser upload succeeded in separate SQLite storage under /tmp/lumen-release-JWEIRI62.
- A 30s Remotion render and a second 10s render completed; both reported semantic_openrouter. Playback after reload and actual downloaded files were checked; the player and download hashes matched.
- 30s SHA-256: 4c4f80fbb219a8790ef6456c9f9227b1d7706f066e34286239aeaf212c1472fb.
- 10s SHA-256: 78cf67ba84f0cdd1fdf2bafd1a516de9665f903a27fafc8b1e31177275e13cda.

ASR and semantic responses in acceptance are synthetic fixtures. HTTP, persistence, jobs, Remotion, source media, playback and downloads are real. This is not a live LLM/ASR quality or creative-quality certification. No provider generation call or paid infrastructure was started for acceptance.

The earlier full legacy suite recorded 97 failures, including tests for retired Studio mutation endpoints and unavailable media fixtures. It has not been made wholly green by this release. The verified scope is the current Create Video path above, not every legacy editing/voice/music surface.

## Deployment safeguards

Backup: /mnt/volume_nyc1_1791446889637/backups/pre-semantic-deploy-20261018T125602Z (code/config archive and PostgreSQL dump). Deployment requires no queued/running production jobs, replaces backend and renderer sources with the Git revision, preserves project media and the mounted library, preserves memory limits and model caches, and restarts only Lumen web/worker/ASR. Runtime file hashes are recorded in DEPLOY_MANIFEST.json. Failed startup restores the prior directories and configuration.
