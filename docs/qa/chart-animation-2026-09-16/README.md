# Chart animation

Optional grow animation for bar charts and rankings. ASS rectangular clipping reveals each bar from the shared zero baseline to its final proportional width. Numeric labels remain final values, so animation does not manufacture intermediate data. Duration 0.2–2 seconds and at least 0.15 seconds shorter than card interval. Default none preserves existing projects. Unsupported card kinds reject grow mode.

Editor exposes animation mode and duration; proposal preview names the animation. AI visual-card prompt supports it. Existing proposal approval and locked-decision guards remain in effect. No live paid AI quality test or interactive browser test.

Scope: proportional bar reveals only; no animated maps, changing datasets, or general-purpose motion-graphics editor.

Validation: full isolated PostgreSQL backend suite 109 passed in 65.31 seconds. Real-render tests compare pixels before/during/after animation for charts and rankings. Two rendered frames inspected visually. Frontend build index-D9Rw-490.js passed.

Deployed on the new Lumen VM with no active jobs. Backup /opt/lumen-rebuild/backups/animation-20260916-094210. Both services active after restart. Old VM and excluded pg hosts untouched.
