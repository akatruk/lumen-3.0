# Remotion engine

## CURRENT STATE

- Package: `motion/` (Remotion **4.0.524**, React 19)
- Canvas: 1080×1920 @ 30 fps (`motion/src/themes/tokens.ts`)
- Registry: `motion/src/registry/` — Director picks type/variant/data only
- Typography: `AutoFitText`, `AnimatedCaption` — never bake text into gens
- Compositions: `DirectorV3Preview`, showcase, real-estate, immigration clips
- Concept triggers: `motion/src/concepts/` (spoken phrase → viz preset)
- Cinematic plates: `motion/src/cinematic/`

## TARGET STATE

Remotion owns typography, captions, graphics, layout, transitions, visual timing.
Original speaker video stays the protagonist. Library assets resolve by id before render.

## IMPLEMENTED (V1)

- Validated scene schema + `normalizeScene` / `renderScene`
- `animated_diagram` + concept-trigger overlays on Director V3
- Backend `resolve_scene_plan()` → immutable render plan JSON
- Feature flag `REMOTION_ENGINE_ENABLED` / `settings.remotion_engine_enabled`

## Contract

Director may choose: scene type, variant, asset ids, speaker treatment, localized text, timing intent, transition, energy.
Director must not choose: CSS, React, x/y, font files, raw animation code.

## Storage

`/mnt/volume_nyc1_1791446889637/lumen-motion` when mounted; else `motion/output` / `motion/public`.
