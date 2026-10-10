---
name: lumen-director
description: >-
  AI Director semantic planning, seeded visual variation, motion presets, and
  resolveScenePlan. Director chooses WHAT; Remotion chooses HOW.
---

# Director

- Plans: `backend/visual_variation.py` (`resolve_plan`, `plan_for_request`)
- Engine wrap: `backend/remotion_engine.resolve_scene_plan`
- Registry types/variants: `motion/src/types/scene.ts`
- Concept triggers: `motion/src/concepts/` + `media/library/concept_triggers.py`

Speaker presence is required. Same seed + versioned inputs → same visuals.
Never emit CSS, React, or x/y from the Director.
