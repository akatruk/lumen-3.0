# Reviewable beat alignment

The manual editor can request a no-charge preview aligning multiple safe adjacent cuts with cached music accents. Music source offset and excerpt looping are mapped to final output time. Shifts are bounded to 0.35 seconds, keep each side at least 0.5 seconds, retain source coverage and total duration, and never cross a spoken interval (including a 0.12-second margin).

Locked shots, discontinuous source cuts, non-cut transitions and shots with timed overlays/inserts/effects are skipped. All current shots must first be approved and saved. Proposed changed shots become unapproved; the response only enters a local draft on explicit action. Existing save/revision checks govern acceptance. Music and finished renders stay unchanged.

Server targeted run: 18 passed across beat preview, creator-style compatibility and manual editor tests. Includes actual video+music rendering, duration/audio checks, loop-offset math, no saved-state mutation, speech/lock/layer protection, stale revisions and cross-user denial. Accent locations are estimates, so listening and review remain necessary.
