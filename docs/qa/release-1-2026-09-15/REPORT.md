# Reference-to-owned workflow — release 1

Deployed 2026-09-15 to https://lumen-fix.universalgravity.org on 142.93.248.163.

## Delivered

- New-project flow searches Douyin through the existing TikHub integration and selects 1–5 reference videos.
- A separate owned portrait video (30–180 seconds, up to 250 MB), rights confirmation, script, topic and creator profile are required.
- Topics: real estate, citizenship abroad, travel. English and Simplified Chinese UI and analysis text.
- References receive shot-level Video DNA: observations, visual form, narrative role, movement, transitions, subtitles, music, emotion, information density and reusable techniques, with uncertainty statements.
- Director recommendations link a reference technique and timestamp to an evidenced change in owned footage. Supported actions: remove, move to front, captions, audio normalization.
- Users approve recommendations, edit applicable time ranges and lock decisions. Unlocking must be saved before changing a locked decision. Revision checks prevent stale writes. Unsaved drafts survive navigation within the browser tab.
- Rendering snapshots the approved plan and reads the owned source only. The resulting master can be previewed and downloaded. Project spending and AI quality review are visible.
- Duplicate creation retries use an idempotency token. Studio projects cannot bypass approval using the legacy render endpoint.
- Existing projects retain their previous workflow.

## Validation

- Full backend suite: **45 passed**, including real FFmpeg rendering, ownership, schema validation, revision conflicts, locks, render snapshots, idempotency and legacy endpoint restrictions. Two upstream test-client deprecation warnings.
- TypeScript and Vite production build passed; git diff whitespace check passed.
- Live integration in an isolated VM directory, using real TikHub and OpenRouter: search → reference analysis → owned-source plan → manual approval and lock → FFmpeg render → AI review → download.
- Synthetic owned travel title-card clip: 32 seconds, 360×640. One evidenced removal of a six-second blank opening. Output: 26 seconds, H.264, 360×640. Source hash unchanged; no automatic approvals. OpenRouter spend: $0.0244425 (TikHub costs excluded).
- Browser checks: reference cart, creator profile, reference DNA, playable 26-second master (readyState 4), unlock/save revision update, editable range, draft restoration after library navigation, blocked render for unsaved changes, Chinese localization.
- Public production checks: HTTPS health 200, latest frontend asset served, studio API without login 401. Both web and worker services active. Existing two projects preserved.
- Production rollback backup: `/opt/lumen-rebuild/backups/release1-20260915-050902`, containing code and SQLite-consistent database backup. No queued/running jobs at deployment. Old Lumen VM untouched.

## Not delivered / limits

This is the first working vertical slice, not completion of the full business PRD.

- One owned input clip per project; no multi-asset editor or reusable profile library.
- No independent regeneration/replacement of shots, new footage generation, or voice regeneration in this flow.
- Only Douyin reference search is connected. Instagram Reels and YouTube Shorts are target destinations; their search and publishing are not connected.
- The output is one master. Three platform-native video variants, covers, titles and publication packages remain unimplemented; the UI explicitly labels them planned.
- No auto-publishing, connector approval flow, performance analytics, or proven retention lift.
- Synthetic live test establishes pipeline correctness, not editorial quality on real estate, citizenship or travel source footage. Human review remains necessary.
- Browser testing used an isolated local QA session and a copy of the integration data; production Google login was not impersonated or bypassed.
