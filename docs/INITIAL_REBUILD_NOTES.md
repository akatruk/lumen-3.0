# Lumen Studio — rebuild

A new, independently deployed implementation of Lumen's video intelligence and editing workflow. Source repositories were examined read-only; no old VM services were changed.

Production: https://lumen-fix.universalgravity.org/ — new VM `142.93.248.163`.

## What is implemented

- Private accounts, invitation-only registration, password hashing, expiring HttpOnly sessions, per-account project/media authorization and CSRF origin checks.
- English and Simplified Chinese UI and AI response schemas. A saved language preference and persistent project URLs.
- Streaming video uploads (250 MB, 180 seconds), immutable source, source proxy, poster and durable SQLite job queue.
- Full video + audio understanding via a configurable Gemini model on OpenRouter. Structured scenes, bilingual transcript, grounded recommendations, editorial scores and explicit uncertainties.
- Expandable recommendations linked to source timestamps. Select only the changes you want; automatic first cut selects high-confidence edits and permits automatic removals only inside measured silence without transcript overlap.
- Real FFmpeg assembly: cuts, source hook reordering without duplication, timestamp-remapped EN/ZH ASS captions, aspect-ratio fitting without cropping original subjects, two-pass audio normalization, optional generated footage overlays.
- Optional first-frame-guided video generation through OpenRouter's asynchronous video API. At most two four-second clips, explicit per-project opt-in, persisted provider job IDs, no automatic duplicate paid submissions after uncertain responses.
- File integrity / duration / audio checks plus an independent AI comparison of original and output. A failed or unavailable AI review is visibly marked for human review.
- Per-project and rolling daily spending reservations; actual provider costs reconcile when available. Ambiguous charges stay reserved. Deleting media does not reset daily spend.
- Versioned render files: a failed new render does not overwrite the last successful result.
- A separate constrained systemd worker, nginx HTTPS, automatic certificate renewal.

## Current verification limits

The connected account initially returned HTTP 402; a subsequent real request succeeded. A 28-second synthetic narrated clip completed real analysis, automatic editing and AI review for approximately $0.035 (before optional generated footage). The review correctly flagged defects instead of marking the output approved. An orphaned subtitle card found by that test was fixed and covered by a regression test. A second live pass generated and composited one four-second clip (three seconds used), retaining original audio. Total test-project spend across both passes was $0.3693005. The generated result remained marked for review because of visual continuity issues. Representative customer-video quality remains unvalidated; a synthetic clip is not a creative-quality benchmark.

This release implements the video studio first. The older influencer marketplace, Douyin discovery, CRM, outreach, OAuth account connections, publishing, and sales automation are not reimplemented here. See `docs/REBUILD_SCOPE.md` for the full Lumen product context and remaining work. Chinese language support is not a claim that mainland-China connectivity or Douyin access has been validated.

Storage is local and private for the initial single-node deployment. It is bounded by `MAX_STORAGE_GB`. Object storage, off-site backups, multi-worker coordination, resumable direct uploads, and organization/team permissions are subsequent infrastructure work. Do not scale the current worker to multiple machines against SQLite.

## Local development

Python 3.12+; Node 22+; FFmpeg built with libass, libx264 and AAC; Noto Sans CJK fonts.

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
cp .env.example .env
# Set an invitation code and AI key in .env.
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8019
# Separate terminal:
.venv/bin/python -m backend.worker
```

For Vite development run `npm --prefix frontend run dev`; its proxy targets port 8018. Set `PUBLIC_ORIGIN=http://127.0.0.1:5178` and run the API on 8018.

## Validation

```sh
python -m pytest backend/tests -q
npm --prefix frontend run build
```

`test_render.py` synthesizes red/green/blue scenes and an audio tone, performs real cuts, reorders blue into the opening, burns Chinese captions and verifies pixels at specific output times. It requires an FFmpeg with the ASS filter. The Homebrew FFmpeg available on this Mac lacks it; the complete suite runs on the new Ubuntu VM.

`backend/tests/seed_ui_fixture.py` is explicitly local-only, requires temporary test render artifacts, and seeds the local QA account with a clearly labeled synthetic fixture. Production has no seeded content or demo results.

## Operations

Application source: `/opt/lumen-rebuild`.
Secrets: `/opt/lumen-rebuild/.env`, root:lumen 0640.
Data: `/opt/lumen-rebuild/data`, lumen:lumen 0700.

```sh
systemctl status lumen-web lumen-worker
journalctl -u lumen-web -u lumen-worker --since '10 minutes ago'
curl https://lumen-fix.universalgravity.org/api/health
```

Service definitions and first-install instructions are in `deploy/`. The application runs as an unprivileged user. Public requests go through nginx; Python listens only on localhost. Avoid restarting the worker while jobs are running. Interrupted jobs fail visibly rather than blindly replaying paid model calls.

The private `access.txt` file is ignored by Git and contains the invitation code for the owner to create an account. It is not shipped to the server or web bundle.
