# Delivery lifecycle acceptance — 2026-09-18

Runtime under test: `3a2ce43` (selected voice/music continuity across picture
renders). This follow-up adds reusable acceptance tests and release instructions;
it does not change production application behavior.

## Results

| Check | Result |
| --- | --- |
| Backend suite on Linux, real FFmpeg/ASS | 304 passed, 6 opt-in external-service tests skipped |
| UI action/error scenarios with mocked APIs | 28 passed |
| Frontend production build | Passed; same `index-Bk-zuRVo.js` and `index-BHzNTM70.css` as production |
| Localization checks | 4 passed |
| Real browser → HTTP → queue/worker → FFmpeg → download | Passed, including three picture renders |
| Production final2 read-only smoke | Passed; no project mutations |

The first backend run had 303 passes and one environment failure because that
temporary checkout lacked `frontend/dist/index.html`. After supplying the same
production build, the frontend cache-header test passed. No assertion was
weakened. The final browser bridge was run with `--skip-server-suite` because the
unchanged application code had already completed the full server suite.

## What the real browser did

The test used Chrome, an authenticated session, an isolated SQLite database and
real media files. It did not intercept browser API requests.

1. Applied background music to an already selected voice version.
2. Applied camera motion, approved the scene, checked lock/unlock, saved and
   rendered a new version.
3. Changed motion duration, enabled captions, saved and rendered again.
4. Reloaded and confirmed the same final selection and download hash.
5. Requested and accepted a deterministic AI proposal, approved both scenes in
   the review dialog, saved the summary and rendered its reordered timeline.

At every delivery checkpoint the player played successfully, the main download
button produced an actual browser download, and its complete SHA-256 matched
the selected immutable delivery endpoint. The two manual versions had different
MP4 hashes; enabled captions reached the renderer. JavaScript errors: none.

The final media was independently decoded and checked:

- Source length: 8 seconds; final length: 6 seconds.
- Final source ranges: `[4, 8]`, then `[0, 2]`.
- Synthetic voice: 880 Hz in the first retained section, then 440 Hz after the
  reorder; original 110 Hz source audio did not replace the selected voice.
- Added music: 220 Hz, still present after the AI-plan render.
- Picture: the new patterned source, not the old voice video's flat blue image.
  Average RGB difference from the corresponding unzoomed source frame: 53.86
  on a 0–255 scale, exceeding the acceptance threshold of 8.

See [delivery checks](delivery-checks.json), [UI checks](ui-checks.json) and
[final browser screenshot](browser-final.png). The generated acceptance MP4 is
kept outside git at `/tmp/lumen-release-acceptance-v4/verified-final.mp4` on the
verification workstation. The isolated Linux checkout is
`/tmp/lumen-release-check.YtzE54`; its server and SSH tunnel stopped after the run.

## Production check

For final2 (`9b3f7ca5bfe549bcadac78d63ba16757`), the selected delivery remained
`c2a774a0875146c2b4426db12d7cbe24` — Russian male voice + Easy Lemon on the latest
picture. Playback passed before and after reload. The main download's first
65,536 bytes matched that delivery's immutable endpoint. The render summary
reported voice continuity. All browser mutations were blocked; none were
attempted. The temporary QA authentication session was revoked.

See [production smoke evidence](production-smoke.json).

## Scope and future use

The test voice and AI proposal are synthetic fixtures. This verifies execution,
selection, persistence and media delivery; it does not evaluate live AI
editorial judgment, translation/pronunciation or external-service availability.
Six paid/live provider checks were deliberately not enabled.

The existing backend suite also verifies that a failed audio/render operation
preserves the previous final and that unavailable voice coverage blocks a new
render rather than silently replacing speech.

Run the reusable command in [release checks](../../RELEASE_CHECKS.md). The root
`AGENTS.md` records the requirement to verify finished media and the full affected
lifecycle before deploying future editing/delivery changes.
