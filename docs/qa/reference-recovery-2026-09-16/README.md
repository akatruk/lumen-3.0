# Live reference recovery

Failed studio project ab2fb0078d9e46f3878e1d48592f4e10: web/fetch_one_video returned HTTP 400 for Douyin 7309788558154321192 before AI analysis.

Official TikHub documented App V3 fetch_one_video_v2 endpoint retrieved the SAME identity. Download was probed: 36.5 s, 576x1024 H.264, audio present, 7,384,489 bytes. Saved as this project's reference source. No replacement reference or source upload.

Added bounded web → App V3 fallback for reference lookup. Authentication, credits, rate limits do not trigger fallback. Wrong video identity is rejected. 24 relevant tests passed; deployment backup /opt/lumen-rebuild/backups/reference-fallback-20260916-082908.

Resumed one studio_analyze job under the project's existing budget after checking failed state and no active job. No automatic rendering or approval.

Endpoint documentation: https://github.com/TikHub/tikhub-plugin/blob/main/skills/douyin/SKILL.md
