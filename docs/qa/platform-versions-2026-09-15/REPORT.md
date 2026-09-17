# Platform export previews — 2026-09-15

This release adds three separately rendered platform previews derived from the reviewed master. It does not complete the full business PRD.

## Behavior

- The user reviews the current master and explicitly requests three platform previews.
- The job snapshots the exact master render ID; it never modifies the master or reads reference footage as render input.
- AI plans Douyin, Instagram Reels and YouTube Shorts title/hook, description, hashtags, CTA and scene ranges. All output copy uses the project's content language, independent of platform or UI language.
- Cuts may use only mapped scene boundaries from the finished master. They cannot cut through recognized speech. Original editing instructions/timestamps are not reapplied to the master.
- Every output is 1080×1920 H.264 MP4, with a distinct hook treatment, JPG cover, metadata JSON and remapped WebVTT captions. Existing master audio and burned-in captions are preserved. Silent source material produces no invented subtitles or voice.
- Full ZIP includes the master MP4, master JSON (actual timeline and review metadata), manifest and all platform files.
- Each variant remains `needs_human_review`; publishing mode is `export_only`. Nothing is automatically posted.
- A duplicate request for an already completed package does not spend again. A new master marks old versions stale. Failed variant generation does not fail or change the approved master.
- Planning reserves up to $0.50 within existing project/daily limits. Rendering is sequential on the current VM.

## Validation

- Full PostgreSQL suite passed (52 tests before final regression addition); focused tests then cover language, scene/speech boundaries, ownership, stale master, human confirmation, duplicate requests and preservation of master after variant failure.
- TypeScript/Vite build passed.
- Real QA pipeline uses a pre-existing approved synthetic travel master and OpenRouter. Three distinct MP4 files and package download are checked; master hash unchanged.
- Two issues discovered by real output inspection were fixed before deployment: platform-based language switching and reapplication of old source cut instructions to the finished master.
- Browser inspection covers queued/running states, three previews, language, descriptions and download links.

## Limits

This is an export-preview feature, not a guarantee of platform-native editorial quality. Limited source material can legitimately yield the same retained scenes in all three outputs; title/cover/copy treatments still differ. It does not fabricate edits merely to change file durations.

It does not regenerate shots/voice, provide music/SFX, expose multi-asset editing, create a full version-history UI, implement publication connectors or collect post-publication analytics. Variant copy and cuts are not yet individually editable in the UI. Human review is required for title placement, claims, pacing and suitability. No blind human evaluation or real-niche retention uplift has been measured.

A 9:16 ≤180-second export is an editorial preset, not proof that any given platform/account will accept or monetize it. See [YouTube's official Shorts duration guidance](https://support.google.com/youtube/answer/15424877?hl=en) and [Meta's Reels creative guidance](https://www.facebook.com/business/ads/facebook-instagram-reels-ads). No platform login or publishing was attempted.

## Final live evidence

All three final outputs are 26 seconds, 1080×1920, H.264, English, with distinct file hashes and source/master unchanged. Their readable previews were verified in the browser (readyState 4); the synthetic master has no audio. Scene retention is identical here because both informative title-card scenes are preserved. The complete QA project cost after three diagnostic runs is $0.047057, including earlier reference/master work; this is not a per-customer price estimate.

## Deployment

Deployed to the new VM and https://lumen-fix.universalgravity.org. Final full PostgreSQL suite: **53 passed**, with two upstream deprecation warnings. Frontend build succeeded. Both services active, existing project count remains 2, no active jobs. Public health=200; unauthenticated variant API=401; the current frontend asset is `index-BuZrRnPT.js`.

Rollback snapshot: `/opt/lumen-rebuild/backups/variants-20260915-055713`, containing previous backend/frontend and PostgreSQL dump. Old VM unchanged. The feature is available in new reference-to-owned Studio projects; legacy imported projects are not silently reclassified as owned footage.
