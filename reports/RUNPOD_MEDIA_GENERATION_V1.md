# RunPod media generation v1

Date: 2026-10-10. Still images only. No new pod. `lumen-picture` was not touched. OpenRouter, Gemini image, and Veo were not called.

## What was stopped

On `lumen-web-gpu` (`wk5d9kjveiqn6l`) the process `python3 main.py --listen 127.0.0.1 --port 8188` (pid 1376) was killed. That process was ComfyUI from another project. After the pod was resumed to copy files, port 8188 was still closed, no ComfyUI process was running, and the GPU was idle at 1 MiB. No speech or render process was killed. Nothing under `/workspace/ComfyUI` or `/workspace/comfyui` was edited, and those checkpoints were not loaded or copied out.

## Model

Lumen-owned Diffusers 0.32.2 on the pod, script `scripts/lumen_media_image.py`, weights at `/workspace/lumen-media-v1/models/sd_xl_base_1.0.safetensors` (6,938,078,334 bytes).

| Item | Value |
| --- | --- |
| Model | `stabilityai/stable-diffusion-xl-base-1.0` |
| Pipeline | `StableDiffusionXLPipeline.from_single_file` |
| GPU | NVIDIA GeForce RTX 4090, 24564 MiB |
| Size | 768×1344 |
| Steps | 30 |
| Guidance | 6.0 |
| dtype | float16 |
| Peak VRAM | 14898 MiB |
| Warm time | 3.87–4.39 s per still, median 4.0 s |
| Batch GPU time | 300 s for 75 stills |

The negative prompt is applied. It asks for no text, letters, numbers, logos, watermarks, passport imagery, signage, or malformed hands. FLUX.1-schnell is gated. The FLUX and LTX files already on the volume belong to the other project and were not used.

## Approved assets

75 stills approved, 0 rejected. 30 photographs, 20 details, 15 objects, 10 foregrounds. Seeds start at 51000. Contact sheets: `contact-sheets/runpod-images.jpg`, `runpod-details.jpg`, `runpod-objects.jpg`, `runpod-foreground.jpg`.

Reviewed on the contact sheets and on `rp_photo_001`, `rp_photo_012`, and `rp_photo_029`. Frames are photographic, with blank paper and no readable passport text. Family prompts sometimes draw four people when the wording asked for three. That was kept as a known limit, not a rejection.

No image-to-video clips were made. The only LTX checkpoint on the volume belongs to the other project. A public LTX-Video 2B file is about 6.3 GB and the lumen directory is 11 GB, so a later download can fit the remaining volume, but it was not started in this pass.

## Library

Copied into `/opt/lumen-rebuild/media/library/out` with `media/library/runpod_assets.py`. Existing rows were left in place. Manifest went from 411 assets to 486. Each new row has `source: runpod`, a sha256, and descriptions in English, Russian, and Chinese. Files live under `static/runpod/`.

Search on that manifest returns `rp_photo_001` for “family planning international relocation”, “семья планирует международный переезд”, and “家庭计划移居国外”.

## Queue and endpoint

`POST /internal/media/generate-image` stays authenticated. The `media_gpu_jobs` queue still yields when a production speech or render job is queued or running. The plan is an SDXL inference spec. It does not build a ComfyUI graph. The live lumen-fix process was not restarted.

## Cost

Account balance at the first resume this task was $59.99. After `podStop` it was $58.19, so about $1.80. While the pod was running the account reported $0.911 per hour. After the stop, spend fell to $0.015 per hour. Inference itself was about five minutes. The $20 cap was not reached. The lumen-fix job queue was empty (`JOBS []`). `podStop` left `wk5d9kjveiqn6l` as `EXITED`. It was not terminated. `lumen-picture` was not changed.

## Git

Code commit `a6f3c8e8c130b9698281251aac6ecbb81d52ee6e` on `fix/seedance-import-prologue`.
