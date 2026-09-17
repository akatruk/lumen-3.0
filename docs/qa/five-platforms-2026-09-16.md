# Five platform export packages

New packages contain Douyin, Instagram Reels, YouTube Shorts, TikTok and Xiaohongshu. Each has its own editorial title/hook, cover, post copy, CTA, subtitle file and video. All remain vertical 9:16 exports from a reviewed master; this change does not add platform-specific aspect selection or guarantee distinct edits from an AI response. No social publishing was added.

Existing three-platform packages can still be reviewed, edited and restored. Validation accepts their exact manifest platform set while requiring all five for new generation. Duplicate platforms are rejected. UI progress and approval counts use package size rather than a hard-coded three.

Validation: eight isolated PostgreSQL/server tests passed, including real FFmpeg creation of all five videos and retained audio in TikTok/Xiaohongshu outputs, plus legacy three-platform editing. Seven local studio tests and frontend build passed. AI plans in render tests were fixtures; real-provider editorial quality was not measured.

Deployment backup: backups/five-platforms-20260916-132541. New JS index-DMZxWRJH.js.
