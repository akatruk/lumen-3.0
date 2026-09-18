# Release verification

An enabled button or a successful render job is not sufficient evidence that an
edit reached the final video. Changes to editing, audio, versions or rendering
must pass the complete delivery lifecycle before deployment.

## Real browser and media acceptance

Run from the repository root, with Chrome and Playwright installed locally:

```sh
PLAYWRIGHT_MODULE=/absolute/path/to/node_modules/playwright \
python3 scripts/verify_release.py \
  --host YOUR_LINUX_TEST_HOST \
  --python /absolute/path/to/test/venv/bin/python \
  --output /absolute/path/to/acceptance-report
```

The command builds the frontend, checks localization, copies code and the build
into a new temporary Linux checkout, and runs the backend suite. It then opens
a loopback-only test server through an SSH tunnel. The test uses a separate
SQLite database, temporary media, a temporary authenticated session and real
API requests, queue processing and FFmpeg. It does not use production project
data or provider credentials. The configured Python must include pytest,
uvicorn and backend dependencies; Linux FFmpeg must include the ASS filter.

The browser applies music to a selected voice, applies manual camera motion,
approves and locks/unlocks a shot, saves, renders, changes motion and captions,
renders again, reloads, accepts an AI plan, approves it and renders again. Each
stage checks playback and the actual download against the selected immutable
delivery. The server checks the final duration and reordered voice segments,
and measures the selected music in the MP4 audio. Failures exit nonzero.

The AI proposal and previously generated voice are synthetic fixtures. This
verifies that accepted edits reach the output; it does not score live AI
editorial quality, speech pronunciation or external provider availability.

`browser.json`, `verified.json`, logs and `verified-final.mp4` are written to
the report directory. Keep the reports with the release evidence. The isolated
remote checkout remains for diagnosis; its path is printed. Temporary server
and tunnel processes stop when the run finishes. `--skip-server-suite` is for
debugging the bridge after the same code has already passed the server suite;
it is not a replacement for the complete release check.

## UI regression coverage

Run `frontend/tests/ui-audit.browser.cjs` with `WORKSPACE_URL` pointing at the
current frontend, `PLAYWRIGHT_MODULE` set as above and `WORKSPACE_MEDIA` pointing
at a small playable test MP4. This covers scene controls, presets, approvals,
locks, captions, sound, cards, music, AI proposals, version controls and error
recovery. These tests stub API responses, so they supplement the real delivery
check and cannot replace it.

## Production smoke check

After deployment, use a temporary authenticated session to verify the affected
project without changing it: selected final version, playback, main download
identity, reload persistence and render-summary contents. Confirm the published
frontend build matches the tested build. Revoke the temporary session. Do not
call a release verified if only a local/mock UI or a job status was inspected.

If a check fails, retain the previous finished video, diagnose the failure and
repeat the entire affected lifecycle after the fix. Do not repair a failed
assertion by weakening the expected output or by silently reverting to source.
