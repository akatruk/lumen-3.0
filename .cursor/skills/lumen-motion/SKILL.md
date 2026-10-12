---
name: lumen-motion
description: >-
  Build and reuse the Lumen Remotion motion library in motion/. Use when
  adding scene components, Scene JSON, AutoFitText, showcase, or concept viz.
  For pipeline wiring see lumen-remotion and lumen-architecture.
---

# Lumen motion library

Short-form Remotion pictures live in `motion/`. Do not start a second component set in `frontend/` or `onboarding-video/`.

Pipeline integration (feature-flagged) goes through `backend/remotion_engine.py` and Director V3 — see `lumen-remotion`. Hypit remains the fallback picture path when the flag is off. Do not invent plate CSS inside Studio HTML as a second renderer.

**V7:** Director `shotPlan` drives layout / `cardMode=progressive_one` / kinetic hook. Never mount empty caption plates. Prefer one hero card over dense stacks.

## Contract

Director chooses: scene `type`, `variant`, duration, text/emphasis/media/data, transition (`cut|fade|slide|wipe`).
Not: x/y, CSS, font size, color, React. `validateScene()` / `normalizeScene()` / `renderScene()`.

## Rules

- Text via `AutoFitText` or `AnimatedCaption`. Never split words (EN/RU); CJK ok.
- No captions/logos in generated footage. No invented statistics.
- One theme: `motion/src/themes/tokens.ts`.
- Concept triggers: `motion/src/concepts/`. Cinematic plates: `motion/src/cinematic/`.

## Registry

Implemented: kinetic_hook, big_number, progress_steps, speaker_focus, broll_caption, timeline, comparison, split_screen, checklist, stat_reveal, animated_diagram.

Deferred: quote, process_flow, image_focus, final_cta.

Canvas: 1080×1920, 30 fps. Storage: volume `lumen-motion` or `motion/output`.

Library micro-clips: `motion/src/clips/` (legacy + `premium/` V4). Encode with `media/library/render_premium_motion_v4.py` → `app-library/motion/premium/`.

```bash
cd motion && npm test && npm run typecheck
```
