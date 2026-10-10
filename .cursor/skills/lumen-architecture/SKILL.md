---
name: lumen-architecture
description: >-
  Lumen service boundaries, video pipeline, ADRs, and change restrictions.
  Use before substantial backend/frontend/motion changes.
---

# Lumen architecture

Read first: `docs/architecture/VIDEO_PIPELINE.md` and ADRs under `docs/architecture/adr/`.

## Boundaries

| Area | Path | Owns |
| --- | --- | --- |
| Studio API | `backend/studio.py` | edit plan, create-video enqueue |
| Hypit prompt | `backend/hypit_prompt.py` | AI picture sentences (fallback path) |
| Remotion engine | `backend/remotion_engine.py`, `motion/` | deterministic composition |
| Director V3 | `backend/director_v3.py` | project «e» Remotion job |
| Media library | `media/library/` | assets + search |
| Worker | `backend/worker.py` | job kinds |

## Restrictions

- Do not invent a second composition engine in `frontend/` or `index.html`.
- Do not restart RunPod for Remotion-only changes.
- Feature flag: `REMOTION_ENGINE_ENABLED` / `settings.remotion_engine_enabled`.
- Acceptance = downloaded MP4 (`docs/RELEASE_CHECKS.md`).
