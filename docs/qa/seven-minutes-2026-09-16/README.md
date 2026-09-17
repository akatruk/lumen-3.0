# Seven-minute limit

User cancelled direct TikTok/Douyin link import before deployment. Removed unpublished reference_links module and resolve route, TikTok CDN additions and platform routing. Direct URL UI was not added. Existing Douyin search remains.

Unified maximum duration to 420 seconds for owned uploads, searched/imported video references and library assets. Exact 420-second videos are accepted; >420 rejected. Existing 30-second minimum for owned studio uploads and 250 MB size limit remain unchanged. Updated EN/ZH UI and env example.

Preparation now derives proxy video bitrate from source duration (12 MiB target budget including 64 kbps audio, capped at previous 600 kbps video). Full timeline and audio retained; existing 16 MiB hard size check remains. This reduces visual detail for longer sources rather than trimming them.

Tests include exact API/search duration boundary and real 420-second video preparation with audio, duration and size checks. Live AI interpretation of a seven-minute customer video is not part of this test.

Validation: full isolated PostgreSQL suite 114 passed in 151.14 seconds. Frontend build index-B6ZCtHvI.js passed. First deployment deferred because one live studio analysis was running; release waits for idle worker before restart.

Deployed after the active job completed. Backup /opt/lumen-rebuild/backups/seven-20260916-101439 includes prior private server environment. Production duration override set to 420; services healthy. Direct-link feature remains cancelled and unpublished.
