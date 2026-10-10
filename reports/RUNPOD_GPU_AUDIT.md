# RunPod GPU audit

Date: 2026-10-10 (updated 2026-10-11 after V4 stills). Pod `lumen-web-gpu` (`wk5d9kjveiqn6l`) was already in the account and was resumed only for generation. No new pod was created. `lumen-picture` (`h2v7b8z2szwlv6`) was left EXITED / untouched.

## Machine

| Item | Value |
| --- | --- |
| GPU | NVIDIA GeForce RTX 4090 |
| VRAM | 24564 MiB (PyTorch reports 23.52 GB usable) |
| Driver | 580.95.05 |
| nvidia-smi CUDA | 13.0 |
| PyTorch | 2.8.0+cu128, CUDA 12.8 available |
| Python | 3.12.3 |
| CPU | 32 |
| RAM | 124 GiB |
| Image | `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` |
| Container disk | overlay 40 GB (wiped when the pod stops) |
| Network volume | `genai-models` (`xv77ctuc80`), 150 GB, mounted at `/workspace` |
| Datacenter | EU-RO-1 |
| Hourly price | ~$0.89–$0.91 while running; ~$0.015/hr when EXITED |

`df` on `/workspace` shows the MooseFS cluster, not the 150 GB quota. Before V1 work, `du /workspace` was about 120 GB (~30 GB free). A gated FLUX schnell download was not started.

## What was already on the GPU volume

Left in place and **not** used by Lumen:

- `/workspace/lumen-speech` (Qwen3-TTS)
- ComfyUI at `/workspace/ComfyUI`, models at `/workspace/comfyui/models` (hgpoint project — do not start)
- `flux1-dev-fp8.safetensors` (17 GB) and `flux1-dev-fp8-e4m3fn.safetensors` (12 GB)
- `clip_l.safetensors`, `t5xxl_fp8_e4m3fn.safetensors`, `ae.safetensors`
- `ltxv-2b-0.9.8-distilled-fp8.safetensors` (4.4 GB) — other project; not loaded
- existing LoRAs, SD1.5 checkpoints, background-removal weights

## Process that was stopped (V1)

A local ComfyUI server on `127.0.0.1:8188` from `/workspace/ComfyUI` was stopped during the first V1 pass. Later resumes left port 8188 closed, no ComfyUI process, GPU idle. Nothing under `/workspace/ComfyUI` or `/workspace/comfyui` was edited.

## Model choice (Lumen-owned)

Image generation uses Diffusers under `/workspace/lumen-media-v1`, script `scripts/lumen_media_image.py`:

| Item | Value |
| --- | --- |
| Model | `stabilityai/stable-diffusion-xl-base-1.0` |
| Checkpoint | `sd_xl_base_1.0.safetensors` (6,938,078,334 bytes) |
| Pipeline | `StableDiffusionXLPipeline.from_single_file` |
| Size | 768×1344 |
| Steps | 30 |
| Guidance | 6.0 |
| dtype | float16 |
| Peak VRAM (bench) | ~14898 MiB |
| Warm still | ~3.9–4.4 s |

Negative prompt applied (no text/letters/logos/passport imagery/malformed hands). FLUX and LTX on the volume belong to another project and are not loaded.

## I2V

Deferred. No lumen-owned video checkpoint under `/workspace/lumen-media-v1`. The LTX file under the ComfyUI tree must not be used via ComfyUI. Pod was left EXITED; no resume for I2V in this close-out.

## Current pod status

`wk5d9kjveiqn6l` (`lumen-web-gpu`): **EXITED** after V4 Batch 2 when the lumen-fix jobs queue was empty. Not terminated. See `reports/RUNPOD_MEDIA_GENERATION_V1.md` for library counts and cost.
