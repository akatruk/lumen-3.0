# Main consolidation — 2026-10-18

Requested scope: consolidate local development branches and pending source changes into main. No deployment.

All local branch tips are ancestors of the integration. The independent tips were experiment/create-project-ux, fix/editorial-retention-integration, feat/visual-effect-plaque and fix/menu-slide. Overlapping older implementations were retained in history; newer Studio, semantic planning and renderer memory limits take precedence in the final tree. Pending source changes from the primary checkout and remaining worktrees were reconciled. Obsolete local-baseline speech tests are preserved in legacy-speech-understanding.py.txt; active coverage follows the model-backed planner API.

Recovery: /tmp/lumen-main-consolidation/before.bundle, working-tree.patch, and per-worktree patches/source archives. Original checkouts and their uncommitted files were not reset.

## Verification

- Frontend production build: passed.
- Frontend Russian localization: 4 passed.
- Frontend studio creation: 3 passed.
- Motion TypeScript: passed.
- Motion tests: 112 passed, using the existing local editorial-proof MP4 fixture.
- Focused backend tests (director, pipeline repair, language, controls, captions, database, speech understanding and passage experiment): 60 passed, 2 skipped.
- Full backend suite: 743 passed, 97 failed, 39 skipped. This is NOT a verified release.

Full-suite failures include old tests that write Studio surfaces already retired in origin/main, missing local media/benchmark fixtures and other unresolved integration/provider expectations. Do not assume every failure predates consolidation. Full delivery/browser lifecycle has not passed. No production code was deployed and no services were restarted.

Large local media outputs, model caches, node_modules and secrets were not added to Git. The local asset manifest was copied only as a verification fixture.
