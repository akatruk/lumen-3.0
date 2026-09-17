# Executable timeline release — 2026-09-15

Implemented source-only timeline tracks with output-time mapping for video, titles, bilingual subtitles and original audio. Stable clip IDs, approve/lock controls, animated start/end framing, cuts and fades through black. Approved AI cuts can initialize a separate editable timeline. Manual renders include their compiled director_timeline artifact.

Single-clip AI proposals are explicitly requested, budget-reserved, versioned and reviewed. Accepting one replaces only its target and leaves it unapproved. Locked clips cannot be moved, replaced, retimed or removed. Changed AI cut edges inside recognized speech are rejected; this relies on transcript quality and is not a guarantee of semantic continuity.

Validation:
- Final isolated Linux server suite: 72 passed, 2 skipped.
- Separate PostgreSQL QA database: 14 passed.
- Frontend TypeScript / Vite production build passed.
- Browser: Chinese and English timeline labels, saved clip lock and disabled mutation controls, output track mapping; corrected overlapping track labels and inspected screenshot.
- Actual synthetic FFmpeg renders exercise subtitles/text, reorder, static framing, animated framing and black fades.
- No paid AI requests. Proposal generation mocked in tests. Manual rendering explicitly tested to avoid AI calls.
- Local macOS full suite has two render failures due to missing libass in its FFmpeg build; corresponding tests pass on server FFmpeg.

Scope still missing from the full business requirements: semantic external/AI B-roll library, archive/news/document retrieval, rendered map/chart/data-animation inserts, music beat/emotion editing, emphasis sound effects, sophisticated masks/zoom transitions, full creator-style automation and closed-loop automatic quality revision. Shot role describes existing footage and does not retrieve or generate it. Preview approximates motion; rendered files are the authoritative result. Fade means fade through black, not cross-dissolve.
