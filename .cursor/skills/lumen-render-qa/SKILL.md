---
name: lumen-render-qa
description: >-
  Render QA for Lumen: real frames/MP4 inspection, captions, audio sync,
  diversity. Unit tests alone are not acceptance.
---

# Render QA

For Director / Remotion / preview QA recovery, follow  
`docs/prompts/cinematic-director-v3-quality-recovery.md` (**MAIN**) first.

- Extract representative frames; read them
- Face obstruction and caption contrast are blocking
- Check caption overflow, safe areas, glyph coverage
- Probe duration, audio presence, 1080×1920
- Compare player vs download delivery
- Follow `docs/RELEASE_CHECKS.md` for edit/render lifecycles

Passing `npm test` without a watched frame is not done.

Director V3 recovery artifacts live under `output/director-v3/` (`preview-v3-r2.mp4`, `autopsy-31/`, `qa-r2/`, `compare/`). A 20s preview PASS does not imply a full-minute delivery PASS.
