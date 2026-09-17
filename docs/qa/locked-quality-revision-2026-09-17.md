# Preserve locked shots during creative revision

Previously any locked manual clip blocked both user-requested creative replanning and automatic low-quality revision proposals. Replanning now permits locked manual shots, requiring their exact identity, index, source bounds and rendering fields to survive. The server restores their saved approval/lock flags and all global edit settings (including captions, normalization and music). New/unlocked shots remain unapproved. The same validation runs during generation and acceptance. Existing revision/ownership/job checks remain; legacy recommendation locks still block replacement.

UI explains preservation in English/Chinese and labels locked shots in proposals. Provider instructions distinguish preserved external footage from unavailable new assets.

Validation: frontend production build passed. Isolated server PostgreSQL suite: 24 passed, covering creative plans, quality revisions and quality comparisons, including actual synthetic-media rendering. Tests cover generation-to-acceptance with one locked shot and one changed shot; removal, movement, trimming, text and asset changes are rejected; a saved locked external asset is retained while new unseen assets remain forbidden. No paid model calls or customer rerenders were used. This does not establish editorial quality on customer footage or provide an unattended rerender loop.

Lock follows existing manual-editor semantics: same shot index and fields, not fixed absolute output time if earlier unlocked shots change duration. Global settings are intentionally preserved conservatively while any shot is locked.
