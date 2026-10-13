# Multilingual media contract

**Date:** 2026-10-14

| | |
| --- | --- |
| ADR | `docs/architecture/adr/ADR-010-universal-multilingual-media-contract.md` |
| Skill | `.cursor/skills/lumen-media-library/SKILL.md` |
| Command | `python3 scripts/validate_media_library.py --multilingual` |
| CI | `python3 media/library/test_media_contract.py -q` plus `scripts/validate_media_library.py --multilingual`. GitHub Actions file was not pushed: the OAuth token has no `workflow` scope. |

## Validator (local manifest + overlay)

| | |
| --- | ---: |
| Assets | 692 |
| Duplicate ids | 0 |
| Strict failures (`production_ready` / `multilingualContract=required`) | 0 |
| Legacy locale gaps (missing concept or a locale title/description after overlay) | **171** |
| Exit | 0 |

New rows go through `media/library/ingest.register_approved`. Incomplete copy stays `PENDING_LOCALIZATION` and is not written to the overlay. Existing human `tags_ru` / `tags_zh` are not replaced.

## Tests

`python3 media/library/test_media_contract.py` — 7 passed: legacy allowed, pending on empty copy, single-id publish, rejected≠production, unapproved 3D blocked, EN/RU/ZH fixture returns `business_meeting_042`.

No new Precision@5. Hybrid stays off.

## Backfill

Idempotent: `scripts/backfill_multilingual_metadata.py`. Remaining 171 need glossary terms or a human description. Do not invent visible content.

## Deploy

Code only to `142.93.248.163:/opt/lumen-rebuild`. Manifest binaries not rewritten. RunPod and strom-v2 untouched. No web restart required for a validator that is not on the request path; search/ingest files are synced.

## Git

SHA recorded on the commit that adds this report.
