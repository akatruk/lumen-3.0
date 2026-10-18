# Decision

Implement concept B only, as `designProfile: "spatial_v1"` on the existing semantic payload.

Absent, empty, or any other value keeps the stem drawing. `motion.process_timeline.v1` and `motion.numeric_range.v1` are the same components.

Timeline: one row per source label, slots reserved so the first word does not jump when the next arrives. A word is painted only after its `at` time. A hairline is drawn only between rows that are already open. The active row gets the accent bar and the title role. Quiet rows stay in the support role.

Range: the two spoken strings sit at the ends. The stem draws across the graphic width using the existing `rangeMotionAt` windows (low 2–10, span 8–24, high 16–26). The kind word sits between the ends. `range.unit` is painted only when the payload has one.

No second implementation pass. The rendered frames match the selected stills, and the remaining darkness is empty ground around short labels, not a broken rule.
