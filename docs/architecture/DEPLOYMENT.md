# Deployment

## CURRENT STATE

- DO VM (`ssh lumen`): production `strom-v2` + testing `strom-v2-testing`
- Domains: lumen.universalgravity.org / test.lumen.universalgravity.org
- Media volume: `/mnt/volume_nyc1_1791446889637/` (app-library, lumen-motion)
- Remotion runs where `motion/node_modules` exists (Mac/dev or volume-mounted server)
- RunPod: GPU asset gen only — do not restart pods for Remotion code deploys

## Practices

- Prefer testing stack for engine verification
- Env files are CI-overwrite — change secrets via GitHub, not hand-edit
- Rollback: set `REMOTION_ENGINE_ENABLED=false` → Hypit / prior path
- Never `docker compose down -v` on production without explicit wipe approval
