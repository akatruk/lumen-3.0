# Full workflow verification — 2026-09-16

Dedicated lumen_qa PostgreSQL schema, isolated code directory on the new Lumen VM. No production account/project created or changed. No external AI/TikHub charges.

New regression: backend/tests/test_full_flow.py. Actual 40-second vertical synthetic video with audio, chunked HTTP upload and saved-offset checks, exact source-byte comparison, real preparation/proxy generation, deterministic Director response, real media-library upload, real candidate sample reel generation, deterministic B-roll suggestion, explicit acceptance, rejection of unapproved rendering, approval, queued worker render, output duration/audio/pixel checks, authenticated download and exact downloaded-byte comparison. Passed in 19.21 seconds (server-local API test, NOT an internet upload speed measurement).

Additional PostgreSQL suites: uploads, Google authorization, Douyin adapter, director revisions, variants, variant revisions — 33 passed. Frontend TypeScript/Vite production build passed.

Initial test fixture corrections: upload creation returns HTTP 201; owned source must be at least 30 seconds and vertical. These were test-fixture mismatches, not production fixes.

Limitations: external AI responses mocked and reference DNA cached; live semantic quality, fresh TikHub retrieval, interactive Google sign-in and browser UI journey were not exercised. Browser automation tool unavailable in this session. This does not certify the complete live user flow, mobile upload speed, or completion of every Lumen 2.0 feature.
