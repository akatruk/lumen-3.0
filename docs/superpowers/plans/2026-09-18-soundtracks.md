# Background Music Library Implementation Plan

**Goal:** Reuse curated background music and owned uploads across projects without re-uploading.
**Architecture:** A fixed manifest and prepared audio files feed authenticated catalogue endpoints. Imports create normal immutable studio_assets with deterministic request IDs; favourites belong to users. React embeds the picker beside the existing project media library.
**Tech Stack:** FastAPI, existing database adapter, FFmpeg/ffprobe, React/TypeScript.

- [x] Verify six official source files and license text; create backend/data/soundtracks.json plus a provisioning script with SHA-256 checks. Store recordings under data/soundtracks.
- [x] Implement backend/soundtracks.py: listing, authenticated previews, owned favourite mutation and idempotent project import. Use fixed catalogue IDs or ownership-checked asset IDs; never accept remote URLs. Handle missing audio, invalid IDs, disk space and full libraries.
- [x] Register router before static mount and create favourite table during DB initialization. Add tests covering preview authentication, cross-user isolation, favourite persistence, immutable/idempotent import and asset capacity.
- [x] Add frontend/src/SoundtrackLibrary.tsx and scoped CSS: curated/favourite/uploaded tabs, mood filtering, search, audio preview, credit copying, import result/error states and RU/EN/ZH copy. Mount in ManualEditor and reload project assets after import.
- [x] Run focused backend tests and production frontend build. Verify Chrome picker actions and mobile layout.
- [x] Check production file hashes and idle jobs, back up replaced files, provision verified recordings, deploy backend and frontend, restart services, test real catalogue/preview/import in test11, revoke temporary QA session. Commit implementation and record checks.
