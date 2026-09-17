# Creator preferences and export controls

## Behavior

Creator profiles accept structured story templates, pacing, presenter screen-time targets and visual density. New projects capture them; rebuilding a Director Timeline can override them. They enter the executable planning prompt as a concrete editorial brief, with speech preservation and available evidence taking priority over targets. Accepting the proposal persists the chosen style at the same revision as the edit. Unaccepted proposals do not mutate the creator profile.

The review displays measured average clip length and presenter/B-roll proportions from the actual proposed timeline and its shot classifications. These are not face recognition or a guarantee of perceived pace. Source cutaways are subtracted from presenter screen time. Reusable templates cover preserved chronology, hook/evidence/takeaway, problem/solution and comparison.

Individual platform versions support 9:16, 16:9, 1:1 and 4:5 export, editable output cover timestamp, and existing scene-range duration controls. Rendering fits the full reviewed master rather than cropping away burned captions. Hook typography uses actual output dimensions. Old manifests lacking the new fields remain editable.

## Validation

- Eight server platform tests passed, including real exports in all four aspect ratios with audio, legacy packages, locks, ownership and immutable history.
- Creator tests check snapshot propagation, acceptance-only profile persistence and actual cutaway duration accounting.
- A compatibility test ensures music saved before volume automation remains valid when rebuilding a creative plan.
- Headless Chrome exercised story selection, submitted an edited 4:5 platform version, and locked/unlocked music controls; all assertions passed. This is a component interaction harness, not authenticated production E2E.
- Frontend TypeScript/Vite production build passed.

## Limits

Templates express editorial preferences, not fabricated footage or forced cuts through speech. A landscape export is a padded adaptation of the reviewed master. Screen-time metrics depend on shot classification. This does not add learned creator profiles, archive/news search, automatic beat-by-beat video recutting, or autonomous publishing.
