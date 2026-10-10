# RunPod Media Recovery

Date: 2026-10-11. Folded into Media Integration V5.

## Hard rules observed

- Did **not** restart / resume pod `6zleobjm8h7zu9`
- Did **not** create GPUs or paid generation
- Did **not** SSH-retry EXITED pod (SSH 255 expected)
- Did **not** migrate the media library off the volume

## Hypothesis A

| Claim | Evidence | Result |
| --- | --- | --- |
| ~400 runpod assets are already inside the 811-asset library on DO | Manifest `source=runpod` = 400; disk files under `static/runpod` = 400; basename sets equal | **PROVEN** |

Local laptop `media/library/out/manifest.json` may be stale (~636 / 225). **Authoritative copy is the DO volume.**

## Local tars vs DO

| Archive | Local files | Gap vs DO |
| --- | --- | --- |
| `output/hypit-v5/hypit-v5-batch.tar` | ~150 hypit_ | Already indexed on DO (75 approved in library) |
| `output/v2-premium/v2-premium-batch.tar` | 240 v2_ candidates | 100 approved on DO; extras are candidates/rejects — not missing from pod |

No safe recovery copy needed for the 400 indexed runpod stills — they are on `/mnt/volume_nyc1_1791446889637/app-library`.

## Only-on-pod options (not executed)

If something existed solely on EXITED `lumen-hypit-4090`:

| Option | Cost / risk |
| --- | --- |
| Resume pod + rsync | ~$0.89/hr RTX 4090; violates “do not resume” for this task |
| New GPU pod | Paid; forbidden here |
| Accept DO library as source of truth | **Chosen** |

## Verdict

**PASS** — recovery not required; inventory complete; continue via V5 integration on web-node media only.
