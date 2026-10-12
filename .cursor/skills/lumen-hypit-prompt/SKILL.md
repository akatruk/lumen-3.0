---
name: lumen-hypit-prompt
description: >-
  Build the Lumen-fix prompt constructor for open-source Hypit
  (https://github.com/hypit-ai/hypit). Use when changing Lumen Studio, the
  Hypit prompt, AI elements, effects, sliders, captions, voice, music, or a
  video render in lumen-fix.
---

# Lumen-fix prompt constructor

Lumen-fix develops the prompt constructor for open-source Hypit
(`https://github.com/hypit-ai/hypit`). Hypit generates the video from that one
prompt. Lumen Studio is the interface where AI elements are edited. Every AI
element a person can change in Lumen Studio must land in the final prompt.

## What to change

- Put a new or edited studio control into the constructor
  (`backend/hypit_prompt.py` → `prompt_modules.assemble_hypit_prompt`).
- `assembly_prompt.txt` is the final Hypit editorial contract with
  `{{placeholders}}` filled by `prompt_modules.assemble.fill_assembly_template`
  (coverage, intensity, voice/caption/music, transcript, staged library).
- **Do not rewrite** core face/caption/library rules for domain refinements —
  add an attachable module under `backend/prompt_modules/`.
- Modules: `editing_controls` (Calm/Balanced/Dynamic + Animation/Intensity/
  Motion/Density) and `localization` (RU/EN/ZH). Job stores `promptAssembly`
  versions (`mainPromptVersion` + `modules[]`) for reproducibility.
- At render time `hypit_picture.render_picture` writes `final_prompt.txt` and
  injects the filled text into `main.svml` `text:Value id="request"`.
- Editing sliders must also stamp `visual_plan.editingControls` for Director
  Remotion (`apply_editing_controls`) — prompt text alone is not enough.
- The saved value on the project and the sentence in the final prompt must
  match. Sliders, «Эффекты», captions, voice, music, picture notes, and the
  reference treatment are all prompt inputs.
- A control that only changes local CSS, a seek script, or a second renderer
  is not finished. Hypit / Remotion renders from the assembled params.
- UI language ≠ video language. `PUT …/language` and
  `PUT …/editing-controls` must not auto-start paid renders. Missing target
  voice → `VOICE_SETUP_REQUIRED` (no silent swap).

## What stays out of Lumen

- Do not add a parallel composition engine: no plate CSS, zoom, font size,
  seek-script geometry, or timeline cuts inside `index.html` as the picture.
- Do not invent facts the host did not say. Do not copy reference footage,
  faces, or music into the output.
- Card pixel size is not an effect. Duration share and intensity are words in
  the prompt.

## Done when

The final prompt text contains the studio change, and the finished Hypit video
shows it. A successful job or an enabled button is not enough.
