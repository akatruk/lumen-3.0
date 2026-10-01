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

## Hypit prompt boundary

Lumen-fix only assembles the prompt for Hypit
(`https://github.com/hypit-ai/hypit`). Lumen stays the app, the project, the
sliders, and the review surface. Hypit generates the video from that prompt.

Sliders and every control in «Эффекты» change that prompt. Hypit renders it.
Card pixel size is not a Lumen effect. Duration share (10% of a 1-minute video
= 6 seconds of animation) and intensity (5–100, step 5) are prompt inputs, not
CSS. Do not invent a parallel composition engine: no plate CSS, zoom, font
size, seek-script geometry, timeline cuts inside `index.html`, or a second
renderer.

The main prompt visualizes the host's words. While a phrase is spoken, the
foreground is a graphic of that thought and the host is a circle; the footage
stays sharp. Profit or growth is an arrow moving up. Risk or a fall is an
arrow moving down. A spoken number is a large figure. Steps appear one by one.
A comparison is two columns. A deadline is a mark on a scale. Do not invent
facts. At 100% this treatment covers the whole minute. A lower percent covers
that share of each minute, and the rest is the host full frame.

The handoff is that one prompt. Hypit builds it into one video. Lumen does not
cut the footage into scenes, does not set a parameter on each frame, and does
not concatenate those pieces.
