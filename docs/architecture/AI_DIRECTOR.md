# AI Director

## CURRENT STATE

- Semantic visual plan: `backend/visual_variation.resolve_plan(seed, energy)`
- History: `data/<project>/visual-history/gen_*.json` + `latest.json`
- Studio create-video (project «e») stores `visual_plan` on the `director_v3` job
- Remotion `DirectorV3` applies looks per beat; concept triggers sync from captions

## TARGET STATE

Director decides WHAT (scene purpose, assets, treatments, energy).
Remotion decides HOW (pixels, easing, typography).
`resolveScenePlan()` freezes a validated render plan before any Remotion call.

## IMPLEMENTED (V1)

- Seeded anti-repetition for backgrounds / layouts / transitions
- `backend/remotion_engine.resolve_scene_plan` wraps visual plan + motion metadata + locale
- Concept-trigger presets for spoken-concept viz

## NOT IMPLEMENTED

- LLM-authored freeform scene graphs outside the registry
- Per-phrase dynamic beat length from full Whisper alignment for all projects
