# RunPod premium media V2

Date: 2026-10-11.

## Sync / library

| Check | Result |
| --- | --- |
| hypit-v5 prerequisite | 75 on DO (was already indexed) |
| V2 generated | **120** candidates on `lumen-hypit-4090` |
| V2 approved / rejected | **100 / 20** (quota: 40 photo / 25 detail / 20 object / 15 FG) |
| Manifest after index | **811** assets, **400** `source=runpod`, **100** `v2_*.png` on disk |
| Contact sheets | `contact-sheets/runpod-v2/v2-{photos,details,objects,foreground}.jpg` |

## Node

| Item | Value |
| --- | --- |
| Pod | `6zleobjm8h7zu9` / `lumen-hypit-4090` only |
| GPU | RTX 4090 24GB @ **$0.89/hr** |
| Status after work | **EXITED** (`podStop`) |
| A4000 | terminated earlier |

## Generation

| Item | Value |
| --- | --- |
| Model | SDXL Diffusers `sd_xl_base_1.0.safetensors` |
| Size / steps | 768×1344 / 32 / guidance 6.5 |
| Warm time | ~4.5 s/still |
| Bench | 3 OK (`output/v2-premium/bench/`) |
| Style lock | `media/library/STYLE_LOCK_V2.md` |
| Plans | `v2-premium-batch.jsonl` (120), `v2-premium-approved.jsonl` (100) |
| I2V | **Deferred** — no lumen video weights; ComfyUI not used |

## Cost

| Item | Approx |
| --- | --- |
| Balance before V2 session | ~$18.11 |
| Balance near stop | ~$17.9x (GPU was idle briefly after BATCH_DONE) |
| V2 GPU hours | well under **$20** production cap (~15–25 min active gen + SDXL re-download) |
| OpenRouter / Gemini / Veo | not used |

## Search note

RU/EN hypit/runpod hits previously OK. zh-CN query `海外移居` returned empty earlier (concept gap) — not a V2 blocker.

## PASS / FAIL vs V2 criteria

| # | Criterion | Status |
| --- | --- | --- |
| 1 | Reuse existing 4090 | **PASS** |
| 2 | No new GPU | **PASS** |
| 3 | Premium stills approved ≥ target mix | **PASS** (100) |
| 4 | Indexed + checksums on DO | **PASS** |
| 5 | Contact sheets | **PASS** |
| 6 | I2V 15 | **FAIL / deferred** |
| 7 | Stop when idle | **PASS** |
