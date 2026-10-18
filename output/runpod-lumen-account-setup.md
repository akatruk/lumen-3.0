# Lumen RunPod account setup

Date: 2026-10-12 (updated: wrong pod stopped, 4090 redeployed)

## Account
- Email: `andreykatruk@gmail.com`
- Purpose: Lumen Studio GPU (Hypit picture) only
- Not used: `a.ovsyannikov@hgpoint.com`

## Resources
| Resource | Id | Notes |
| --- | --- | --- |
| Network volume | `spsiypcy8y` (`lumen-gpu`, 80 GB, EU-RO-1) | mounts at `/workspace` |
| Pod (RUN this) | `nxi1rfwb94eufx` (`lumen-hypit-4090`) | RTX 4090, image `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`, volume attached |
| Pod (keep EXITED) | `hufsgfs9f7gpga` (`lumen-web-gpu`) | RTX PRO 4500 — do not start for Lumen Hypit |
| Former pod | `0pejenx239aha7` (`lumen-hypit-4090`) | terminated 2026-10-12 (host had no free GPU for resume) |

## Server config (`lumen-test`)
- `RUNPOD_API_KEY` → andreykatruk account
- `LUMEN_GPU_VOLUME=spsiypcy8y`
- `LUMEN_HYPIT_GPU=1`
- SSH key: `/opt/lumen-rebuild/data/gpu/id_ed25519`
- Hypit runtime on volume (`/workspace/lumen-runtime.tar` → extract to `/opt/hypit`)

## Ops
- Control script allows only `lumen-hypit-4090` (`scripts/runpod_pod_control.py`)
- `backend/hypit_gpu.py` `POD_NAME=lumen-hypit-4090`

## Verify
- `hypit_gpu._ensure_pod()` returns live SSH
- `test -x /opt/hypit/bin/hypit.mjs` on pod
