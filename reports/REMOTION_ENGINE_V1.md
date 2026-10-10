# Remotion Professional Video Engine V1

Date: 2026-10-11. Repo: `lumen-3.0`.

## Verdict

**PARTIAL PASS** — architecture, skills, engine module, Director integration, tests, and a real 20s MP4 are done. DO app health verified. Media volume path not mounted on the VM at audit time. Remotion is **not** the default for every project (flag off; Hypit fallback preserved). Full multilingual create-video → Remotion for arbitrary projects is reserved.

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

## Deployment / DO

| Check | Result |
| --- | --- |
| `ssh lumen` prod `:3001/api/health` | **200** |
| testing `:3003/api/health` | **200** |
| `/mnt/volume_nyc1_1791446889637/app-library` | **not mounted** on host at verify time (library count ~811 from prior V2 report; local mirror **636**) |
| RunPod | **not touched** (hard rule) |
| Code on DO testing | requires CI deploy after push — not claimed live until pipeline runs |

## Success criteria

| # | Criterion | Status |
| --- | ---: | --- |
| 1 | Architecture docs | **PASS** |
| 2 | Agent skills | **PASS** |
| 3 | Remotion in real pipeline | **PASS** (project «e» + `remotion_engine`) |
| 4 | User video central | **PASS** |
| 5 | Media library usable | **PASS** (search additive; DO volume path missing on host) |
| 6 | Motion components | **PASS** |
| 7 | Deterministic typography | **PASS** (AutoFitText) |
| 8 | Captions readable | **PASS** (frame QA) |
| 9 | RU/EN/ZH | **PARTIAL** (locale stack + cards; create-video Remotion still RU Director V3 demo) |
| 10 | Director motion presets | **PASS** (registry + visual plan) |
| 11 | Real 20s MP4 | **PASS** |
| 12 | No regression (Hypit fallback) | **PASS** (flag default off) |
| 13 | Deployment verified | **PARTIAL** (health OK; new SHA not asserted on testing containers) |
| 14 | Git commit + push | **PASS** — `005cca6` on `fix/seedance-import-prologue` |

## Git

| Item | Value |
| --- | --- |
| Branch | `fix/seedance-import-prologue` |
| SHA | `005cca6caeb7afc2bfb788ef37c250198b343fdf` |
| Remote | `origin` pushed |

## Known limitations

- Non-«e» Remotion create-video not generalized (speaker staging).
- DO volume mount path absent on current VM layout — use prior indexed library / local mirror.
- I2V / GPU batches deferred (out of scope).
- Another agent may touch media cleanup — `search.py` only gained additive `concept_triggers.expand_query`.
