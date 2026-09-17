# Scoped Director alternatives — 2026-09-15

Implemented: request an AI alternative for one existing unlocked Director decision, with user feedback and reference/creator context. Generation stores a separate proposal; explicit acceptance replaces only that decision and resets its approval. Other decisions and the existing master remain intact. Revision checks, owner checks, job exclusion, locked-decision protection and speech-boundary validation apply. Failed or interrupted AI requests retain the original plan. Requests use the existing $0.50 reservation and project budget accounting. No automatic retries of ambiguous paid requests.

The UI provides EN/中文 controls, proposal explanation and acceptance. It warns when the existing master comes from an earlier plan. Generation does not generate new video frames: supported operations remain remove, move_to_front, captions and normalize_audio. Reference media is never rendered into the output.

Validation: 59 PostgreSQL tests passed; production frontend build passed. Added tests cover proposal/acceptance, unchanged plan before acceptance, failed provider, ownership, locked decisions, stale proposals, preservation of other approved/locked decisions, and speech cuts. Real OpenRouter QA in an isolated schema passed, costing $0.02246925. AI proposed moving the owned title-card range 6–16 seconds to the opening; explicit acceptance advanced revision, reset approval and preserved the old master. This was a synthetic silent video, not proof of editorial quality. See live-report.json.

Browser read verified the new proposal block, accepted alternative, reset approval and final earlier-master warning. Interactive final form/language-switch check was not completed because automatic approval review twice returned model-capacity errors. Earlier DOM inspection was successful. No production login was bypassed.

Remaining: generated/replacement footage, richer editing tools, multi-asset timeline, complete plan restore UI, native platform adaptation, real business-video quality pilot, updated onboarding and publishing/analytics. This release does not close FR5 in full.

Deployed to new VM with backup `/opt/lumen-rebuild/backups/director-alternatives-20260915-074901`; web and worker active. Final frontend bundle: `index-OUBRBsSj.js`.
Public checks after release: health 200, frontend asset 200, unauthenticated alternatives endpoint 401. Isolated QA server stopped.
