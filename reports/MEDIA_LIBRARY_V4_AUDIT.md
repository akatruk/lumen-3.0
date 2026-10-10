# Media library V4 audit

Counted from the live lumen-fix library at `/opt/lumen-rebuild/media/library/out` → `/mnt/volume_nyc1_1791446889637/app-library` on 10 October 2026 after V4 Batch 2.

## Inventory (server, authoritative)

| | Count |
| --- | ---: |
| Approved manifest rows | 636 |
| RunPod SDXL stills (`source=runpod`) | 225 |
| Photographs (`static/runpod/photographs`) | 90 |
| Details | 60 |
| Objects | 45 |
| Foregrounds | 30 |

Id ranges: V1 `001–030` photos (+ matching families), V4 Batch 1 `031–060`, V4 Batch 2 `061–090`.

## Provider status

- OpenRouter image/video: HTTP 402. Do not use.
- RunPod `lumen-web-gpu` (`wk5d9kjveiqn6l`): resume-only. Confirmed `EXITED` after Batch 2 when jobs queue empty.
- ComfyUI / hgpoint: do not start or load.
- `lumen-picture` (`h2v7b8z2szwlv6`): leave EXITED / untouched.

## Coverage

Batch 1 + Batch 2 targeted citizenship, second passport, residency, approval, country comparison, remote work, couple/family relocation, city arrival, investor meeting, property investment/viewing, business relocation, document consultation, global mobility, key handover. Sixty multilingual concept search tests pass on the live manifest.

## Jobs / safety

Do not restart the worker while a job runs. Do not overwrite published player `d3fbb40fe25a4bb2adf74a32635df28b`. Project «е» is Director V3 Remotion, not Hypit. Index with `runpod_assets.apply` before any render stages a new still.
