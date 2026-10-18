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
- **Premium Media Factory V5 (batch1):** recipe `recipes/premium-media-factory-v5-batch1.json`, indexer `scripts/index_premium_media_v5_batch1.py`, contact sheet `media/library/out/contact-sheets/premium-media-v5-batch1.html`. Adds **23** Remotion/metadata rows (8 cinematic BG plates, 4 parallax, 3 premium-3D candidates `needs_review`, 5 business motion, 3 transitions). Generative I2V/masters **BLOCKED_ON_GPU_APPROVAL**. Report: `reports/LUMEN_PREMIUM_MEDIA_FACTORY_V5.md`. GPU choice: `reports/PREMIUM_GPU_SELECTION.md`. **Do not treat `pmv5_bg_*` abstract plates as real-world environmental backgrounds.**
- **Cinematic Env Factory V6 (batch1):** replace abstract BG generation with photoreal environmental cinema (business / RE / family-reloc / city / investment). Plans `media/library/plans/cinematic-env-v6-batch1.jsonl` + `cinematic-env-v6-i2v-batch1.jsonl` (16 clips). Recipe `recipes/cinematic-env-factory-v6-batch1.json`. Indexer `scripts/index_cinematic_env_v6_batch1.py`. Family `cinematic_environment`. Volume path `motion/cinematic-env-v6/`. GPU audit `reports/CINEMATIC_ENV_FACTORY_V6_GPU_AUDIT.md`; delivery `reports/CINEMATIC_ENV_FACTORY_V6.md`. Pod runner `scripts/run_cinematic_env_v6_on_pod.sh` (pinned `dznvwn90el5au4` only).

## TARGET STATE

One language-neutral library. Contract: ADR-010. RU/EN/ZH queries expand to English tags. Remotion never embeds the whole library in the frontend build — resolve by asset id at plan time. Prefer Remotion deterministic motion for objects/graphics; generative I2V only when weights + budget exist.

## Rules

- Prefer `search_assets(query=…)` over hardcoded filenames
- No readable text/logos in generative stills or motion clips
- Quarantine before delete (cleanup agents); never wipe approved media in engine work
- Coordinate additively with other agents touching `search.py`
- Do not claim H.264 has alpha — production alpha is `libvpx-vp9` `yuva420p`
- **Premium 3D V1:** Blender factory `media/library/3d_factory/` → `motion/premium3d/*.webm` + `models/premium3d/*.glb` + BLEND sources. Registry rows in `premium-3d-v1-rows.json`. Director V10 selects by concept. Report: `reports/LUMEN_3D_ASSET_FACTORY_V1.md`. RunPod EXITED → local Blender pilot; do not resume GPU without auth.
- **Semantic motion V14:** component catalog `media/library/catalogs/semantic_motion_v14.json`, lookup `media/library/semantic_motion_registry.py`. Five motion components (not binaries), three layouts, RU/EN/ZH tags. Deterministic keyword match. Descriptions are text-only and are **not** written into CLIP `asset_embeddings`. `VISUAL_INTELLIGENCE_ENABLED` stays 0. Recipes: `recipes/semantic-motion-v14.json`. Flag `SEMANTIC_MOTION_V14_ENABLED` default 0. V15 adds ten rows to the same catalog (15 components, 45 layout variants). Flag `SEMANTIC_MOTION_V15_ENABLED` default 0. Recipes: `recipes/semantic-motion-v15.json`. V16 does not add components. It swaps a staged clip only when the current `assetId` contradicts the spoken intent, and only to a clip already in the manifest. Recipes: `recipes/scene-composer-v16.json`. Flag `SCENE_COMPOSER_V16_ENABLED` default 0. V17 indexes those component descriptions in `motion_component_index` (512-d text model only, not CLIP `asset_embeddings`). Flag `MOTION_QUALITY_V17_ENABLED` default 0. V18 does not add catalog rows. It refuses a component when the scene quote does not support it and retargets a Bangkok-skyline query from the words in that beat. Flag `MOTION_DESIGN_V18_ENABLED` default 0.
- **Experience embeddings:** text tags (including `tags_ru` / `tags_zh`) use `clip-ViT-B-32-multilingual-v1`. Image files and video keyframes use the CLIP vision encoder `clip-ViT-B-32` (512-d, shared space). Vectors live in PostgreSQL `asset_embeddings` (view `media_embeddings`). Video rows store `frame_seconds`. Binaries stay on the media volume. Full approved index: `scripts/index_experience_assets.py --approved`. Hybrid search is `VISUAL_INTELLIGENCE_ENABLED` (default off): keyword candidates, then semantic rerank. Cosine does not outrank a keyword hit. Reviewed intents live in `media/library/relevance/intents_v2.json`. See `docs/architecture/AI_MEMORY.md`.
