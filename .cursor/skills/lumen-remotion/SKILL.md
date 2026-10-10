---
name: lumen-remotion
description: >-
  Remotion conventions for Lumen motion/: frame-driven animation, compositions,
  registry contract, and pipeline integration via remotion_engine.
---

# Lumen Remotion

Package: `motion/` — Remotion 4.x, canvas 1080×1920 @ 30fps.

## Rules

- Drive motion with `useCurrentFrame()` / `interpolate` / `spring` — never wall-clock timers.
- Director fields only through `validateScene` / `normalizeScene` / `renderScene`.
- Text: `AutoFitText` or `AnimatedCaption`. No important text in generated images.
- Safe insets: `SAFE_INSET` in `themes/tokens.ts`.
- Pipeline entry: `backend/remotion_engine.py` → Remotion CLI → MP4.
- Reuse `lumen-motion` for registry scenes; this skill covers engine integration.

## Check

```bash
cd motion && npm test && npm run typecheck
```

Render a real MP4 before claiming success.
