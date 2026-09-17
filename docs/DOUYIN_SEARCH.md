# Douyin search and import

Implemented on 2026-09-14 in lumen-fix using the TikHub integration and server-only credentials found in the user's local Lumen repository.

## Product flow

Studio → Search Douyin → results → Improve this video → goal/output language/aspect/budget → Import & analyze. The imported original enters the same worker analysis and optional rendering pipeline as a manual upload. Projects retain Douyin ID, author and original share URL. EN and Simplified Chinese UI are supported.

Search uses POST /api/v1/douyin/search/fetch_general_search_v1 with keyword, cursor, sort_type, publish_time, filter_duration=0, content_type=1, search_id and backtrace. This matches the old Lumen API search path. Default sort is likes descending; relevance and newest are optional. Publish filters: all, 1, 7, 180 days. Video-only results under 180 seconds are included; unknown duration/date remains eligible, with actual duration validated during import. Ads and image/slideshow posts are excluded. Sorting applies within each returned provider page, not a guaranteed global ranking across all of Douyin.

Import resolves fresh playback metadata through GET /api/v1/douyin/web/fetch_one_video using the selected immutable aweme_id. The result identity must match. Download is bounded to 250 MB, verified with ffprobe, and atomically promoted to the source file. Failed imports are retryable. Repeating the same result import returns its existing project. Download URLs cannot be supplied by the browser; only server-returned URLs on allowed public Douyin/ByteDance CDN hosts are used, with every redirect validated. API credentials are never forwarded to media hosts. Covers are served through authenticated owned-result endpoints.

## Operations

TIKHUB_API_KEY and TIKHUB_BASE_URL live in the private server .env. TIKHUB_DAILY_REQUESTS defaults to 100 combined provider searches/detail requests across accounts per rolling 24 hours. This is a request cap, not an exact monetary budget. TikHub charges are separate from OpenRouter AI project budgets. Searches are cached per user/query/page for 5 minutes; import selections expire after an hour. Three concurrent projects/account and existing storage constraints remain in force.

## Validation

- Live keyword 咖啡 returned 12 eligible video results from TikHub.
- A selected result was resolved, downloaded and probed both locally and from the new VM: 21.533333s, 576×1024, H.264, audio present, 3,155,343 bytes.
- Browser validated results, cover images, import options, creation of a queued project and original Douyin attribution on an isolated local test app using the captured real search response. No QA account was added to production.
- All 38 backend tests passed on the new VM; frontend TypeScript/Vite production build passed.
- Paid AI analysis/render was not re-run on this external test clip; the existing pipeline is reused. This release does not claim full parity with old KOL/R2/script-matching workflows.
