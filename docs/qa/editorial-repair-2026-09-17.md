# Bounded recovery for editorial proposals

Completed malformed responses in timeline proposals, stock query planning and candidate ranking now receive the same single repair attempt as director planning. Timeline semantic validation runs inside the provider call, so an out-of-range insert or prohibited clip mutation can trigger repair before the job fails. Each attempt uses existing budget reservations; ambiguous network errors, credit rejection and truncation are not blindly replayed. Saved edits still require explicit application and approval.

The interface explains the per-call $0.50 reservation and maximum one repair. Tests cover recovery, the two-call ceiling, semantic-validator feedback and stock fallback behavior with mocked provider responses. No paid model requests were used for these checks.

Verification results: full pre-change isolated PostgreSQL suite 222 passed / 4 skipped in 237.86 seconds; final changed-code targeted server suite 45 passed in 11.93 seconds. The skipped tests require opt-in paid provider calls. Production build passed, deployed services and external health endpoint are healthy. Full-suite coverage uses fixtures and synthetic media; it does not prove editorial quality across real customer footage.
