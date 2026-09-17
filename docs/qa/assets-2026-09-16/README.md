# Project B-roll media library

Added private immutable project assets through the existing adaptive resumable uploader. Completion creates an asset rather than an analysis project. Asset uploads have their own retry/completion namespace; attribution and rights confirmation required. Up to 20 videos, 250 MiB and 180s each; disk/storage constraints checked.

Library previews and a per-clip placement selector support source in-point and clip-relative insertion times. Each clip uses either source cutaway or library B-roll, never both. Manual saves and render jobs validate project ownership and asset duration. Renderer resolves paths internally and keeps the base audio; uploaded file audio is not mixed in. Asset IDs and timings persist in the Director Timeline. Enclosing clip locks/approval govern placement. AI regeneration currently must preserve external B-roll because the model has not inspected those assets.

This is a user-supplied library, not stock search, semantic retrieval or generated footage. Those requirements remain open. Browser automation tools unavailable this turn; frontend build and API/render tests used. No paid AI requests.

Final isolated Linux suite: 82 passed, 2 skipped. PostgreSQL assets/manual/upload tests: 15 passed. Frontend TypeScript/Vite build and upload recovery tests passed. Actual external-video render verifies insertion and return to base footage; existing audio-preservation render remains passing.
