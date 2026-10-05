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
  (`backend/hypit_prompt.py` and the call that writes the prompt for Hypit).
- The saved value on the project and the sentence in the final prompt must
  match. Sliders, «Эффекты», captions, voice, music, picture notes, and the
  reference treatment are all prompt inputs.
- A control that only changes local CSS, a seek script, or a second renderer
  is not finished. Hypit renders the prompt.

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
