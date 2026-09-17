# Platform cuts protect saved master speech

Platform AI planning, worker validation and manual variant edits previously protected only the initial analysis transcript. They now also protect saved master caption/transcript intervals, remapped through the master cut order. This includes manually corrected speech even when captions are hidden. Removed source spans do not create phantom output speech. Duplicate ranges are deduplicated; legacy masters fall back to manual_transcript where available.

The same helper runs in both platform planning/rendering and the manual edit endpoint. It uses the saved master snapshot rather than later editor drafts. Initial speech remains protected if a caption was deleted; disabling subtitles is not permission to cut a spoken sentence.

Local tests: 6 passed, including an API rejection of a scene-boundary cut that falls inside corrected speech, unchanged package preservation after rejection, allowed full-span edit, reordered timeline mapping and legacy fallback. No paid AI requests.

Server verification: 16 tests passed in isolated lumen_qa schemas, including five-platform render/export in legacy and editable-caption modes, aspect ratios, audio, locks and revision history.
