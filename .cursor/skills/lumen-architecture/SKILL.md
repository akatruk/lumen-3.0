---
name: lumen-architecture
description: >-
  Lumen service boundaries, video pipeline, ADRs, and change restrictions.
  Use before substantial backend/frontend/motion changes.
---

# Lumen architecture

Read first: `docs/architecture/VIDEO_PIPELINE.md` and ADRs under `docs/architecture/adr/`.

**Director V3 / Remotion / video QA recovery:** load  
`docs/prompts/cinematic-director-v3-quality-recovery.md` (**MAIN** product prompt) before substantial edits.  
Prompt index: `docs/prompts/README.md`. Hypit assembly: `backend/assembly_prompt.txt` (not the MAIN editing brief).

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

- **PROJECT CREATION MUST NOT REQUIRE AI INFERENCE.** Upload → ffprobe metadata → `ready`. Deferred analysis runs on Create video (`backend/source_analysis.py`). See `docs/architecture/PROJECT_CREATION_REFACTOR.md`.
- Do not invent a second composition engine in `frontend/` or `index.html`.
- Do not restart RunPod for Remotion-only changes.
- Feature flags: `FAST_PROJECT_CREATION_ENABLED` (default on), `LLM_PROVIDER` (default `none`), `REMOTION_ENGINE_ENABLED`.
- Acceptance = downloaded MP4 (`docs/RELEASE_CHECKS.md`).
