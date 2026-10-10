# RunPod media generation v1

Date: 2026-10-10; library close-out 2026-10-11. Still images only for V1+V4. No new pod. `lumen-picture` was not touched. OpenRouter, Gemini image, and Veo were not called. ComfyUI was not started.

## Close-out audit (2026-10-11)

Live re-check on `lumen-fix` (`142.93.248.163`) and a short `podResume` of `wk5d9kjveiqn6l` only for I2V proof, then `podStop`.

| Check | Result |
| --- | --- |
| Manifest assets | **636** |
| `source=runpod` | **225** (all `type=image`) |
| Jobs queue `queued`/`running` | **0** (status counts: failed 126, complete 121) |
| `media_gpu_jobs` | empty |
| `POST /internal/media/generate-image` | **401** `unauthorized` on `:8018` |
| Health | `{"status":"ok","version":"0.1.0"}` |
| Multilingual search | `media/library/search.test.py` **12/12 OK** on live manifest |
| Contact sheets (stills) | `runpod-images/details/objects/foreground.jpg` + `contact-sheets/v4/*` present |
| Contact sheet (motion) | **N/A** — no RunPod I2V clips; no `runpod-motion.jpg` |
| New media this close-out | **0** (no re-append, no duplicate ids) |
| Pod after stop | `wk5d9kjveiqn6l` **EXITED**; `lumen-picture` **EXITED** untouched |

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
- Motion: deferred with I2V (no RunPod motion assets to sheet)

## Library (live lumen-fix)

Path: `/opt/lumen-rebuild/media/library/out` → `/mnt/volume_nyc1_1791446889637/app-library`.

| Item | Count |
| --- | ---: |
| Manifest assets | **636** |
| `source=runpod` | **225** |
| Prior baseline (pre–V1 stills) | 411 |
| After V1 only | 486 |
| After V4 (+150) | 636 |

Existing rows were left in place. No duplicate ids re-appended. Each RunPod row has `source: runpod`, sha256, and `description` en/ru/zh. Multilingual search via `media/library/search.py` + concepts: V4 coverage report 60/60; close-out unit tests 12/12.

## I2V

**Deferred (re-proved 2026-10-11).** Resume of `wk5d9kjveiqn6l` showed `/workspace/lumen-media-v1/models/` contains only `sd_xl_base_1.0.safetensors`. No lumen-owned SVD / LTX / I2V checkpoint. Diffusers pipeline *code* exists under the venv (`py/diffusers/pipelines/{ltx,stable_video_diffusion,i2vgen_xl}/`) but that is not weights. Foreign LTX at `/workspace/comfyui/models/checkpoints/ltxv-2b-0.9.8-distilled-fp8.safetensors` (4.2G) was left untouched; ComfyUI was not started (port 8188 closed, no process). Installing and debugging a new video checkpoint for ~10 clips was skipped to stay inside the $20 GPU cap and ownership rules. Prefer a future lumen-native 4s subtle motion path if weights are installed under `/workspace/lumen-media-v1` without starting ComfyUI.

## Queue and endpoint

`POST /internal/media/generate-image` is authenticated (`current_user`). Plans are SDXL Diffusers specs (`image_plan` → `StableDiffusionXLPipeline` / `sd_xl_base_1.0.safetensors`). The `media_gpu_jobs` queue yields when production `jobs` are `queued`/`running`. `finish()` calls `index_generated_before_stage` before marking complete so Director cannot stage unindexed stills.

Deployed to lumen-test (`/opt/lumen-rebuild`) with `backend/media_gpu.py` and `app.include_router(media_gpu_router)`. Verified 2026-10-11: health `ok`; unauthenticated `POST /internal/media/generate-image` returns **401** `unauthorized` (route present, auth required). `lumen-worker` was not restarted (queue empty).

## Cost

| Phase | Notes |
| --- | --- |
| V1 first resume | balance ~$59.99 → ~$58.19 after stop (~$1.80) |
| V4 expansion session | ~$0.59 batch spend (user-confirmed); idle after stop ~$0.015/hr |
| Close-out I2V proof resume | balance ~$57.479 → ~$57.453 after stop (~**$0.026**); peak spend ~$0.911/hr while RUNNING |
| Hourly while RUNNING | ~$0.89–$0.91 |
| Cap | $20 — not reached |
| Final pod | `wk5d9kjveiqn6l` **EXITED** (not terminated) |
| `lumen-picture` | untouched (**EXITED**) |

## Git

Branch `fix/seedance-import-prologue`:

- V1 stills + endpoint module: `a6f3c8e`
- V4 expansion: `619b011`
- V4 counts / spend notes: `129ed74` … `4fd5233`
- V1 report close-out: `6e4be96` / tip pin `0999751`
- This audit close-out: see tip after push
