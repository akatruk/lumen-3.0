# UI audit — 2026-09-18

Scope: production navigation and existing media with read-only requests; browser fixtures for mutations and paid actions; backend tests with isolated databases and mocked providers. No customer render, media deletion, paid generation, or real Google login was initiated.

## Coverage

- [x] Navigation, project list/search, new project reference selection/removal, file selection/upload submission, workspace, guide modes/chapters, RU/EN/ZH persistence, logout and OAuth launch.
- [x] Project player/source/result/dubbed versions, compare, scene seeking, version-matched download links, actual playback and Range downloads.
- [x] Manual montage reorder/add/remove/approval/lock/save/discard, draft preview before/after/play/pause, timeline modes, caption controls and validation.
- [x] Camera controls, first-scene transition restrictions, sound accents, source/library B-roll, all six card types and map/chart/event controls.
- [x] Music search/filter/favorite/copy/add, track and volume points, music lock, rhythm analysis/alignment, safe beat preview, AI music proposal apply, music upload shortcut and library upload.
- [x] Voice sample/full voiceover submission; AI individual regeneration (edit/card/sound/generated/library modes), full-plan generation/apply, alternative generation/replacement, stock discovery and matching/placement.
- [x] Platform creation approval gate, approval/lock/unlock/reopen, manual aspect/caption/title/range editing, history/restore.
- [x] Manual and cleanup pre-render summaries, explicit confirmation, failed/stale summary, save conflict preserving draft, logout failure, mobile layout, console/network errors.

## Fixed defects

1. **Inspect did not seek the already selected scene.** It only changed React time state; the media element stayed at its previous position. It now seeks and pauses the source player and shows the draft.
2. **Incoming transitions were offered on the first scene.** The renderer ignores these without a preceding scene. The first-scene preset/options are disabled with an explanation; fade-through-black remains available.
3. **Blank new captions could be submitted.** Save remained enabled although the backend rejects empty enabled captions. Client validation now matches that constraint.
4. **Stock AI matching opened a hidden panel.** Selecting an imported candidate configured the regenerator under another hidden tab. It now switches to Effects and opens the matching form.
5. **Failed logout produced an unhandled rejection.** The signed-in screen now remains available and shows an error the user can dismiss/retry.
6. **The old cleanup render bypassed the new summary.** It now fetches a separate summary of approved cleanup recommendations and requires confirmation. The dialog explicitly explains that manual timeline effects/music are excluded from this separate mode. Revision checks remain enforced.

All six were traced to their handlers/validation; regression cases cover the corrected behavior. Fixture-selector and fixture-response mistakes discovered while expanding tests were corrected separately (not counted as product bugs).

## Evidence

- Editor audit: **25 scenarios**; navigation/auth audit: **6**; workspace suite: **5**; summary suite: **1** with multiple error/revision/mobile assertions. **37 browser scenarios total**.
- Existing backend suite on Linux: **282 passed, 6 skipped** after supplying the isolated stage's missing frontend build and rerunning that one test. The initial frontend cache-header failure was staging setup, not a product defect.
- After fixes: **16 focused backend tests passed on macOS and Linux**, including two new cleanup-summary regressions (284 distinct backend tests passed overall).
- Skips: two PostgreSQL-only cases in the isolated SQLite run; four opt-in live provider/Commons cases. Paid-provider completion/quality and third-party availability are not certified by fixture tests.
- TypeScript/Vite production build passed; **4 localization tests passed**.
- Production: all **7 projects** opened; actual source/result/dub playback checked on test11; download returned **206** with video MIME and attachment disposition; all **6 mobile tool tabs** fit at 390px. No page errors or mutation requests.
- Broader production sweep: **28 desktop/mobile views**, covering top-level pages and editor/review sections; no overflowing page, error alert, failed response, or JavaScript exception observed.
- After deployment: actual Inspect seeking, first-scene transition gate and cleanup summary endpoint/dialog passed on test11; no mutations. Public JS/CSS bytes match the tested build. Health endpoint returned 200.

JSON scenario results and the sanitized production sweep are alongside this report. The 25 editor scenarios were also exercised against the published production bundle with intercepted APIs. One test initially checked the music-upload shortcut before its animation-frame callback; after waiting for the resulting state, its targeted production repeat passed. This test-timing correction is recorded in the scenario results. Browser mutation tests intercept every API request; they verify UI state and request contents. Backend tests exercise handlers, permissions, revisions and rendering separately. This is broad scenario coverage, not proof of every possible control-state combination or real paid AI output.

## Reproduce

Start Vite on port 5192. Set `PLAYWRIGHT_MODULE` to an installed Playwright package; Chrome must be available. Generate a disposable media fixture:

```sh
ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=240x426:rate=10 -t 12 -c:v libx264 -pix_fmt yuv420p -y /tmp/lumen-qa-video.mp4
WORKSPACE_MEDIA=/tmp/lumen-qa-video.mp4 node frontend/tests/ui-audit.browser.cjs
WORKSPACE_MEDIA=/tmp/lumen-qa-video.mp4 node frontend/tests/navigation.browser.cjs
node frontend/tests/workspace.browser.cjs
node frontend/tests/render-summary.browser.cjs
npm --prefix frontend run build
npm --prefix frontend run test:locale
.venv/bin/python -m pytest backend/tests/test_render_summary.py backend/tests/test_manual.py -q
```

For full rendering tests use Linux FFmpeg with ASS/subtitle filters. The default full suite does not opt into paid external tests.

Production backup: `/opt/lumen-rebuild/backups/ui-audit-20260918-104741`. Only the web process was restarted; active worker jobs were not interrupted. Temporary QA login session is revoked after verification.
