# RunPod GPU audit

Date: 2026-10-10. Pod `lumen-web-gpu` (`wk5d9kjveiqn6l`) was already in the account and was resumed. No new pod was created. `lumen-picture` (`h2v7b8z2szwlv6`) was left exited.

## Machine

| Item | Value |
| --- | --- |
| GPU | NVIDIA GeForce RTX 4090 |
| VRAM | 24564 MiB (PyTorch reports 23.52 GB usable, ComfyUI reports 24081 MB) |
| Driver | 580.95.05 |
| nvidia-smi CUDA | 13.0 |
| PyTorch | 2.8.0+cu128, CUDA 12.8 available |
| Python | 3.12.3 |
| CPU | 32 |
| RAM | 124 GiB, about 116 GiB available at audit, no swap |
| Image | `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` |
| Container disk | overlay 40 GB. It is wiped when the pod stops. |
| Network volume | `genai-models` (`xv77ctuc80`), 150 GB, mounted at `/workspace` |
| Datacenter | EU-RO-1 |
| Hourly price | $0.89 while this pod is running |
| Account balance at resume | $59.99 |

`df` on `/workspace` shows the MooseFS cluster, not the 150 GB quota. `du /workspace` was about 120 GB before this task, so about 30 GB was free. A 23 GB FLUX schnell download was not started.

## What was already on the GPU

At audit the GPU was idle: 1 MiB used, 0% utilization, no GPU processes. The lumen-fix job queue was empty.

Left in place on the volume:

- `/workspace/lumen-speech` (Qwen3-TTS)
- ComfyUI at `/workspace/ComfyUI`, models at `/workspace/comfyui/models`
- `flux1-dev-fp8.safetensors` (17 GB) and `flux1-dev-fp8-e4m3fn.safetensors` (12 GB)
- `clip_l.safetensors`, `t5xxl_fp8_e4m3fn.safetensors`, `ae.safetensors`
- `ltxv-2b-0.9.8-distilled-fp8.safetensors` (4.4 GB), left unused
- existing LoRAs, SD1.5 checkpoints, and background-removal weights

## Process that was stopped

A local server on `127.0.0.1:8188` had been started from `/workspace/ComfyUI` during an earlier attempt. That process (pid 1376, `python3 main.py --listen 127.0.0.1 --port 8188 --disable-auto-launch --disable-all-custom-nodes`) was stopped. After a later `podResume` of the same pod, the port was still closed, no ComfyUI process was running, and GPU memory was 1 MiB. Nothing under `/workspace/ComfyUI` or `/workspace/comfyui` was changed, and those checkpoints were not loaded or copied.

## Model choice

Image generation is a lumen-owned Diffusers script, `scripts/lumen_media_image.py`, with weights stored under `/workspace/lumen-media-v1/models`. The checkpoint is `stabilityai/stable-diffusion-xl-base-1.0` (`sd_xl_base_1.0.safetensors`, about 6.9 GB). It is publicly downloadable and fits the free space on the 150 GB volume and the 24 GB card. FLUX.1-schnell is gated. The FLUX and LTX files already on the volume belong to another project and are not loaded.

SDXL applies a negative prompt. Portrait output is 768×1344, 30 steps, guidance 6.0, float16. The checkpoint on the volume is 6,938,078,334 bytes. The lumen directory `/workspace/lumen-media-v1` is 11 GB. See `reports/RUNPOD_MEDIA_GENERATION_V1.md` for the batch, the library sync, and the cost.
