# Final music delivery and audio UX

Goal: A chosen track must reach the finished video and download, retain the selected voiceover, and replace rather than stack previously added music.

Evidence: AI candidate checkboxes only scope a suggestion. Accept writes studio_manual but never renders. Dubbing replaces all Master audio, including music. Current final selection only understands dubbed videos.

- [x] Add owned audio-mix versions and durable, free audio-only rendering from the immutable Master/voiceover. Bind selection to current Master and current final output; preserve previous final on failure. Replace music from the unmixed base; support removal.
- [x] Preserve a music-free audio base and music metadata on future manual renders. Retain added music when selecting or creating a different voiceover.
- [x] Put the actual soundtrack selector, preview and explicit final-apply action before the optional AI panel. Identify candidate checkboxes as candidates; AI apply updates final through the same path. Show pending/final status and separate source-track preview from rendered result.
- [x] Verify actual audio/video and normal download, ownership, stale state, failures, removal, reload and voiceover compatibility; publish and exercise existing final2 with the requested Easy Lemon track.
