---
name: lumen-director
description: >-
  AI Director semantic planning, seeded visual variation, motion presets, and
  resolveScenePlan. Director chooses WHAT; Remotion chooses HOW. For Director
  V3 / Remotion / video QA recovery, load docs/prompts/cinematic-director-v3-quality-recovery.md first.
---

# Director

**MAIN prompt (Director V3 / Remotion / video quality recovery):**  
load and follow `docs/prompts/cinematic-director-v3-quality-recovery.md` before planning or coding.  
Index: `docs/prompts/README.md`. Hypit handoff is separate: `backend/assembly_prompt.txt`.

- Plans: `backend/visual_variation.py` (`resolve_plan`, `plan_for_request`)
- Editing prefs: `prompt_modules/editing_controls.py` → `apply_editing_controls`
  (Animation/Intensity/Motion/Density + Calm/Balanced/Dynamic). Create-video
  passes `editing=` into `plan_for_request`; Remotion reads
  `visualPlan.editingControls` (motion gain, concept cap, `animateGraphics`).
- Engine wrap: `backend/remotion_engine.resolve_scene_plan`
- Composition: `motion/src/preview/DirectorV3.tsx` (`DirectorV3Preview`)
- Shared portrait geometry: `motion/src/preview/portraitLayouts.ts` (splits fill 1080×1920; face band; criteria explanations RU/EN/ZH)
- Registry types/variants: `motion/src/types/scene.ts`
- Concept triggers: `motion/src/concepts/` + `media/library/concept_triggers.py`

Director runs at **Create video**, not at project upload. Default plan builder is local heuristic (`backend/providers/director.py`). Optional LLMs: `LLM_PROVIDER=openrouter` (forbidden on the RunPod Director track) or `LLM_PROVIDER=runpod` (Ollama on `lumen-hypit-4090`, fail-closed). Source transcript/cache: `backend/source_analysis.py`.

**RunPod Native Director V1 (2026-10-12):** replaces DO Inference blocker for this track — model `qwen2.5:7b-instruct`, runtime Ollama `/v1`, SSH tunnel only. See `reports/RUNPOD_DIRECTOR_V1.md`. When `LLM_PROVIDER=runpod`, never silent-heuristic; raise `RUNPOD_LLM_UNAVAILABLE`.

Speaker presence is required. Same seed + versioned inputs → same visuals.
Never emit CSS, React, or x/y from the Director.
Subject protection and caption contrast are blocking (see MAIN prompt §9A).

Implemented (not aspirational):
- Captions use a dark pill (`data-caption-backing="dark"`); locale from `visualPlan.language`.
- Split layouts use `splitSpeakerRect` / `splitMediaRect` — no landscape shrink into a black void.
- Beside cards are title + relationship explanation (`criteriaCardsFor`), not single-word labels.
- Concept overlays are beat-gated; speaker PIP is skipped when a primary speaker panel is already on screen.
- Consult prefers full-bleed `consult.mp4`; sparse stamp `.webm` plates are not mounted as panels.
- Validation: `preview-v3-r5.mp4` (preserve r2–r4) + ordinary fulls under `output/director-v3/ordinary/` (`e-full` / `b-full` / `c-full`).
- Ordinary path script: `scripts/ordinary_director_render.py` (= resolve_plan→resolve_scene_plan→render_with_plan). Default create-video duration is 20s unless `duration_seconds` set to max step.
- Prompt load: Hypit → `assembly_prompt.txt`; Remotion → `visual_variation` + `remotion_engine`. MAIN brief in docs only.
- Rules: `director_media_rules.py`; captions keyed to `beatsFor`; RouteLink under face band; caption bottom = `captionClearance`.
- `recent_asset_ids` reads all `visual-history/*.json` (not only `gen_*`); prefer non-recent plates; FG skips `concept_*`.
- Consult: one cover + presenter PIP from `speakerFile` — never duplicate library inset.
- **Gap:** DirectorV3 caption *strings* still RU immigration pack — locale flag does not localize lines (EN/ZH unavailable until transcript wiring).
