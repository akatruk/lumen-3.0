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
- Engine wrap: `backend/remotion_engine.resolve_scene_plan`
- Composition: `motion/src/preview/DirectorV3.tsx` (`DirectorV3Preview`)
- Shared portrait geometry: `motion/src/preview/portraitLayouts.ts` (splits fill 1080×1920; face band; criteria explanations RU/EN/ZH)
- Registry types/variants: `motion/src/types/scene.ts`
- Concept triggers: `motion/src/concepts/` + `media/library/concept_triggers.py`

Speaker presence is required. Same seed + versioned inputs → same visuals.
Never emit CSS, React, or x/y from the Director.
Subject protection and caption contrast are blocking (see MAIN prompt §9A).

Implemented (not aspirational):
- Captions use a dark pill (`data-caption-backing="dark"`); locale from `visualPlan.language`.
- Split layouts use `splitSpeakerRect` / `splitMediaRect` — no landscape shrink into a black void.
- Beside cards are title + relationship explanation (`criteriaCardsFor`), not single-word labels.
- Concept overlays are beat-gated; speaker PIP is skipped when a primary speaker panel is already on screen.
- Consult prefers full-bleed `consult.mp4`; sparse stamp `.webm` plates are not mounted as panels.
- Validation artifact: `output/director-v3/preview-v3-r2.mp4`.
