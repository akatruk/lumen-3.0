# Media library V4 report

Date: 2026-10-10. Multilingual media library expansion V4 on lumen-fix. OpenRouter / Gemini image / Veo were not used. ComfyUI was not started. `lumen-picture` (`h2v7b8z2szwlv6`) was left EXITED. Published player `d3fbb40fe25a4bb2adf74a32635df28b` was not overwritten.

## Cost safety (this follow-up)

Jobs queue empty (`queued`/`running`/`processing` = 0). `podStop` on `lumen-web-gpu` (`wk5d9kjveiqn6l`) only → `desiredStatus: EXITED`. Not terminated. No `_start_pod`. After final stop: `currentSpendPerHr` 0.015, `clientBalance` ≈ 57.55.

## Counts (server, authoritative)

| | |
| --- | ---: |
| Manifest rows | 636 |
| RunPod SDXL stills (`source=runpod`) | 225 |
| Photographs under `static/runpod/photographs` | 90 |
| Details | 60 |
| Objects | 45 |
| Foregrounds | 30 |
| Rejected this pass | 0 |
| New duplicates skipped | 0 |

Path: `/opt/lumen-rebuild/media/library/out` → `/mnt/volume_nyc1_1791446889637/app-library`.

| Batch | Seeds | Ids | Stills | Status |
| --- | ---: | --- | ---: | --- |
| V1 | 51000+ | photo 001–030 (+ matching detail/object/fg) | 75 | prior |
| V4 Batch 1 | 52000+ | photo 031–060, detail 021–040, object 016–030, fg 011–020 | 75 | already indexed; not re-appended |
| V4 Batch 2 | 53000+ | photo 061–090, detail 041–060, object 031–045, fg 021–030 | 75 | generated + indexed |

## Provider / GPU

| Item | Value |
| --- | --- |
| Pod | `lumen-web-gpu` `wk5d9kjveiqn6l` (resume / stop only) |
| Model | SDXL base 1.0, Diffusers, `/workspace/lumen-media-v1` |
| Size | 768×1344 photos/details/fg; 1024×1024 objects |
| Steps / guidance | 30 / 6.0 |
| Warm still | ~4.0 s |

I2V deferred: no lumen-owned video checkpoint under `/workspace/lumen-media-v1`.

## Cost

| | USD |
| --- | ---: |
| Balance after final stop | ~57.55 |
| Approximate V4 session spend (batches) | ~$0.59–$1.80 range across resumes |
| Hard cap | 20.00 |

Idle spend returned to ~$0.015/hr after `podStop`.

## Contact sheets v4

`contact-sheets/v4/` on the server:

- Batch 1: `v4-photos.jpg`, `v4-details.jpg`, `v4-objects.jpg`, `v4-foreground.jpg`
- Batch 2: `v4-batch2-photos.jpg`, `v4-batch2-details.jpg`, `v4-batch2-objects.jpg`, `v4-batch2-foreground.jpg`

## Tests

`media/library/search.test.py`: 12 tests OK on the live server manifest, including the 60-query set (20 concepts × en/ru/zh).

## Deploy

Synced batch planners, `runpod_pod_control.py`, `lumen_media_image.py`, `runpod_assets.py`, and `media_gpu.py` to `/opt/lumen-rebuild`. Worker not restarted (queue empty).

## Git

- Planners / indexer / pod control: `619b011`
- Docs follow-up (counts + pod stop): `1a0c77daf56638c67c845f3a6e4077586dc3e153`
