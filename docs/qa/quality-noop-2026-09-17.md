# Reject unchanged quality-fix claims

Quality revision validation now compares the proposed executable edit with the approved portion of the saved edit that was reviewed. A claim that any review issue is addressed is rejected when the executable edit is unchanged. New clip IDs, approval/lock flags, shot-role labels, explicit default motion endpoints, and inactive caption styling do not constitute a fix. Honest not_applied responses remain valid. The comparison runs after server caption/music restoration and lock preservation.

This is a no-op guard, not proof that a changed edit solves a specific defect. It does not identify every perceptually equivalent render (for example, splitting contiguous clips). A new render and review are still needed to assess actual quality. Legacy revisions without a saved manual edit retain their prior behavior.

Local quality-revision tests: 6 passed. No paid AI requests.

Server validation: 27 tests passed in isolated lumen_qa schemas, including actual synthetic rendering and creative-plan lock preservation.
