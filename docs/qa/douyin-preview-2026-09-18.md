# Douyin search preview repair — 2026-09-18

The search cards rendered only cover images: there was no playback trigger or preview endpoint. Added an explicit keyboard-accessible cover button and native modal video player, independently of reference selection/import. The player has loading, failure/retry, close/Escape and external-original controls, with Russian, English and Chinese UI. Closing stops playback.

Authenticated preparation reads an ownership-checked saved search result, uses the existing restricted CDN downloader, refreshes only the selected Douyin identity if its URL is unavailable, and produces a full-length browser-compatible MP4. H.264 video is copied; other codecs use a bounded H.264 conversion. Playback supports Range requests. Preparation is serialized across web processes, byte/duration/disk bounded and cached for the result lifetime. No project, analysis or render job is created.

21 backend tests passed on the deployment host, including isolation, expiry, cache reuse, Range access, failed-media cleanup, and real FFmpeg verification that a 46.2-second source is not truncated. Frontend production build passed.

Chrome verification used the user's existing real `real estates` search records without issuing another paid search. Preparation and media requests used live endpoints and actual CDN recordings. Both selected videos decoded and played beyond 50 seconds: 56.2 seconds at 1024×576 and 81.148828 seconds at 720×1280. No media error occurred. Cached reopen, Escape, mobile cover controls and unauthenticated denial (401) were checked. A provisional 45-second cap was removed before final delivery and the two QA previews rebuilt in full.

Production app.py hash matched HEAD before deployment. Backups are under backups/douyin-preview-20260918. Only the web service required restarting. Temporary QA owner session revoked and local browser credentials removed after verification. Existing project edits and prepared videos were untouched.
