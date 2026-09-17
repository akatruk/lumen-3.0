# Stable beat alignment and skip explanations

The alignment candidate filter previously excluded accents within 25 ms of a cut, then could move that already-aligned cut to a worse neighbouring accent. The proposal now leaves those cuts untouched. Repeating alignment after approving a proposal remains stable for the same track and accents.

Preview responses expose per-cut skip reasons: already aligned, locked, timed overlays/effects, discontinuous source or transition, speech, minimum shot duration, or no nearby accent. The EN/ZH preview identifies cuts by ordinal rather than internal IDs. Changes remain a reviewable unsaved draft, with altered shots requiring approval again.

Validation: 7 local non-render tests passed; 21 isolated server tests passed, including real synthetic rendering with unchanged total duration and audio. Frontend production build passed. No paid AI calls. This remains bounded onset-based alignment, not full musical phrase analysis.

Headless Chrome fixture verified both languages display already-aligned and speech-protection reasons. Deployment backup: `backups/beat-stability-20260917-120356`.
