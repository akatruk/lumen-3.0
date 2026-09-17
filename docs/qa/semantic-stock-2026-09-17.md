# Scene-grounded automatic B-roll discovery

A durable stock_discover job snapshots a saved scene, overlapping transcript/observations and creator context. One budget-reserved AI request generates up to three English Commons video queries with bilingual narrative purpose and cautions. The worker executes the queries, applies existing CC BY/CC0/public-domain eligibility checks, deduplicates page IDs and saves up to 12 private candidate records for the existing import pipeline.

The scene UI starts discovery, polls status, shows purpose/cautions and loads candidates automatically. Stale saved revisions are marked and do not automatically load into the current results. Search failure preserves the edit and project status. Restart recovery marks interrupted requests failed rather than replaying paid requests. Access control, scene IDs, revision, lock and pending-job checks are enforced server-side. Unsaved edits disable discovery.

Results are semantic query + metadata retrieval, not visual verification of returned videos. Exact event/property identity and license suitability need review. Import and placement remain explicit; imported library candidates can use the existing visual matching workflow. Provider scope is Commons, not commercial archive/news catalogues.

Validation: 7 isolated server tests passed (ownership, stale/locked scenes, query execution/deduplication, import compatibility, failure isolation and worker behavior). Frontend build passed. Live synthetic integration results recorded below.

Live integration: synthetic 40-second Earth-rotation card → real OpenRouter query planner → real Commons searches passed in 11.52 seconds. Three queries returned 12 eligible metadata candidates; settled AI cost $0.007479. A prior launch failed before the API call because the test runner inherited root's temporary-directory identity; rerunning as lumen with its normal identity fixed the harness. The final code uses a focused SearchPlan system prompt instead of the generic editor prompt. No customer media was sent for this test.
