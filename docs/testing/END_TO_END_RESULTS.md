# End-to-end results

Not executed.

Blocked on purpose:

- A Qwen transcribe job was already running on lumen-fix (`3c3a87baf59e4a859ce3b085fc64e3c2`). A second heavy ASR process was not started.
- Production deploy was not approved.
- original1 and original4 were not copied or overwritten.
- No Russian, English, or Chinese fixture was uploaded through this checkout.
- No Remotion render was started, so there are no new frames to review.
- The transcript panel was not clicked in a browser.

Unit tests that did run are listed in `docs/architecture/PRODUCTION_BASELINE.md`. They do not show that a video matches the speech.
