# UX action audit — 2026-09-17

## Findings and fixes
- P1: Global button reset removed borders/backgrounds; unclassified actions (including accepting a creative plan) looked like static text. Added a low-specificity visible fallback scoped to project/form/card/search surfaces. Existing navigation and timeline-specific styles still override it.
- P1: The next creative-plan action appeared only after a long shot list. Added explicit primary actions above and below, with replacement explanation, applying state, disabled reason and save shortcut.
- P1: Render allowed clicks with unapproved manual shots, leaving rejection to the server. Count pending approvals, explain the next step and disable render until approved; saving remains available.
- P2: Inspector tabs and sticky source player collided with the 68px app header. Corrected desktop offsets; mobile inspector tabs remain in normal flow.
- P2: Additional cleanup disclosure looked like loose text. Added a framed, padded disclosure control.
- P2: Library upload had unexplained disabled states and retained the selected native file after success. Explain missing file/attribution/permission or full library; reset file input after success so the same file can be selected again.
- P2: Form textarea sizing, narrow layouts, audio player width and error presentation needed consistent treatment.

## Scope and evidence
Source review covered the project shell, creation/upload, creative decisions, manual editor, alternatives, media/music/B-roll components, variants/export and shared styling. Browser fixture uses real CreativePlan and ManualEditor components with mocked API responses; it does not mutate production projects or invoke paid providers.

Nine checks pass at desktop and an actual 390px iframe viewport: primary action style/44px+ target; actions above and below; disabled explanation; unapproved render block; visible media upload input; upload prerequisite text; no page overflow; navigation offset; successful apply callback. Reviewed screenshots. TypeScript/Vite build and git diff whitespace check pass.

This is not a new live upload→paid analysis→render test, nor certification of every possible project state. Existing upload transport and backend rendering were not changed. No customer project or plan was edited.
