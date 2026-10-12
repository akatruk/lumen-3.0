---
name: lumen-3d-assets
description: >-
  Lumen Premium 3D Asset Factory: Blender procedural objects, alpha VP9
  masters, GLB/BLEND sources, DigitalOcean library indexing, Director V10.
---

# Lumen 3D assets

## Rules

- Quality gate: **5 objects × 3 motions** before mass production.
- True alpha = PNG sequence or VP9 `yuva420p` WebM. Never claim H.264 has alpha.
- No baked language text / logos / passport numbers in geometry.
- RunPod builds at scale when authorized; local Blender OK for pilot.
- Do **not** resume RunPod without explicit authorization.
- Store masters on DigitalOcean volume (`app-library`); not only on RunPod.

## Paths

- Factory: `media/library/3d_factory/`
- Output: `3d-library/` (models, blender, alpha, previews, registry)
- Library publish: `motion/premium3d/` via `index_3d_assets.py --publish-binaries`
- Director: `backend/director_v10.py`
- Remotion: `FloatingForeground` with `transparent` OffthreadVideo for alpha webm

## Commands

```bash
blender -b --python media/library/3d_factory/blender_factory.py -- \
  --asset l3d_generic_passport --motion reveal --out 3d-library
.venv/bin/python media/library/3d_factory/build_batch.py --out 3d-library
.venv/bin/python media/library/3d_factory/index_3d_assets.py --publish-binaries
```

## Report

`reports/LUMEN_3D_ASSET_FACTORY_V1.md`
