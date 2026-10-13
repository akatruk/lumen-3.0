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

**V8:** Spoken concepts bind to library webm (`director_v8.MOTION_BINDINGS` → mobility/document/folder/compare/shield). Prefer animated objects over static cards. `SemanticMotionClip` must cover ~520px speaker-safe — tiny insets = fail. Preview: `output/director-v8/`.

**V9:** Transparent objects (`director_v9.OBJECT_BINDINGS`) over opaque webm boxes. One secondary visual max. Steps = speaker + type, not a dark card wall. Preview: `output/director-v9/`.

## Contract

Director chooses: scene `type`, `variant`, duration, text/emphasis/media/data, transition (`cut|fade|slide|wipe`).
Not: x/y, CSS, font size, color, React. `validateScene()` / `normalizeScene()` / `renderScene()`.

## Rules

- Text via `AutoFitText` or `AnimatedCaption`. Never split words (EN/RU); CJK ok.
- No captions/logos in generated footage. No invented statistics.
- One theme: `motion/src/themes/tokens.ts`.
- Concept triggers: `motion/src/concepts/`. Cinematic plates: `motion/src/cinematic/`.
- V11.1 business motion: `motion/src/preview/BusinessMotion.tsx` — shareholder_structure, equity_distribution, capital_investment, company_ownership, investment_flow, company_control, financial_comparison, business_process. Numbers only when Director stamps `showCount` / `foreignRatio` with source text. Labels RU/EN/ZH; numerals identical.

## Registry

Implemented: kinetic_hook, big_number, progress_steps, speaker_focus, broll_caption, timeline, comparison, split_screen, checklist, stat_reveal, animated_diagram.

Deferred: quote, process_flow, image_focus, final_cta.

Canvas: 1080×1920, 30 fps. Storage: volume `lumen-motion` or `motion/output`.

Library micro-clips: `motion/src/clips/` (legacy + `premium/` V4). Encode with `media/library/render_premium_motion_v4.py` → `app-library/motion/premium/`.

```bash
cd motion && npm test && npm run typecheck
```
