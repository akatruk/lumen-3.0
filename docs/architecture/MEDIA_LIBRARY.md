# Media library

## CURRENT STATE

- Root (DO volume): `/mnt/volume_nyc1_1791446889637/app-library` (**829** rows after premium-motion V4 calibration; was ~811)
- Premium motion: `motion/premium/pm_*.webm` (VP9 `yuva420p` alpha except opaque BG) — recipes in `media/library/recipes/premium-motion-v4-calibration.json`
- Contact sheets: `contact-sheets/premium-motion/`
- Repo mirror: `media/library/out/manifest.json` (may lag volume); commit rows via `out/premium-motion-v4-rows.json` + `index_premium_motion_v4.py`
- Search: `media/library/search.py` + `concepts.py` + additive `concept_triggers.py` — haystack includes `tags_ru` / `tags_zh`
- Families: photography, editorial_object, deterministic_motion, generative_motion, vector/SVG
- Staging into Remotion: `visual_variation.stage_backgrounds` → `motion/public/director-v3/picked/`
- Report: `reports/PREMIUM_MOTION_LIBRARY_V4.md`

## TARGET STATE

One language-neutral library. RU/EN/ZH queries expand to English tags. Remotion never embeds the whole library in the frontend build — resolve by asset id at plan time. Prefer Remotion deterministic motion for objects/graphics; generative I2V only when weights + budget exist.

## Rules

- Prefer `search_assets(query=…)` over hardcoded filenames
- No readable text/logos in generative stills or motion clips
- Quarantine before delete (cleanup agents); never wipe approved media in engine work
- Coordinate additively with other agents touching `search.py`
- Do not claim H.264 has alpha — production alpha is `libvpx-vp9` `yuva420p`
- **Premium 3D V1:** Blender factory `media/library/3d_factory/` → `motion/premium3d/*.webm` + `models/premium3d/*.glb` + BLEND sources. Registry rows in `premium-3d-v1-rows.json`. Director V10 selects by concept. Report: `reports/LUMEN_3D_ASSET_FACTORY_V1.md`. RunPod EXITED → local Blender pilot; do not resume GPU without auth.
