# Consecutive-render quality comparison

Adds a total score delta and five category deltas (hook, clarity, pacing, visuals, audio), including regression flags. Each new review records its configured model and rubric version. Missing, malformed or incompatible historical scores are explicitly non-comparable. Comparison never changes approval or publishes a render. Low-quality revision planning receives this comparison alongside the existing review and output timeline.

Validation: production frontend build passed. Isolated server/PostgreSQL QA: 7 tests passed (comparison, quality revision and worker defaults). Covers a higher total with worse audio, missing/legacy/incompatible reviews and malformed scores. No paid AI calls or customer rerenders were made for this change. No authenticated browser end-to-end claim.

Limitations: two newly scored renders are needed for historical comparison. Independent AI judgments vary; this is not a paired visual review, engagement prediction, unattended rerender loop, or automatic best-version selection.
