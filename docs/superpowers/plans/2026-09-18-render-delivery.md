# Render delivery and visible effects

Evidence: final2 current Master has a single 162.1-second unchanged scene. Saved manual scene has 1→1.2 zoom, approved=false, normalization, and music; no later picture render exists. Audio-only delivery has updated Russian voice/music independently. AI proposals remain unaccepted; basic recommendations are unapproved. Existing rendering really applies approved edit fields, but the UI does not show this divergence at the player.

Implementation:
1. Compare saved intended picture timeline against actual Master timeline, independently of revision, review flags, and audio-only delivery. Expose pending visual changes, final scene count, and selected audio override in manual responses. Surface beside player with direct review action, and inside preflight. Refresh on Master identity change.
2. Summarize slow full-scene camera moves honestly; offer a 4-second movement duration for the zoom preset. Make duration executable in FFmpeg, draft preview and timeline, without changing old saved edits or locked scenes.
3. Reject partially unapproved renders at the API boundary rather than silently dropping scenes.
4. Verify actual rendered pixels for short-duration zoom and existing manual/auto trims, graphics, cutaways and audio using Linux FFmpeg; browser-test stale final status, review path and preset duration.
5. Publish tested change and report what is and is not included in final2. Do not silently accept AI proposals or replace the user's final/audio with a test render.
