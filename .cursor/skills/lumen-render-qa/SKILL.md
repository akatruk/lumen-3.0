---
name: lumen-render-qa
description: >-
  Render QA for Lumen: real frames/MP4 inspection, captions, audio sync,
  diversity. Unit tests alone are not acceptance.
---

# Render QA

- Extract representative frames; read them
- Check caption overflow, safe areas, glyph coverage
- Probe duration, audio presence, 1080×1920
- Compare player vs download delivery
- Follow `docs/RELEASE_CHECKS.md` for edit/render lifecycles

Passing `npm test` without a watched frame is not done.
