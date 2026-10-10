# RunPod media generation v1

Date: 2026-10-10; library close-out 2026-10-11. Still images only for V1+V4. No new pod. `lumen-picture` was not touched. OpenRouter, Gemini image, and Veo were not called. ComfyUI was not started.

## Model

Lumen-owned Diffusers on pod `lumen-web-gpu` (`wk5d9kjveiqn6l`), script `scripts/lumen_media_image.py`, weights at `/workspace/lumen-media-v1/models/sd_xl_base_1.0.safetensors` (6,938,078,334 bytes).

| Item | Value |
| --- | --- |
| Model | `stabilityai/stable-diffusion-xl-base-1.0` |
| Pipeline | `StableDiffusionXLPipeline.from_single_file` |
| GPU | NVIDIA GeForce RTX 4090, 24564 MiB |
| Size | 768×1344 |
| Steps | 30 |
| Guidance | 6.0 |
| dtype | float16 |
| Peak VRAM | ~14898 MiB |
| Warm time | ~3.9–4.4 s per still (median ~4.0 s) |

## Approved assets

| Batch | Still count | Seeds | Breakdown |
| --- | ---: | --- | --- |
| V1 | 75 | from 51000 | 30 photo / 20 detail / 15 object / 10 foreground |
| V4 batch 1 | 75 | from 52000 | same mix |
| V4 batch 2 | 75 | from 53000 | same mix |
| **Total RunPod** | **225** | | **90 / 60 / 45 / 30** |

Approved 225, rejected 0. Files under `static/runpod/{photographs,details,objects,foreground}/`. Contact sheets:

- V1: `contact-sheets/runpod-images.jpg`, `runpod-details.jpg`, `runpod-objects.jpg`, `runpod-foreground.jpg`
- V4: `contact-sheets/v4/v4-photos.jpg`, `v4-details.jpg`, `v4-objects.jpg`, `v4-foreground.jpg`, plus `v4-batch2-*.jpg`

## Library (live lumen-fix)

Path: `/opt/lumen-rebuild/media/library/out` → `/mnt/volume_nyc1_1791446889637/app-library`.

| Item | Count |
| --- | ---: |
| Manifest assets | **636** |
| `source=runpod` | **225** |
| Prior baseline (pre–V1 stills) | 411 |
| After V1 only | 486 |
| After V4 (+150) | 636 |

Existing rows were left in place. No duplicate ids re-appended. Each RunPod row has `source: runpod`, sha256, and `description` en/ru/zh. Multilingual search via `media/library/search.py` + concepts: V4 coverage report 60/60.

## I2V

**Skipped.** No lumen-owned I2V / LTX weights under `/workspace/lumen-media-v1`. The LTX checkpoint on the shared volume belongs to another project and must not be loaded through ComfyUI. Prefer a future lumen-native 4s subtle motion path if weights are installed under `/workspace/lumen-media-v1` without starting ComfyUI. Pod was not resumed for I2V.

## Queue and endpoint

`POST /internal/media/generate-image` is authenticated (`current_user`). Plans are SDXL Diffusers specs (`image_plan` → `StableDiffusionXLPipeline` / `sd_xl_base_1.0.safetensors`). The `media_gpu_jobs` queue yields when production `jobs` are `queued`/`running`. `finish()` calls `index_generated_before_stage` before marking complete so Director cannot stage unindexed stills.

Deployed to lumen-test (`/opt/lumen-rebuild`) with `backend/media_gpu.py` and `app.include_router(media_gpu_router)`. Verified 2026-10-11 after `lumen-web` restart with empty production queue: health `ok`; unauthenticated `POST /internal/media/generate-image` returns **401** `unauthorized` (route present, auth required). `lumen-worker` was not restarted.

## Cost

| Phase | Notes |
| --- | --- |
| V1 first resume | balance ~$59.99 → ~$58.19 after stop (~$1.80) |
| V4 expansion session | ~$0.59 batch spend (user-confirmed); idle after stop ~$0.015/hr |
| Hourly while RUNNING | ~$0.89–$0.91 |
| Cap | $20 — not reached |
| Final pod | `wk5d9kjveiqn6l` **EXITED** (not terminated) |
| `lumen-picture` | untouched |

## Git

Branch `fix/seedance-import-prologue`:

- V1 stills + endpoint module: `a6f3c8e`
- V4 expansion: `619b011`
- V4 counts / spend notes: `129ed74` … `4fd5233`
- V1 report close-out (this file + GPU audit): `6e4be96`
