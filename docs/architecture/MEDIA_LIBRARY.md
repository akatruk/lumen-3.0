# Media library

## CURRENT STATE

- Root (DO volume): `/mnt/volume_nyc1_1791446889637/app-library` (target ~811 assets / ~400 runpod)
- Repo mirror: `media/library/out/manifest.json` (may lag volume)
- Search: `media/library/search.py` + `concepts.py` + additive `concept_triggers.py`
- Families: photography, editorial_object, deterministic_motion, generative_motion, vector/SVG
- Staging into Remotion: `visual_variation.stage_backgrounds` → `motion/public/director-v3/picked/`

## TARGET STATE

One language-neutral library. RU/EN/ZH queries expand to English tags. Remotion never embeds the whole library in the frontend build — resolve by asset id at plan time.

## Rules

- Prefer `search_assets(query=…)` over hardcoded filenames
- No readable text/logos in generative stills
- Quarantine before delete (cleanup agents); never wipe approved media in engine work
- Coordinate additively with other agents touching `search.py`
