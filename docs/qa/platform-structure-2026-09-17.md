# Platform narrative controls

Platform creation accepts independently selected narrative structures: preserve order, hook/evidence/takeaway, problem/solution or comparison. These persist in the queued job and package manifest and become explicit instructions for choosing and ordering master scene ranges. The planner must explain when the footage does not support the requested structure rather than inventing material. Preserve-order requests have a deterministic chronological validator; other structures require editorial review.

Manual platform editing now supports move earlier/later and use-as-opening, without retyping source times. Existing speech-safe scene boundaries, overlap checks, immutable package revisions and approval/lock controls remain enforced. Manual revisions may deliberately override the initial structure preference; manifest structures describe the original AI request.

This is scene-range restructuring of the reviewed master, not a separate source-layer composition. Already burned-in captions/graphics travel with their footage. No paid model-quality validation was performed for this block.

Validation: frontend production build passed. Real five-platform rendering passed in the initial server run; the newly added persistence test initially selected the unrelated first job and failed. After restricting the test query to platform_variants, all 11 API/validation/revision tests passed on isolated PostgreSQL in 2.41 seconds. No production jobs or user projects were modified during testing.
