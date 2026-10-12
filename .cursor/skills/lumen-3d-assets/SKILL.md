---
name: lumen-3d-assets
description: >-
  Lumen Premium 3D Asset Factory + V10.1 quality gate: Blender procedural
  objects, RGBA PNG alpha masters, optional Remotion floats. 3D is optional;
  V9 clean composition is the rollback baseline.
---

# Lumen 3D assets

## Rules

- **3D is optional. Professional quality is mandatory.**
- Do not expand the library until existing objects pass production_ready.
- Do not resume RunPod without explicit authorization.
- No baked language text / logos / passport numbers in geometry.
- True alpha master = `3d-library/alpha_png/**/frame_*.png` (RGBA).
- Do **not** trust WebM as alpha until `ffprobe` reports `yuva420p` (macOS
  libvpx often silently emits opaque `yuv420p`).

## Quality gate (V10.1)

- Gate file: `media/library/3d_factory/quality_gate_v101.json`
- Director: `backend/director_v10_1.py` (default via `director_v10.apply_premium_3d`)
- Env: `PREMIUM_3D_MODE=v10.1` (default) | `off` | `v10_legacy`
- Statuses: `production_ready` | `approved_trial` | `experimental` | `rejected`
- Remotion: `FloatingForeground` supports `format: png_seq` + scale profiles
  `hero | supporting | foreground | background`

## Paths

- Factory: `media/library/3d_factory/`
- Output: `3d-library/` (models, blender, alpha_png, alpha, previews, registry)
- Reports: `output/director-v10-1/`, `reports/LUMEN_3D_*`

## Commands

```bash
blender -b --python media/library/3d_factory/blender_factory.py -- \
  --asset l3d_generic_passport --motion open --out 3d-library
.venv/bin/python media/library/3d_factory/build_batch.py --out 3d-library
PREMIUM_3D_MODE=v10.1 .venv/bin/python scripts/ordinary_director_render.py \
  --source data/<project>/source --project-id <id> --language ru-RU \
  --duration 60 --seed 42 --out output/director-v10-1/director-v10-1-e-preview-60s.mp4
```
