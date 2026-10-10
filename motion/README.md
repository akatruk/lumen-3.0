# Lumen motion library

Phase 1 Remotion components for short-form motion graphics. This package is additive. It does not render the Lumen video a person downloads.

## Where it sits

Lumen's finished picture is still one open-source Hypit prompt (`backend/hypit_prompt.py`). Hypit draws that prompt. Studio controls, captions, voice, and music stay on that path. Nothing in this package is wired into `studio.py`, `worker.py`, the Hypit prompt, or the current player.

`onboarding-video/` is a separate Remotion project for product walkthroughs. `frontend/` is Lumen Studio. This library lives in `motion/` so it does not become a second renderer inside the player.

The text problems in the current Hypit picture come from that prompt, not from this package: `caption-fine` places captions in a fixed-size box (`wrap: word`, about 28–32px), and motion plates are full-frame color washes. A word that is wider than the box can break. This library measures the line and wraps only on whitespace.

## Director contract

A future AI Director chooses a scene id and structured props: variant, duration, text, emphasis, media, and a transition from a fixed list. `validateScene()` accepts that object or returns errors. `normalizeScene()` fills duration, timed words, and placeholder media.

The Director does not choose raw x/y, CSS, font size, color, React, or animation code. Those keys fail validation. Unlisted scene ids fail. These ids are registered and rejected until a later phase: `animated_diagram`, `quote`, `process_flow`, `image_focus`, `final_cta`.

Preview media is a colored placeholder (Speaker, Footage, Image, Screen). No stock footage is downloaded. Pass `media.src` later when a real file exists.

Default canvas: 1080×1920, 30fps. Safe insets keep type out of the TikTok/Reels chrome: top 180, right 120, bottom 320, left 72.

## Phase 1 map

```
motion/
  src/themes/          tokens
  src/types/           discriminated scene schema
  src/utils/           measure, wrap, duration, safe area
  src/registry/        catalog, validateScene, normalizeScene, render
  src/primitives/      frame-driven entrances, type, lines, camera
  src/typography/      AutoFitText, AnimatedCaption
  src/media/           speaker, b-roll, background, image, screenshot
  src/layouts/         safe area
  src/transitions/     cut, fade, slide, wipe
  src/components/      KineticHook, BigNumber, ProgressSteps, SpeakerFocus, BrollCaption
  src/showcase/        MotionLibraryShowcase
  preview-frames/      stills from `npx remotion still` (generated)
```

Implemented scenes: `kinetic_hook`, `big_number`, `progress_steps`, `speaker_focus`, `broll_caption`, `timeline`, `comparison`, `split_screen`, `checklist`, `stat_reveal`.

```bash
npm test
npm run typecheck
npx remotion still src/index.ts MotionLibraryShowcase preview-frames/kinetic-hook.png --frame=72
```

## Not in this package

- Still deferred: `animated_diagram`, `quote`, `process_flow`, `image_focus`, `final_cta`.
- A Director that turns a transcript into this scene JSON, and any link from Lumen Studio or the Hypit prompt.
