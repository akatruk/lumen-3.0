# RunPod premium GPU audit (V2)

Date: 2026-10-11. Hypit account only. Single media node after cleanup.

## Target instance

| Item | Value |
| --- | --- |
| Pod id | `6zleobjm8h7zu9` |
| Name | `lumen-hypit-4090` |
| GPU | NVIDIA GeForce RTX 4090, **24564 MiB** (`nvidia-smi` 2026-10-10 session) |
| Driver (live) | 595.91.07 |
| PyTorch (live) | 2.4.1+cu124 (+ matching `torchvision==0.19.1`) |
| Image | `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04` |
| Container disk | 60 GB overlay — **ephemeral, wiped on stop** |
| Network volume | none |
| Hourly | **$0.89/hr** Secure Cloud |
| Account | only this pod (A4000 `mxzxfgdtxvia7f` **terminated**) |

## Balance snapshot

| When | Balance | Spend/hr | State |
| --- | ---: | ---: | --- |
| Post single-node cleanup | ~$18.11 | 0 | EXITED |
| V1 hypit-v5 batch | spent ≈ $0.24 from ~$18.36 | — | 75 stills done |

## Proven image path

- Checkpoint: `sd_xl_base_1.0.safetensors` (6,938,078,334 B) via Diffusers `StableDiffusionXLPipeline.from_single_file`
- Size 768×1344, steps 30–32, guidance ~6–6.5, fp16
- Warm still ≈ **4.3–5.3 s**; peak VRAM ≈ **15 GB**
- FLUX / Wan / LTX: not on this disk; ComfyUI not used

## Constraints

- Never create a second pod; resume `6zleobjm8h7zu9` only
- Re-download SDXL after each stop (ephemeral disk)
- I2V deferred without lumen-owned video weights
- Budgets: ≤$5 bench, ≤$20 production batch
