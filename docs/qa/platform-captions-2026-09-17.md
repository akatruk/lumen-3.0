# Independent platform caption rendering

New master renders retain a private caption-free companion when Lumen captions are enabled. The companion copies the pre-caption picture and final processed audio without another video encode. Duration, dimensions and audio presence are checked. Masters without Lumen captions reuse the normal file. Source-embedded text, scene labels and graphics remain.

Each platform version supports inherit/custom/off and independent caption size, top/bottom position and white/yellow color. Captions preserve transcript/emphasis and map source → master → platform timestamps. The exporter uses the clean picture and one subtitle layer; manual changes create an immutable package revision requiring review. Old masters retain existing exports and reject custom/off requests until a new master is rendered. EN/ZH UI explains the limitation.

Verification: frontend production build passed. Final isolated server/PostgreSQL suite: 22 passed in 59.06 seconds. Server tests cover five-platform exports for legacy and clean masters, source/scene reorder timing, missing clean-file refusal, legacy API refusal, and actual EN/ZH renders. Decoded audio hashes match between captioned and clean masters; pixel checks distinguish the subtitle-bearing image from the clean image. The first pixel test used an invalid FFmpeg timestamp `.5`; corrected to `0.5` before the final run. Local real-render test is unsupported by the installed FFmpeg without ASS; render checks run on the server.

No paid AI requests or customer rerenders. The extra companion consumes disk space; no claim of removing captions already present in original footage. This change provides manual per-platform styling, not automatic text-placement or occlusion detection.
