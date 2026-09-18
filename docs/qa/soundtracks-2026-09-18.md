# Reusable soundtrack collection — 2026-09-18

Deployed six real tracks from the official Kevin MacLeod catalogue: Life of Riley, Carefree, Dream Culture, Easy Lemon, Cipher and Clear Air. Checked the source catalogue attribution against https://incompetech.com/music/royalty-free/music.html and licensing page https://incompetech.com/music/royalty-free/licenses/. Each pinned manifest entry includes a SHA-256, source and license URLs, duration and attribution text. Recordings are provisioned on the host, not committed to Git. This is a curated starter collection, not a popularity chart.

Added authenticated collection/previews, private favorites, owned music reuse and idempotent imports as normal studio_assets. No saved edit, speech track, render or spending is changed by importing. The picker supports RU/EN/ZH, search and mood filters, one preview at a time, credit copying, missing tracks and full-library notices.

11 focused backend tests passed locally and on the Linux host. Frontend production build passed. Chrome fixture checks passed for tabs, favourites, one-click import, real audio decoding, mood filtering and 390px layout. An accessible-name issue in the mood selector was reproduced from its label and fixed with an explicit localized accessible name.

Live test11: Easy Lemon decoded and played (126.380425 seconds). Asset count changed from 3 to 4; repeat import returned the same ID with existing=true. Imported asset: 1a74f1f19e0847a1a330ccdd975fcad3. Favourite persisted over reload, then the QA selection was cleared. Anonymous preview returned 401. Master remained 40786ce1be014f7da5977ecb0e7602e7 and spending remained $0.69464365. Music is available for choosing in the saved edit; no automatic re-render was started.

Deployment backed up prior app.py, db.py and frontend entry under backups/soundtracks-20260918; original backend hashes matched HEAD and no jobs were active. Both services restarted successfully. Temporary owner QA session revoked and local browser credentials deleted.
