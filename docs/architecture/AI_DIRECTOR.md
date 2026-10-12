# AI Director

## CURRENT STATE (V5)

- **Default production path:** Director V4 + Remotion when `REMOTION_ENGINE_ENABLED=1` (default). Hypit is explicit legacy only (`REMOTION_ENGINE_ENABLED=0`).
- Project create does **not** call the Director. Deferred source plan: `backend/source_analysis.ensure_analysis`.
- Semantic visual plan: `backend/visual_variation.resolve_plan(seed, energy)`
- **Execution:** `backend/director_execution.enforce_plan` (PIP ≥324px, heading completeness, caption≠card, statistic dedupe) inside `resolve_scene_plan`
- **Captions:** transcript → `caption_phrases` → Remotion (not LLM caption fragments)
- **V6:** `locale_consistency` + `director_semantics` — one viewer locale; speech-backed headlines/cards; layout diversity; reject EN captions under RU cards
- Studio create-video stores `visual_plan` on `director_v3` when `should_use_remotion`
- Hypit model brief (legacy): `backend/assembly_prompt.txt` via `hypit_prompt.py`

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
