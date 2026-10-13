# ADR-010: Universal multilingual media contract

Status: Accepted (2026-10-14)

Extends ADR-004 (one library), ADR-001 (Remotion owns type), ADR-002 (no baked text), ADR-005 (target audio timing), ADR-008 (quarantine).

## Decision

RU (`ru-RU`), EN (`en-US`), and ZH (`zh-CN`) are a publication gate for **new** assets. Legacy rows stay readable. There is still one manifest and one canonical `id`.

## Invariants

1. One canonical `id` per visual. Do not translate filenames.
2. One library. No `*_ru` / `*_en` / `*_zh` copies of the same picture.
3. A new production asset must be findable from RU, EN, and ZH queries via `localized` plus `tags` / `tags_ru` / `tags_zh`.
4. Generic visuals stay language-neutral.
5. No captions, logos, or readable documents inside generated pixels.
6. Viewer-facing type is Remotion.
7. Motion components take localized strings; they do not bake labels.
8. Director passes `project.language` into `search_assets(..., locale=)`.
9. Timing follows target-language audio (ADR-005).
10. `quarantined` / `rejected` / `duplicate` / `corrupt` stay out of default search.
11. `premium_3d` is not `production_ready` without an explicit quality-gate approval.
12. Ingest runs `validate_media_library --multilingual` before publication. Failure sets `qualityStatus=PENDING_LOCALIZATION`.
13. Future cinematic batches use the same ingest: frame-grounded metadata separate from the prompt, `en-US` / `ru-RU` / `zh-CN`, and index only after approval. Incomplete rows stay `PENDING_LOCALIZATION`.

## Schema

Keep the manifest fields. Do not add a second document format.

| Contract name | Manifest field |
| --- | --- |
| assetId | `id` |
| conceptId | `conceptId` |
| type | `type` |
| domain | `domain` |
| qualityStatus | `qualityStatus` or `status` |
| storage | `file` |
| supportedLocales | `supportedLocales` (default the three locales when `localized` is complete) |
| localized copy | `localized["en-US"|"ru-RU"|"zh-CN"].title` and `.description` |

## Consequences

- New agents must call `media/library/ingest.register_approved` or the validator. Glossary fill is not a silent repair of empty human copy: `ensure_locales` only fills from existing English tags and never overwrites `tags_ru` / `tags_zh`.
- CI runs fixture tests only. It does not download weights or the volume.
- `VISUAL_INTELLIGENCE_ENABLED` stays 0 until a labeled zh-CN eval recovers. Keyword search plus phrase expansion remains the default.

## Tradeoffs

- Legacy rows (no `multilingualContract`) are reported, not failed. Strict mode would hide most of the current library.
- Query expansion to English tags (ADR-004) is allowed. Viewer-facing card copy must not fall back to English when the project locale is RU or ZH.

## Exceptions

- Quarantine and rejected rows are excluded, not localized as a condition of exclusion.
- Experimental 3D stays `needs_review` until the quality gate lists it.
- Motion `.tsx` components are not binary assets. Locale coverage is props, not a video file per language.

## Enforcement

`python3 scripts/validate_media_library.py --multilingual`

Exit 0 when only legacy gaps remain. Exit 1 when any row with `multilingualContract=required` or `qualityStatus=production_ready` fails. New ingest uses that strict check.
