# Creative layers — deployed 2026-09-16

AI proposals now support visual_card and sound_effects modes, each scoped to its own clip layer. Proposals are reviewed and accepted before separate approval. Unchanged/no-op proposals cannot be applied. Existing locked clips and revision guards remain enforced.

Visual cards use the existing bilingual number/comparison renderer. Prompt requires supplied data and source attribution; human factual review remains necessary. This is not automatic fact verification or support for maps/charts.

Sound accents: original synthesized chime, click, whoosh; clip-local timestamps, four maximum per clip, -36 to -12 dB amplitude. Render mixes approved accents onto the source audio with a peak limiter. Source-only videos without audio receive a silent bed plus scheduled effects. This is not music selection, beat synchronization or sophisticated sound design.

Validation: local selected backend suite 89 passed, 2 skipped, 1 deselected. Actual audio-energy checks verify silence outside the requested interval. Proposal API tests exercise review/acceptance and unapproved state. Frontend production build passed (index-D7ETLtHE.js). An additional full real-render test passed: source audio preserved, unapproved effects excluded; all six creative-layer tests passed. Paid AI calls not made.

Previous staging block resolved. Full suite on isolated lumen_qa PostgreSQL database: 100 passed in 58.12 seconds, including ASS rendering, full upload-to-download integration, and new sound effects. No active production jobs at deployment. Backup: /opt/lumen-rebuild/backups/creative-layers-20260916-090157. SSH disconnected at the end of deployment; independent reconnect confirmed installed sound module, both services active and new index-D7ETLtHE.js published. Original VM and pg1/pg2 untouched. Live AI creative quality and interactive browser UX remain unverified.

Remaining scope: music library/rights/ducking/beat alignment; advanced graphics; external and generated B-roll in the Director workflow; complete platform export adaptations; bounded automatic rendered-quality revision. These are not claimed complete by this change.
