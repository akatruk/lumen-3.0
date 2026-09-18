# Final audio selection repair

Goal: Completed voice changes must be reflected in the finished video and ordinary download, including after reload.

Evidence: Dubbing writes an independent immutable video. The result endpoint always serves the Master, and workspace selection starts at result; no saved final-output choice exists.

Design: Keep the render Master immutable for rendering/dubbing inputs. Store a project final-output selection bound to that Master. Completed full voiceovers become the final output; failed jobs and samples do not. Existing ready versions get an explicit Use as final action and the original Master remains selectable. A new render invalidates old selection. The normal result endpoint resolves the current final output, so all existing downloads work. Workspace polls its identity to refresh playback and shows the active language. Stale versions remain downloadable but cannot replace a newer edit.

- [x] Regression tests: finished endpoint differs after successful dubbing; master unchanged; sample/failure isolation; selection ownership/readiness/staleness; new render invalidates selection.
- [x] Backend selection table/helper, endpoint and completion/cached selection; media result resolution and Master alias.
- [x] UI final status/apply action, refresh playback/cache identity, immutable Master in versions; clear generation behavior.
- [x] Browser regression and backend tests, deploy, verify current user's existing voiceover and select it where compatible with current Master.
