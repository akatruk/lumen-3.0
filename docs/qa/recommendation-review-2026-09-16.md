# Analysis-to-edit accountability

New creative plans must address every initial recommendation with an implemented/not-applied outcome and bilingual reasoning. The server verifies implemented claims for full interval removal (including source cutaways), complete recommended opening, captions and normalization. Unsupported generation cannot be claimed. Inappropriate edits can be declined with a reason; no forced decorative operation or extra AI pass is added. Existing snapshots remain compatible. Validation also runs when accepting the proposal.

EN/ZH UI exposes these outcomes as proposed edits, not completed renders. This does not independently verify subjective reasoning or guarantee editorial quality.

Validation: 28 local tests passed for AI contracts, plan validation and executable audit; frontend production build passed. Fifteen isolated PostgreSQL tests on the server passed, including synthetic upload -> analysis -> creative plan -> review -> asset insertion -> real FFmpeg render -> download. AI responses in those tests were fixtures; no paid generation or real-user quality evaluation was performed.

Deployment backup: backups/recommendation-review-20260916-130931. Deployed after checking zero active jobs. Initial health request hit a startup 502; service startup completed and subsequent local and public health checks returned ok. Bundle index-DhVfNyHF.js.
