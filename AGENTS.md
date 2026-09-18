# Lumen working agreement

The user has experienced repeated regressions where saved edits, voiceover or
music did not reach the final video. Treat the finished, downloaded media as the
acceptance result, not an enabled button, an API success response or a completed
job alone.

For changes affecting editing, rendering, audio, delivery selection or versions:

- Follow `docs/RELEASE_CHECKS.md`. Run the affected complete lifecycle with the
  real browser, API, worker and renderer, including a second render, page reload
  and download. The reusable entry point is `scripts/verify_release.py`.
- Confirm the player and main download resolve to the same selected delivery,
  and selected voice/music survive a new picture render. Check actual frames,
  duration and audio; a plan summary alone is not proof of application.
- Retain the previous finished output on failure. Never make the UI appear
  successful by silently substituting source footage or an older picture.
- Use an isolated project and database for destructive scenarios. Verify the
  user's affected project without modifying it unless repair is needed and
  authorized. Keep a recoverable copy before repairing existing media.
- Run relevant UI, backend, build and localization checks. Fix discovered
  failures and repeat the affected flow before deployment. Do not rely only on
  mocked API browser tests for delivery behavior.
- State what was actually verified and what used synthetic AI/TTS fixtures.
  Do not claim live editorial quality or provider behavior from fixture tests.

Continue authorized diagnosis, fixes and verification autonomously. Do not ask
the user to discover regressions one button at a time or repeat tests that can
be performed in the available environment.
