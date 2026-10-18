# Premium GPU selection (Media Factory V5)

**Date:** 2026-10-13  
**Mode:** READ-ONLY inspection — **no pod resume, no new pod, no resize**  
**Account:** andreykatruk (via lumen-test `/opt/lumen-rebuild/.env`)

## Live pod inventory

| Pod id | Name | desiredStatus | costPerHr (listed) | GPU |
| --- | --- | ---: | ---: | --- |
| `dznvwn90el5au4` | `lumen-hypit-4090` | **EXITED** | $0.72 | **RTX PRO 4500** |
| `hufsgfs9f7gpga` | `lumen-web-gpu` | **EXITED** | $0.72 | **RTX PRO 4500** |

| Metric | Value |
| --- | --- |
| Client balance | **~$7.90** |
| Idle spend/hr | **~$0.008** (storage/idle only) |
| nvidia-smi | Unavailable while EXITED (not started) |

## Options considered

| Option | VRAM (typical) | Secure ~$/hr | Fit for V5 batch | Notes |
| --- | ---: | ---: | --- | --- |
| **A. Resume existing RTX PRO 4500** (`dznvwn90el5au4`) | ~32 GB class (Blackwell PRO) | ~$0.72 | **Recommended when authorized** | Already in account; Hypit volume path; no new provision |
| B. Resume second EXITED 4500 (`hufsgfs9f7gpga`) | same | ~$0.72 | Avoid | Keep EXITED per ops; not Hypit primary |
| C. New RTX 4090 Secure | 24 GB | ~$0.69–0.89 | Only if 4500 insufficient | Creates spend + risk of orphan pods; forbidden without approval |
| D. A6000 / L40 / H100 | 48–80 GB | $1.5–4+ | Overkill for SDXL stills + short I2V | Balance too low |

Historical notes: older audits listed a true 4090 (`wk5d9kjveiqn6l` / prior `lumen-hypit-4090`). Current name `lumen-hypit-4090` is bound to **RTX PRO 4500** pod `dznvwn90el5au4` (see `reports/ORIGINAL1_HYPIT_PROMPT_MEDIA_FIX.md`).

## Workloads vs VRAM

| Workload | Peak VRAM (prior benches) | 4500 sufficient? |
| --- | ---: | --- |
| SDXL stills 768×1344 fp16 | ~15 GB | Yes |
| Short I2V (if lumen-owned weights present) | ~18–24 GB | Likely yes |
| FLUX-dev fp8 | ~12–20 GB | Yes if weights authorized |
| Local Blender EEVEE/Cycles CPU/GPU mac | N/A | Prefer Mac Blender for `l3d_v2_*` |

## Recommendation (ONE config)

**Reuse EXITED pod `dznvwn90el5au4` (`lumen-hypit-4090` / RTX PRO 4500 @ ~$0.72/hr).**  
Do **not** create a new pod. Do **not** start `hufsgfs9f7gpga`.  
Authorize explicitly before `scripts/runpod_pod_control.py resume`.

### Cost envelope (if approved)

| Slice | Estimate |
| --- | --- |
| Resume + SDXL re-download warm | ~$0.05–0.15 |
| First-batch stills/I2V (~23 assets, generative subset) | ~$1.50–4.00 |
| Hard stop | Balance &lt; $3 or spend &gt; $5 without new approval |

## Current V5 decision

**BLOCKED_ON_GPU_APPROVAL** for true generative video / RunPod SDXL.  
Ship contrast engine + Remotion/CSS/SVG cinematic plates + business motion from existing library without paid compute.

## Stop condition (this session)

Pods are EXITED → **STOP**. No auto-resume.
