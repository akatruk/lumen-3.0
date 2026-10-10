# Lumen Library Validation

Companion to `LUMEN_MEDIA_INTEGRATION_V5.md`. Date: 2026-10-11.

## Inventory

| Source | Count |
| --- | --- |
| Total manifest | 811 |
| runpod | 400 |
| vector | 341 |
| generated | 55 |
| remotion | 10 |
| MISSING source field | 5 (Remotion TSX scene refs — not binary plates) |

Runpod id prefixes in manifest: `rp_` 225, `hypit_` 75, `v2_` 100 (plus 67 vector ids that also start with `v2_` — not runpod files).

## File health

- Present: 806/811 (5 remotion `.tsx` paths expected absent as media)
- Runpod present: 400/400
- Zero-byte: 0 runpod; tiny files are vector SVGs (~323)
- Rejected dir: 5 files, none referenced by manifest
- Duplicate ids: 0
- Checksums: `sha256` not stored on runpod rows (generation metadata only); PNG integrity sample 30/30 OK; full runpod scan 400/400 PNG

## Search

54 multilingual intents → **54 hits** after V5 alias/casefold fix. Stale pre-fix snapshot was 46/54.

## Director utilization sample (3 seeds)

- Unique assets: 9, repeats: 0, cross-variant overlap: []
- Prefixes: rp_, v2_, re_
- editorial_object plates used (e.g. `rp_object_003`, `v2_detai_007`)

## Deliverables

- `output/library-validation/variant-{a,b,c}.mp4` (local + DO)
- `reports/LUMEN_MEDIA_INTEGRATION_V5.md`
- `reports/RUNPOD_MEDIA_RECOVERY.md`

**Verdict: PASS** for validation scope (no new media required).
