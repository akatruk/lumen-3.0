# Video pipeline

## CURRENT STATE

| Path | When | Engine |
| --- | --- | --- |
| Hypit prompt → GPU/worker picture | Most projects | `backend/hypit_prompt.py` + `media.render` (FFmpeg) |
| Director V3 Remotion | Project «e» only (`director_v3.PROJECT_ID`) | `motion/` Remotion `DirectorV3Preview` |
| Studio edit plan | All | `studio.state` + worker jobs |

Flow today (typical project) — **fast project creation** (`FAST_PROJECT_CREATION_ENABLED`, default on):

```
upload → ffprobe metadata → status=ready (no LLM)
  → user opens project / sets language / voice / style
  → Create video
       → reuse cached source analysis OR deferred local transcript + heuristic Director
         (optional OpenRouter only if LLM_PROVIDER=openrouter)
       → hypit prompt / Remotion («e»)
       → picture job → downloadable MP4
```

Invariant: **PROJECT CREATION MUST NOT REQUIRE AI INFERENCE.**

See `docs/architecture/PROJECT_CREATION_REFACTOR.md`.

Project «e»:

```
create-video → visual_variation.plan_for_request
  → job kind director_v3
  → Remotion render → MP4 (no Hypit)
```

## TARGET STATE

```
USER SOURCE VIDEO
  → transcript / analysis
  → AI Director (semantic scene plan)
  → media library search + cards + motion registry
  → voice / alignment / target timeline
  → resolveScenePlan() → validated render plan
  → Remotion composition (speaker central)
  → FFmpeg probe / accept → final MP4
```

RunPod stays asset generation only. Hypit remains fallback when `REMOTION_ENGINE_ENABLED` is off.

## IMPLEMENTED (V1)

- Remotion package in `motion/` (registry, AutoFitText, Director V3, concept triggers)
- Seeded visual plans in `backend/visual_variation.py`
- `backend/remotion_engine.py`: feature flag, `resolve_scene_plan`, render-plan persistence
- Project «e» Remotion delivery; flag-gated expansion hook for other projects

## NOT IMPLEMENTED

- Remotion as default for every project without the flag
- Full localized timeline → Remotion props for all locales in production create-video
- Automatic DO volume mount of the whole media library into Remotion `public/`

## KNOWN LIMITATIONS

- Local Mac manifests may lag DO (~636 vs ~811 assets)
- Director V3 composition is still a fixed six-beat film; scene registry feeds overlays / diagrams, not a fully dynamic beat graph yet
