# Whole creative timeline proposals

The legacy Director alternatives control only supported four recommendation actions. Added a separate full-edit proposal on the main Director page, using the actual Edit/Clip renderer schema, rather than adding labels for unsupported operations.

The model can propose ordered source clips, shot types, crop/motion, cuts/fades, owned-source cutaways, factual cards, captions/highlighting, source normalization and sparse synthetic sound accents. External media and music generation are explicitly excluded. Results are drafts, not approved renders or claims of improved performance.

Proposals preserve the current plan and renders until explicitly applied. Applying replaces the manual timeline, increments its revision, clears stale local manual drafts and opens the existing editor. Every clip remains unapproved and unlocked. Existing locked manual or legacy decisions prevent full-plan replacement. Ownership, revision, active-job and budget checks apply. Failed proposal jobs preserve the ready project.

Validation includes API generation→review→apply→individual approval→render queue, ownership, lock/revision checks, invalid media and speech boundaries, failure isolation, and a real renderer test combining a reordered timeline, motion, bilingual card and sound effect.

Frontend production build passed. Full isolated PostgreSQL/FFmpeg suite: 126 passed in 124.88 seconds. Deployment backup: /opt/lumen-rebuild/backups/creative-plan-20260916-104249. Public entry points to index-B5FjsvU-.js; both services active and health OK. Real provider proposal 1e2bbff82e444c2da82ab61df39f8e1b queued for the existing project; no edit applied or rendered automatically. Browser interaction not verified.


Real-video verification exposed conflicting re-transcribed speech boundaries. Follow-up preserves the original analyzed transcript, supplies safe cut points, and provides precise boundary feedback on validation failure. The 21 affected tests, including real rendering and transcript reuse, passed after this change. Backup: /opt/lumen-rebuild/backups/creative-speech-20260916-104644.

Final real proposal 574303703d104e86b49183fa6a7e0f49 is ready: 18 clips, 161.5 seconds, text labels and 4 sound accents; 19 original caption entries retained, subtitles disabled because the source already has embedded captions. All clips unapproved. This particular model proposal did NOT add motion, cutaways or data cards; those capabilities are available but cannot be claimed as applied to this draft. No automatic acceptance or rendering of user content. Music and external B-roll generation remain out of scope for this increment.
