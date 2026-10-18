# Remotion Professional Video Engine V1

Date: 2026-10-11. Repo: `lumen-3.0`.

## Verdict

**PARTIAL PASS** — architecture, skills, engine, Director integration, tests, local 20s MP4, and **lumen-test deploy** (`142.93.248.163`) are done with flag **off**. Remotion is **not** default for every project. Remaining: non-«e» Remotion create-video, EN/ZH create-video → Remotion.

## Architecture

Docs:

- `docs/architecture/VIDEO_PIPELINE.md`
- `docs/architecture/REMOTION_ENGINE.md`
- `docs/architecture/MEDIA_LIBRARY.md`
- `docs/architecture/AI_DIRECTOR.md`
- `docs/architecture/MULTILINGUAL_PIPELINE.md`
- `docs/architecture/RENDERING_AND_AUDIO.md`
- `docs/architecture/DEPLOYMENT.md`
- ADRs `docs/architecture/adr/ADR-001` … `ADR-008`

## Skills

| Skill | Path |
| --- | --- |
| lumen-architecture | `.cursor/skills/lumen-architecture/SKILL.md` |
| lumen-remotion | `.cursor/skills/lumen-remotion/SKILL.md` |
| lumen-motion-design | `.cursor/skills/lumen-motion-design/SKILL.md` |
| lumen-director | `.cursor/skills/lumen-director/SKILL.md` |
| lumen-media-library | `.cursor/skills/lumen-media-library/SKILL.md` |
| lumen-multilingual | `.cursor/skills/lumen-multilingual/SKILL.md` |
| lumen-render-qa | `.cursor/skills/lumen-render-qa/SKILL.md` |
| lumen-deployment | `.cursor/skills/lumen-deployment/SKILL.md` |
| lumen-motion (updated) | `.cursor/skills/lumen-motion/SKILL.md` |

## Remotion

| Item | Value |
| --- | --- |
| Package | `motion/` Remotion **4.0.524** |
| Canvas | 1080×1920 @ 30 fps |
| Composition | `DirectorV3Preview` |
| New modules | `motion/src/concepts/*`, `motion/src/cinematic/*`, `AnimatedDiagram` |
| Backend | `backend/remotion_engine.py` — `resolve_scene_plan`, store plan, `render_with_plan` |
| Flag | `REMOTION_ENGINE_ENABLED` / `settings.remotion_engine_enabled` (default **false**) |
| Fallback | Hypit create-video path unchanged for non-«e» projects |

## Director integration

```
create-video (project «e»)
  → visual_variation.plan_for_request
  → job director_v3
  → remotion_engine.resolve_scene_plan + store
  → Remotion CLI → MP4
```

Illegal Director keys (`x`, `css`, `fontSize`, …) stripped in `resolve_scene_plan`.
Render plans: `data/<pid>/remotion-plans/<generationId>.json`.

## Preview

| File | Notes |
| --- | --- |
| `output/remotion-engine-v1/preview.mp4` | 20.05 s, 1080×1920, H.264+AAC, ~10.2 MB |
| `output/remotion-engine-v1/preview.props.json` | Resolved props |
| `output/remotion-engine-v1/render-plan.json` | Immutable plan |
| `output/remotion-engine-v1/frame-240.png` | Mid-film QA still (concept overlay + captions) |

## Tests

| Suite | Result |
| --- | --- |
| `motion` npm test | **48/48 pass** |
| `motion` typecheck | **pass** |
| `backend/tests/test_remotion_engine.py` + `test_director_v3.py` | **9 pass** |

## Deployment / DO (lumen-test follow-up)

| Check | Result |
| --- | --- |
| Host | `root@142.93.248.163` (`lumen-test`) — **not** strom-v2 `Host lumen` |
| Method | `git archive` of tip → `/opt/lumen-rebuild/` (backend/motion/docs/skills/report) |
| Services restarted | **`lumen-web` + `lumen-worker` only** |
| RunPod / GPU | **not touched** |
| Prod flag / prod containers | **not changed** |
| Health `http://127.0.0.1:8018/api/health` | **200** |
| `from backend import remotion_engine` | **OK** |
| `settings.remotion_engine_enabled` | **`False`** (`.env` has no `REMOTION_ENGINE_ENABLED`; default off) |
| `remotion_engine.enabled()` | **`False`** |
| Library `/mnt/volume_nyc1_1791446889637/app-library` | **reachable** — manifest **811** assets |
| Server deploy marker | `/opt/lumen-rebuild/DEPLOY_SHA.txt` → see Git below |

`REMOTION_ENGINE_ENABLED` was **not** set to `true`. Project «e» Remotion path remains available via existing Director V3 wiring; Hypit remains the create-video fallback for everyone else.

## Success criteria

| # | Criterion | Status |
| --- | ---: | --- |
| 1 | Architecture docs | **PASS** |
| 2 | Agent skills | **PASS** |
| 3 | Remotion in real pipeline | **PASS** (project «e» + `remotion_engine`) |
| 4 | User video central | **PASS** |
| 5 | Media library usable | **PASS** (811 on lumen-test volume) |
| 6 | Motion components | **PASS** |
| 7 | Deterministic typography | **PASS** (AutoFitText) |
| 8 | Captions readable | **PASS** (frame QA) |
| 9 | RU/EN/ZH | **PARTIAL** — cards/locale stack exist; **create-video Remotion path still Director V3 RU demo**; EN/ZH create-video → Remotion not shipped |
| 10 | Director motion presets | **PASS** (registry + visual plan) |
| 11 | Real 20s MP4 | **PASS** (local preview) |
| 12 | No regression (Hypit fallback) | **PASS** (flag default / server **false**) |
| 13 | Deployment verified | **PASS** on lumen-test (health + import + library); not deployed to strom-v2 prod |
| 14 | Git commit + push | **PASS** — see Git |

## Git

| Item | Value |
| --- | --- |
| Branch (report push) | `feat/media-library-cleanup-v1` |
| Engine feature commit | `005cca6caeb7afc2bfb788ef37c250198b343fdf` |
| Code archive deployed to lumen-test | `08c5ea20257c977ccc4d90e3b8060aca8ed1116a` |
| Report tip (`DEPLOY_SHA.txt` after sync) | `b9b9a346f345445770d073576352c1b63e7b1893` |
| Remote | `origin` pushed |

## Remaining gaps (honest)

1. **Non-«e» projects** — create-video still Hypit; Remotion not generalized (speaker staging / composition).
2. **EN/ZH create-video → Remotion** — not wired; Director V3 preview captions/locale remain RU-centric.
3. **Flag stays off** — do not enable `REMOTION_ENGINE_ENABLED=true` until non-e path is safe or scoped explicitly to project «e» only in ops docs.
4. **strom-v2 DO** (`188.166.244.242` / test.lumen…) — this follow-up deployed **lumen-test** rebuild host only, not that compose stack.
5. I2V / GPU batches still deferred.
