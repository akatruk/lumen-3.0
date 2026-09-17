# Upload interruption fix

Observed production access log: POST /api/studio/projects returned HTTP 400 with zero response bytes. No corresponding application traceback; disk had 20 GB free. This supports an incomplete upload request before project creation; existing logs do not identify the precise client/network reason. The old uploader sent a whole video as one multipart request and reported an unhelpful generic error, incorrectly promising the source was saved.

Replaced browser upload with authenticated 1 MB chunks. Each acknowledged offset is persisted; an interrupted request checks that offset before retrying. Temporary transfers expire after 24 hours, with a limit of five per user. Completion reuses existing source validation and idempotent project creation. Uploading chunks never starts an AI job. Lost completion responses retry the same request ID; completed-request lookup avoids retransmitting an already accepted video. Existing multipart clients remain supported.

Validation: isolated server 76 passed, 2 skipped; isolated PostgreSQL upload/project tests 8 passed. Browser uploader logic tested with mocked lost chunk and completion responses, correct offsets and no retransmission of completed projects. Frontend production build passed. No paid AI requests.

Limits: new code requires refreshing the page. Old interrupted multipart uploads cannot be recovered. Resume uses the same file metadata and browser tab session storage; it is not a cross-device upload. Actual throughput still depends on the user's connection. No claim that the exact user's connection was reproduced.

## Large-file follow-up

Recent failed traffic still used POST /api/studio/projects (legacy multipart); there were zero resumable upload sessions. The inspected in-app tab also held an older JS bundle (and was on sign-in, so it was not necessarily the user's active upload tab). Server was 99–100% idle, disk 17% used, no configured upload rate limit. These observations do not prove the user's network cause or an inherent 8% threshold.

Added uncached explicit HTML entry routes, ignoring stale conditional HTML requests; assets remain available for existing tabs. Increased client chunks from 1 MiB to negotiated 4 MiB (75% fewer requests, not a promise of 4× throughput). Added server-confirmed transferred bytes and average MB/s to progress. Safe Nginx logs now include timestamp, request length, request time and upstream response time without query strings or credentials.

Validation: frontend build and recovery tests; 32 MiB API transfer with replayed chunk and SHA-256 equality; cache-header regression; 10 isolated server tests plus the same 10 on PostgreSQL QA passed. No paid AI calls. Users must reload an already-open old application to activate new code.

## Slow-link timeout correction

Observed actual 4 MiB request: 119.360s total, 0.037s upstream application processing. Earlier incomplete chunk received ~2.26 MB then Nginx returned 408 with no upstream. Increased chunks were inappropriate for this connection.

Removed the browser's total-duration timer on file PUTs (metadata/completion requests retain their bounded timeout). Start with 256 KiB; double only when a chunk finishes under 3s, halve over 15s, bounded 256 KiB–4 MiB. Reset chunk size on transient failure and handle HTTP 408 as retryable. Nginx client-body inactivity allowance increased from 120s to 1800s; this is not a 30-minute whole-file limit. Cancellation remains available.

Frontend recovery tests assert no active duration timer during file PUT, validate lost responses and adaptive growth. Production frontend build passed. Static assets published with graceful proxy reload, no backend/worker restart.
