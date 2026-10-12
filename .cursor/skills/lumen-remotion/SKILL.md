---
name: lumen-remotion
description: >-
  Remotion conventions for Lumen motion/: frame-driven animation, compositions,
  registry contract, and pipeline integration via remotion_engine.
---

# Lumen Remotion

**MAIN quality-recovery prompt:** `docs/prompts/cinematic-director-v3-quality-recovery.md`  
(index: `docs/prompts/README.md`).

Package: `motion/` — Remotion 4.x, canvas 1080×1920 @ 30fps.

## Rules

- Drive motion with `useCurrentFrame()` / `interpolate` / `spring` — never wall-clock timers.
- Director fields only through `validateScene` / `normalizeScene` / `renderScene`.
- Text: `AutoFitText` or `AnimatedCaption`. No important text in generated images.
- Safe insets: `SAFE_INSET` in `themes/tokens.ts`.
- Pipeline entry: `backend/remotion_engine.py` → Remotion CLI → MP4.
- V5: default Create Video path when `REMOTION_ENGINE_ENABLED=1` (`should_use_remotion`). Transcript captions via `attach_transcript_captions`. Fail closed — never silent Hypit override.
- V8 (≥45s): `director_v8` expands to `long60`, stages semantic webm into `motion/public/picked/`; `DirectorV3` mounts `SemanticMotionClip` from plan `semanticMotion.staged`. Audit `semanticMotionAudit.pass` before claiming motion is live.
- V9: prefer `FloatingForeground` (transparent SVG/PNG, no bordered shelf). yuv420p webm ≠ alpha — do not put it in a black box over the speaker. Honor `compositionPolicy=v9_clean` / `composition.floatObject`.
- Reuse `lumen-motion` for registry scenes; this skill covers engine integration.

## Check

```bash
cd motion && npm test && npm run typecheck
```

Render a real MP4 before claiming success.
