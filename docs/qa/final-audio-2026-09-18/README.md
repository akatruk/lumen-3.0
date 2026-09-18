# Final voiceover delivery repair

## Root cause and reproduction

The dubbing worker saved a separate video, while the ordinary result endpoint always returned the render Master. ProjectWorkspace initialized its playback to that endpoint and had no persistent final choice. A backend regression test failed with `original master` instead of `dubbed video` after a successful dubbing job. The initial browser regression also failed because there was no Use in final video action.

## Repair

A final-output selection is stored per project and bound to its render Master. Successful full dubbing jobs and reused completed videos select that output. Samples and failed jobs do not. The result endpoint resolves the selected voiceover; the Master remains immutable and separately accessible. Existing ready voiceovers can be selected explicitly. Ownership, readiness, file availability and current-Master checks guard selection. Rendering a new Master invalidates the earlier voiceover selection; historical voiceovers remain available. The existing render summary explains that a separately dubbed version is not carried into a new render.

Workspace playback reflects the saved final language/voice, refreshes when its identity changes, and retains the selection across reloads. The final endpoint disables caching because the selected file can change.

## Verification

- 24 Linux backend tests passed: dubbing, actual audio assembly, media API ownership and complete rendering flow.
- 27 editor browser scenarios and five workspace scenarios passed.
- Four localization tests and TypeScript/Vite build passed. Existing large-bundle warning remains.
- Production final2: selected its already completed Russian male voiceover through the UI; verified reload persistence and ordinary result-download Range bytes, ETag and size match the dubbed file. The original Master remains accessible and differs.
- Server decoding of the first 30 seconds confirmed different audio hashes between the Master and voiceover. Both video streams are 162.133 seconds.
- No new paid generation or rendering was requested on production.

## Release

Static JS: index-DDjEn2n0.js. CSS: index-BvZ9mHUO.css.
Backup: /opt/lumen-rebuild/backups/final-audio-20260918-113424.
Existing final2 selection: 3242a5a016584394b79f3ad3c021358f, bound to Master 3d9d91ac54284c80ba4a1186e3a59c30.
