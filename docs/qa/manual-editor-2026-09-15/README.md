# Manual editor release

Adds a separate Manual editor / 手动剪辑 tab and entry point from the AI plan. User-owned source ranges can be added, removed, trimmed and reordered (max 40; repeated ranges intentionally repeat footage). Each clip has bounded 1–3× crop/zoom, horizontal/vertical framing and a text overlay. Subtitle timings, English/Chinese text, size, placement and color are editable. Subtitle preview uses the project's output language. Original picture subtitles cannot be removed by this feature.

Manual settings are stored in studio_manual and use the existing optimistic plan revision and project job lock. Rendering snapshots settings into the job; it never calls AI and publishes needs_review/manual_review_required. AI recommendations remain separate. Master transcript overrides flow into platform VTT exports. The existing platform-generation feature still uses AI if explicitly requested.

Browser draft preview approximates framing and text, plays the selected source interval, and leaves audio unprocessed. Final FFmpeg render is required to inspect exact typography, loudness and joins. Manual cuts may cut speech; user review remains necessary. Local session drafts survive navigation and unsaved changes prevent accidental render. Saved revisions prevent silent concurrent overwrite.

Validation:
- Isolated remote full suite: 66 passed, 2 skipped.
- Real synthetic FFmpeg render: reordered blue/red scenes, crop to a green test region, safe Chinese overlays, edited yellow subtitles, expected output duration and retained audio. No paid providers called.
- PostgreSQL QA: 9 manual/studio tests passed, including ownership, revision conflicts, immutable queued snapshot and rendering with no approved AI suggestions.
- Latest transcript fallback change: 7 manual/variant tests passed locally.
- Frontend production build passes.
- Local browser QA: trim/zoom/overlay preview; subtitle editing/style save; EN/中文 switch; clip add/reorder; persisted saved state; no desktop horizontal overflow.

These are synthetic fixtures, not a claim that the user's existing production video has been manually edited or rendered.
