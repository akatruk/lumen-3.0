# Lumen 3.0

English / Simplified Chinese video intelligence and editing studio.

Live application: https://lumen-fix.universalgravity.org/

Product scope: [LUMEN 3.0 requirements](docs/product/LUMEN_3_REQUIREMENTS.md).

## Workflow

1. Find reference videos through the Douyin/TikHub integration and upload owned footage (up to 7 minutes / 250 MB).
2. Analyze reference DNA and source footage, then review an AI-generated Director Timeline.
3. Approve, replace, regenerate or lock editing decisions. Adjust cuts, framing, transitions, captions, graphics, B-roll, music and sound effects.
4. Render and review the result; low quality scores can produce a revision proposal.
5. Export platform versions with editable ranges, captions, covers and duration limits.

Google SSO uses an email allowlist. Production uses PostgreSQL, a durable job worker, private local media storage, resumable uploads and per-project AI budgets. External media features include Commons search/import, licensed uploads and optional illustrative generation. Automatic publishing is not implemented.

The current capability matrix and limits are documented in [implementation status](docs/product/remaining-implementation.md). Verification reports are in [docs/qa](docs/qa). Passing technical tests does not guarantee editorial quality for every video.

Editing and delivery changes must pass the [release verification lifecycle](docs/RELEASE_CHECKS.md), including repeated renders, audio continuity, reload and actual MP4 downloads.

## Local development

Python 3.12+, Node.js 22+, FFmpeg with libass/libx264/AAC, and Noto Sans CJK fonts are required.

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
cp .env.example .env
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8018
# In a separate terminal:
.venv/bin/python -m backend.worker
```

Configure credentials locally in `.env`; never commit them. See [Google SSO](docs/GOOGLE_SSO.md), [PostgreSQL](docs/POSTGRESQL.md) and [Douyin search](docs/DOUYIN_SEARCH.md). For Vite development use `npm --prefix frontend run dev` and set `PUBLIC_ORIGIN` to the development origin.

`frontend/` contains the React application; `backend/` contains the API, worker, editing engine and tests; `onboarding-video/` contains tutorial production sources. Public tutorial videos and public-domain map geometry are included. User uploads, private configuration, dependency directories and build output are excluded.

Earlier rebuild notes are retained as historical documentation in [INITIAL_REBUILD_NOTES.md](docs/INITIAL_REBUILD_NOTES.md); they are not the current capability specification.
