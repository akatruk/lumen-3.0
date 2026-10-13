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
- Do not expand the library until passport / suitcase / folder are PREMIUM_READY.
- Do not resume RunPod without explicit authorization.
- No baked language text / logos / passport numbers in geometry.
- True alpha master = RGBA PNG sequence and/or ProRes 4444 (`yuva*`).
- Never trust WebM alpha until `ffprobe` reports `yuva420p`.

## Versions

| Ver | Path | Gate |
|-----|------|------|
| V1 | `3d-library/` | REJECTED |
| V2 | `3d-library-v2/` | `quality_gate_v2.json` — `production_ready: []` |
| Director | `backend/director_v10_2.py` | default `PREMIUM_3D_MODE=v10.2` |

## Commands

```bash
blender -b --python media/library/3d_factory/blender_factory_v2.py -- \
  --asset l3d_v2_passport --motion passport_open --out 3d-library-v2
.venv/bin/python media/library/3d_factory/build_batch_v2.py --out 3d-library-v2 --hero-only
PREMIUM_3D_MODE=v10.2 .venv/bin/python scripts/ordinary_director_render.py \
  --source data/<project>/source --project-id <id> --language ru-RU \
  --duration 60 --seed 42 --out output/3d-quality-recovery/director-v10-2-e-preview-60s.mp4
```

## Report

`reports/LUMEN_3D_QUALITY_RECOVERY_V2.md`
