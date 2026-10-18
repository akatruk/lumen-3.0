# Hypit prompt modules

## Attachment point

`backend/prompt_modules/assemble.py` → `assemble_hypit_prompt(manual)`  
called from `hypit_prompt.illustration_request` / `assemble_illustration`  
wired into `studio.create_video` (Hypit + Remotion «e» job payloads) and `GET /picture-prompt`.

Main body file `backend/assembly_prompt.txt` is **not** rewritten for domain features.

## Assembly order

1. Main prompt text (content-addressed `mainPromptVersion = assembly:<sha12>`)
2. Studio levels (animation / intensity / motion / density) — short summary line
3. Module index (`attached: editing_controls@1.0.0, localization@1.0.0` or subset)
4. Each applicable module instruction block
5. `MODULE CONFLICTS` (explicit; `none` when clean)
6. `RUN PARAMS` JSON (`editingControls`, `targetLocale`, typography, voice defaults, versions)
7. `USER CONTENT` pointer (timed lines stay in author SVML)

## Modules

### editing_controls@1.0.0

- **Always** attaches (defaults = Balanced when sliders omitted)
- Rules for Calm / Balanced / Dynamic + Animation / Intensity / Motion / Density
- Prefers speech meaning → host visibility → readability → relevant visuals → style
- Does **not** cancel face/caption safety, scene duration, asset quality, or same-source bans
- `runParams.editingControls`: `{ animation, intensity, motion, density, visualEnergy, preset }`
- Remotion path: `apply_editing_controls` stamps the Director visual plan
  (`motionIntensity`, `animateGraphics`, `overlayBudget`, `conceptTriggers`)
- Studio: `PUT /api/studio/projects/{pid}/editing-controls` persists prefs only (no render/TTS)

### localization@1.0.0

- Applies when `manual.language` resolves to `en-US` / `ru-RU` / `zh-CN`
- Reuses `language.build_language_directive`, `audio_instruction`, `director_context_blocks`
- Adds shared rules: single targetLocale, translate all visible surfaces, keep facts, target-VO timing, no silent voice swap
- Cache: `data/<pid>/localization/<locale>/` + `prompt-assembly.json` on create-video

## Job reproducibility fields

```json
"promptAssembly": {
  "mainPromptVersion": "assembly:b30efd9101c0",
  "modules": [
    {"id": "editing_controls", "version": "1.0.0", "domain": "editing"},
    {"id": "localization", "version": "1.0.0", "domain": "localization"}
  ],
  "conflicts": [],
  "runParams": {
    "editingControls": {
      "animation": 60,
      "intensity": 60,
      "motion": 80,
      "density": 70,
      "visualEnergy": "balanced",
      "preset": "balanced"
    },
    "targetLocale": "ru-RU"
  }
}
```

## Parameter path (ordinary Director create-video)

```
CreateVideo sliders / Calm|Balanced|Dynamic
  → PUT editing-controls (save only) + POST create-video
  → prompt_modules.assemble (+ editing_controls + localization)
  → visual_variation.plan_for_request(..., editing=…)
  → apply_editing_controls → visual_plan.editingControls
  → remotion_engine.resolve_scene_plan
  → DirectorV3 props (motion gain, concept cap, animateGraphics)
  → finished MP4
```

Slider moves alone never start paid GPU/TTS. New montage requires Create video (not a post-process of an existing MP4).
