# Lumen 3D Quality Recovery V2

**Date:** 2026-10-13  
**Git SHA:** _(stamped on commit)_  
**Host GPU:** local Blender 5.2.2 LTS (RunPod **not** resumed)  
**DO volume:** `/mnt/volume_nyc1_1791446889637` — 78 GB free  

## Principle

Premium 3D is not a checkbox. Three excellent objects beat thirty mediocre ones. V9 quality is mandatory.

## Audited assets

V1 library (15 variants): all **REJECTED** for premium production (primitive + opaque WebM).  
See `reports/3D_ASSET_AUDIT.md`.

## Root causes

| Cause | Status after V2 |
|-------|-----------------|
| Primitive geometry | Improved, still NEEDS_REWORK |
| Flat materials | Noise/bump added, still short of commercial |
| Opaque WebM alpha | **Fixed** (PNG + ProRes 4444) |
| Tiny Remotion scale | **Fixed** (profiles + face-safe clamp) |
| Director force-bind | **Fixed** (`production_ready` gate) |
| Ground in alpha | **Fixed** |

## Models / animations produced

Under `3d-library-v2/`:

- `l3d_v2_passport` — passport_open (+ factory supports reveal / second_passport_reveal)
- `l3d_v2_suitcase` — suitcase_roll (+ arrival / foreground_pass in factory)
- `l3d_v2_folder` — folder_open (+ reveal / documents_stack in factory)

Hero showcase: `output/3d-quality-recovery/{passport_open,suitcase_roll,folder_open,3d-showcase}.mp4`

## Quality status

| Status | Items |
|--------|-------|
| PREMIUM_READY / production_ready | **none** |
| NEEDS_REWORK | all `l3d_v2_*` hero variants |
| REJECTED | entire V1 set + globe |
| EXPERIMENTAL | apartment building (hold) |

## A/B

Trial with 3D bound (`v102-trial-3d.mp4`) vs V9: V9 wins on cleanliness; V2 3D is recognizable with real alpha but still CG/toy. Gate closed.

## 60s preview

`output/3d-quality-recovery/director-v10-2-e-preview-60s.mp4` — V9 editorial, `boundCount=0`, `shotPlanVersion=v10.2`.

## Code

- `media/library/3d_factory/blender_factory_v2.py`
- `media/library/3d_factory/build_batch_v2.py`
- `media/library/3d_factory/catalog_v2.json`
- `media/library/3d_factory/quality_gate_v2.json`
- `backend/director_v10_2.py` (default via `PREMIUM_3D_MODE=v10.2`)

## Deployment

Code synced to `142.93.248.163:/opt/lumen-rebuild`. RunPod untouched. V9 fallback intact.

## Remaining limitations

1. Procedural geometry still reads as product-viz pilot, not commercial motion design.
2. Remaining V2 motions (reveal/stack/arrival/pass) not all batch-rendered this pass.
3. No cutaway_hero Remotion layout yet (needed before large hero floats).
4. Large ProRes/PNG masters not committed to Git (local + DO volume only).
