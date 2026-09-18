# Render Summary Implementation Plan

**Goal:** Summarize the saved executable montage before rendering.
**Architecture:** A pure backend summary derives from approved clips and the renderer timeline. A read-only owned-project endpoint adds revision and unapplied proposal counts. The existing confirmation dialog loads this summary each time and enables rendering only for the matching saved revision.
**Tech Stack:** FastAPI, Pydantic, React, TypeScript, pytest.

- [x] Add regression tests for unchanged/split footage, small trims, visible effects, excluded unapproved clips and owned endpoint revision.
- [x] Implement backend/render_summary.py and GET manual/summary, reusing audit_edit and compile_timeline; count ready creative/music/individual proposals separately.
- [x] Add localized RenderSummary.tsx; integrate loading/error/retry and revision gate into ManualEditor dialog; preserve cost notice.
- [x] Run focused backend tests, frontend build/localization checks, and browser confirmation checks. Deploy backed-up release and verify production read-only. No customer render or paid AI call.
