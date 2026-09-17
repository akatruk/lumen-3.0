# Moving-shot transitions

Crossfade, zoom, wipe and circle now combine moving outgoing/incoming footage across the cut instead of holding an outgoing PNG. Four frames on either side at 30 fps form an eight-frame transition. Tail/head playback is slowed locally to preserve total duration without adding footage outside approved source ranges. Short clips use smaller windows.

Audio streams are copied unchanged for both clips. Source/output range mapping and subsequent caption/music timing remain unchanged; visual synchronization displacement inside the transition is bounded by 133 ms. Fade-to-black behavior remains separate.

Local FFmpeg tests: 5 passed. Tests cover every transition, both clips' audio and duration, eventual incoming image, visible blending before the boundary, silent inputs and temporary-file cleanup. Server integration validation is recorded below after completion.

Isolated server PostgreSQL/FFmpeg validation: 17 passed in 54.47 seconds (transitions, creative effects and full flow). No paid AI calls were needed for this block.
