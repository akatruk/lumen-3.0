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
- V9/V10.1: prefer `FloatingForeground` (transparent SVG/PNG or `format: png_seq` RGBA). yuv420p webm ≠ alpha. Honor `compositionPolicy=v9_clean` / scale profiles. Do not float large 3D over the face — cutaway layouts only when `production_ready`.
- V11.1: `DirectorV3` mounts `BusinessMotion` from `scene.businessMotion` (provenance-stamped). `BigFigure` renders only with spoken evidence — never default `2`. Captions: larger dark pill (min ~64px), phrase group 1–2 lines.
- V11.2: `CleanSteps` uses `Step N` + label on separate lines (never `{n} Shareholders`). `BusinessMotion` respects `placement` / `shelfTop` / `faceSafe` (media column or below face band); transparent node fills; simultaneous node reveal when `showCount`. Caption plate opacity ~0.55.
- Adaptive contrast: `motion/src/utils/adaptiveLineStyle.ts` + `ConnectorStroke` — analyze full connector path vs plate; outline/recolor gold on beige. Tests in `adaptiveLineStyle.test.ts`.
- V14: `DirectorV3` mounts `SemanticMotion` from `scene.semanticMotionV14` and skips `BusinessMotion` on that beat. `resolveLayout` refuses face-band and caption overlap. Flag `SEMANTIC_MOTION_V14_ENABLED` default off.
- Reuse `lumen-motion` for registry scenes; this skill covers engine integration.

## Check

```bash
cd motion && npm test && npm run typecheck
```

Render a real MP4 before claiming success.
