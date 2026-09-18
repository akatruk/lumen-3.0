# Pre-render summary

The existing shared manual editor confirmation now fetches `/api/studio/projects/{id}/manual/summary`. Facts come from the saved, approved clips and `compile_timeline`, not proposal descriptions or local drafts. Render retains its atomic revision check. Summary loading, failure and revision mismatch disable confirmation.

Includes source/planned duration (frame rounding disclosed), removed source ranges, output/source timestamps per scene, executable visual/audio operations, added captions/music/normalization, source audio vs separate dubbing clarification, and ready unapplied proposals across creative/music/individual edits (including older proposals).

Near-original is a conservative settings heuristic: no visual effects/captions/reorder and no trimming above max(2 seconds, 2% of source). Audio changes alone do not count as visual changes. This does not score actual rendered image quality or compare against a previous output.

Validation:
- 21 backend tests passed: summary, manual editing, editorial pacing. Regression covers the final2-like split/1.6-second trim, approved-only clips, ownership, unapplied proposal isolation, revision and saved-plan requirements.
- TypeScript/Vite build and 4 localization tests passed.
- Workspace browser suite: 5 scenarios passed, including explicit confirmation and render revision.
- Summary browser suite: request failure/retry, stale revision, near-original warning, 390px mobile overflow, no accidental render. Screenshot inspected.
- No paid AI request or customer render was run.
