# Media library V4 report

Date: 10 October 2026. Multilingual media library expansion on lumen-fix. OpenRouter / Gemini image / Veo were not used. ComfyUI was not started. `lumen-picture` (`h2v7b8z2szwlv6`) was left EXITED. No app rebuild. Published player `d3fbb40fe25a4bb2adf74a32635df28b` was not overwritten. strom-v2 was not touched.

## Counts

| | |
| --- | ---: |
| Starting approved rows (server) | 486 |
| Batch 1 approved | 75 |
| Batch 2 approved | 75 |
| Rejected this pass | 0 |
| New duplicates skipped | 0 |
| Final approved rows | 636 |
| RunPod SDXL stills total | 225 |
| Photographs (`visualFamily`) | 130 |
| Motion video (unchanged) | 17 |
| SVG (unchanged) | 341 |

Batch 1: `rp_photo_031–060`, `rp_detail_021–040`, `rp_object_016–030`, `rp_fg_011–020` (seeds 52000+).  
Batch 2: `rp_photo_061–090`, `rp_detail_041–060`, `rp_object_031–045`, `rp_fg_021–030` (seeds 53000+).

Files live under the existing library path:

`/opt/lumen-rebuild/media/library/out` → `/mnt/volume_nyc1_1791446889637/app-library`

RunPod masters staged then indexed via `media/library/runpod_assets.py` (anti-dupe by id / checksum). Contact sheets: `contact-sheets/v4/`.

## Provider / GPU

| Item | Value |
| --- | --- |
| Pod | `lumen-web-gpu` `wk5d9kjveiqn6l` (resume / stop only) |
| Model | SDXL base 1.0, Diffusers 0.32.2, `/workspace/lumen-media-v1` |
| Size | 768×1344 photos/details/fg; 1024×1024 objects |
| Steps / guidance | 30 / 6.0 |
| Peak VRAM | ~14880 MiB |
| Warm still | ~4.0 s |

I2V deferred: no lumen-owned video checkpoint under `/workspace/lumen-media-v1`. LTX on the volume belongs to another project and was not loaded. Wan not promised.

## Cost

| | USD |
| --- | ---: |
| Balance before first resume | ~58.14 |
| Balance after final stop | ~57.55 |
| Approximate session spend | **~$0.59** |
| Hard cap | 20.00 |

Idle spend returned to ~$0.015/hr after `podStop`. Pod status at end: `EXITED`. Jobs table was empty throughout generation.

## Multilingual search

`reports/MULTILINGUAL_MEDIA_COVERAGE.md`: 20 concepts × 3 languages = 60 queries. All returned hits; 0 decorative arrows as top hit; 19/20 share the same top id across locales. Gap concepts from the audit (citizenship, second passport, remote work, residency, investor meeting, couple, family home, city arrival) now resolve to RunPod stills with `conceptId`.

## Cross-generation picks (expanded library)

Seeds 839204 / 120011 / 103 with `recent_ids` memory:

| Seed | Document beat | Proof beat |
| --- | --- | --- |
| A 839204 | `rp_photo_066` | `document_approval_001` |
| B 120011 | `rp_photo_087` | `i2v_phone_001` |
| C 103 | `rp_photo_035` | `i2v_consult_001` |

Plans: `output/media-library-v4/variant-*.v4.json`. Prior 20 s mp4s remain; new plans pick V4 stills for the document beat. Published player untouched.

## Tests

- `media/library/search.test.py`: 12 passed (60-query set + RunPod row + passport concept match).
- `backend/tests/test_media_gpu.py` + `test_visual_variation.py`: 11 passed.

## Deployed to lumen-fix

- Indexed 150 stills into the live manifest (486 → 636).
- Synced `search.py`, `concepts.py`, `runpod_assets.py`, `search.test.py`, `media_gpu.py`, `visual_variation.py`.
- No `lumen-web` / `lumen-worker` restart (queue empty; code paths read library files from disk).
- Full “перенесём на диск” relocation deferred: assets already on the volume-backed library symlink; no second storage layout invented.

## Deferred

- I2V / motion expansion (no lumen-owned I2V weights).
- Optional second volume copy or macOS mirror of PNG masters (server library is authoritative).
- Remotion re-render of variant mp4s from the new `.v4.json` plans (plans ready; prior mp4s kept).
- Writing `conceptId` onto the pre-RunPod 411 rows (225 RunPod rows already have it).

## Git

Commit `619b01195470fcdbab8bc617d2fc8c8713eb31d5` on `fix/seedance-import-prologue` (pushed).
