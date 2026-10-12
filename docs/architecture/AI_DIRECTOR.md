# AI Director

## CURRENT STATE

- Project create does **not** call the Director. Deferred source plan: `backend/source_analysis.ensure_analysis` (heuristic by default; OpenRouter optional).
- Semantic visual plan: `backend/visual_variation.resolve_plan(seed, energy)`
- History: `data/<project>/visual-history/gen_*.json` + `latest.json`
- Studio create-video (project «e») stores `visual_plan` on the `director_v3` job
- Remotion `DirectorV3` applies looks per beat; concept triggers sync from captions
- Media rules: `backend/director_media_rules.py` (canonical same-source ban) applied in planner + `remotion_engine.resolve_scene_plan`
- Hypit model brief (non-Remotion projects): `backend/assembly_prompt.txt` via `hypit_prompt.py` — concise QUALITY ENFORCEMENT block; full recovery checklist stays in `docs/prompts/cinematic-director-v3-quality-recovery.md`

## TARGET STATE

Director decides WHAT (scene purpose, assets, treatments, energy).
Remotion decides HOW (pixels, easing, typography).
`resolveScenePlan()` freezes a validated render plan before any Remotion call.

## IMPLEMENTED (V1)

- Seeded anti-repetition for backgrounds / layouts / transitions
- `backend/remotion_engine.resolve_scene_plan` wraps visual plan + motion metadata + locale
- Concept-trigger presets for spoken-concept viz
- Eligibility-before-rank library search; situational queries; no passport placeholder when photo exists
- Same-source ban: main plate and inset cannot share canonical identity (still + i2v)
- Premium motion V4 (`pm_*` deterministic WebM) is searchable via multilingual tags; prefer for conceptual/hero overlay beats when Remotion engine is enabled
- Consult beat: one cover plate + presenter PIP from original speaker timing (never duplicate library inset)
- Long-form captions follow `beatsFor` (not fixed 20s stamps); ordinary full-render helper: `scripts/ordinary_director_render.py`
- Recent-history anti-repeat scans all `visual-history/*.json` and prefers never-recent plates

## NOT IMPLEMENTED

- LLM-authored freeform scene graphs outside the registry
- Per-phrase dynamic beat length from full Whisper alignment for all projects
- **Director V4 production LLM** (DigitalOcean Gradient / `https://inference.do-ai.run/v1`) — blocked: no `MODEL_ACCESS_KEY` / `GRADIENT_MODEL_ACCESS_KEY` on lumen-test; OpenRouter forbidden for this track. Details: `reports/LUMEN_DIRECTOR_V4.md`.
