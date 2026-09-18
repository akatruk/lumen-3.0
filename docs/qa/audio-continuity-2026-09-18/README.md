# Voice and music survive a new picture render

## Root cause

final2 published Master `8e4055b0300b413dae3214a568a0ec58`, then `7bb073b029bd409891f77dfe08cc39f9`, at plan revision 10. Picture editing was present (1→1.2 zoom over four seconds). The final selection still pointed to mix `423b1104966945e298e99f423ba7828d` on Master `3d9d91ac54284c80ba4a1186e3a59c30`. The strict resolver rejected that stale video and served the new Master with original speech. This was an audio handoff failure, not a rollback of picture edits.

## Fix

- Snapshot the chosen voice and soundtrack, including recovery of a stale explicit selection left by the old renderer.
- Map voice through source-time ranges for trims, reorders and restored sections. Retain the original voice lineage, avoiding repeated cutting of already shortened voiceovers.
- Build the new picture with mapped voice, saved music and sound effects; no speech generation or provider call is needed for the transfer.
- Publish the new Master and its ready voice/music delivery in one database transaction. Failures retain the old result and selection.
- Keep clean voice separate from music/SFX, and retain original edit audio for explicit restore. Master/caption-free/music-free companions remain consistent.
- Remap downloadable translated VTT timings alongside audio.
- Manual and cleanup preflights report voice retention; unavailable voice coverage blocks rendering instead of silently reverting to original speech.

## Verification

- Linux: 57 backend tests passed, including actual FFmpeg manual and automatic render, dubbing, final music, scene mapping, consecutive renders and recovery.
- Final local five-test audio group passed, including selected music through automatic cleanup, three consecutive cuts/restorations, explicit original-audio restore, failure preservation and byte-identical current picture on repair.
- 28 browser editor scenarios passed across full run and targeted rerun after updating the intentionally changed cleanup explanation. Preflight regression and new voice-summary/error-blocking browser test pass. Production build passes.

## Production recovery and confirmation

Recovered final2 on the newest picture Master `7bb073b029bd409891f77dfe08cc39f9`:

- New selected mix: `c2a774a0875146c2b4426db12d7cbe24`.
- New aligned Russian voice version: `6ad2d1d1836a48329e145aab13534e58`.
- Easy Lemon retained at -18 dB, fade-in 1 s, fade-out 2 s, ducking enabled.
- Video packet SHA-256 exactly equals the newest Master: no picture rollback or re-encoding during repair.
- 15-second final PCM sample correlates 0.997331 with the aligned Russian voice.
- Read-only authenticated browser confirms playable current mix before and after reload, main download resolves to the same mix, and next-render preflight states voice retention. Zero writes and JavaScript errors during browser verification.
- No paid AI calls during repair. Previous media versions remain available.
- Recovery checkpoint (server only): `/opt/lumen-rebuild/data/9b3f7ca5bfe549bcadac78d63ba16757/audio-recovery-1789735612.json`.
- Published index SHA-256: `66ac1c975c9f0107be0e95eeccb4f3701f004bae76e5b2bfe7d1104f2f2e5329`.

This supersedes the separate-dubbing limitation documented in the earlier render-delivery audit. A genuinely unvoiced source range or missing selected audio fails safely; the user can explicitly choose original edit audio or generate a suitable voice version.
