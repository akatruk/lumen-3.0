# Remotion engine

## CURRENT STATE

- Package: `motion/` (Remotion **4.0.524**, React 19)
- Canvas: 1080×1920 @ 30 fps (`motion/src/themes/tokens.ts`)
- Registry: `motion/src/registry/` — Director picks type/variant/data only
- Typography: `AutoFitText`, `AnimatedCaption` — never bake text into gens
- Compositions: `DirectorV3Preview`, showcase, real-estate, immigration clips
- Library clips entry: `motion/src/clips/` (`ClipRoot` + `premium/` V4 calibration heroes/concepts/FG/BG/scenes)
- Concept triggers: `motion/src/concepts/` (spoken phrase → viz preset)
- Cinematic plates: `motion/src/cinematic/` (V5 batch1 treatments: mist_paper, teal_depth, midnight_ridge, graphite_drift, …)
- **Semantic motion V14:** `motion/src/semantic/` — `SemanticMotion` (5 components × 3 layouts), `layouts.ts` face/PIP/caption exclusions, gallery composition `SemanticMotionV14Gallery`. Mounted from `scene.semanticMotionV14` in `DirectorV3` when the plan carries it. Frame-driven `interpolate` only. Connectors use `adaptiveLineStyle`. Flag off = this layer is absent.
- **Semantic motion V15:** same mount, `componentsV15.tsx` (10 components × 3 layouts). Gallery `SemanticMotionV15Gallery`. Payloads still travel on `scene.semanticMotionV14`. Flag `SEMANTIC_MOTION_V15_ENABLED` default off.
- **Scene composer V16:** `SemanticMotion` uses `motionRect` only when `compositionClears` says it misses the face and the caption plate. `enterFrame` delays the diagram to the spoken timestamp. `DirectorV3` fullscreen speaker for overlay; split paints the staged clip full-bleed and the speaker in `speakerRect`. Flag `SCENE_COMPOSER_V16_ENABLED` default off. Flag off keeps the V14/V15 layout.
- **Adaptive connector contrast:** `motion/src/utils/adaptiveLineStyle.ts` → `adaptiveLineStyle({background, path, preferredColor, strokeWidth, sceneTheme})`. Wired into `BusinessMotion` / `ConnectorStroke` / ConceptViz growth arrows. Full-path sampling (not endpoints). Fixes gold/light strokes on beige paper plates.
- Transitions: `soft_pull`, `cross_blur`, `iris_soft` in `SceneTransition`
- Business motion: `capital_flow` + existing shareholder/capital/ownership presets
- Premium clip encode: PNG sequence → system ffmpeg `libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0` (`media/library/render_premium_motion_v4.py`)
- Env: `LUMEN_BACKGROUND_PLATE=<treatment>` on `ordinary_director_render.py` for plate QA

## TARGET STATE

Remotion owns typography, captions, graphics, layout, transitions, visual timing.
Original speaker video stays the protagonist. Library assets resolve by id before render.

## IMPLEMENTED (V1 → V5)

- Validated scene schema + `normalizeScene` / `renderScene`
- `animated_diagram` + concept-trigger overlays on Director V3
- Backend `resolve_scene_plan()` → immutable render plan JSON
- Feature flag `REMOTION_ENGINE_ENABLED` / `settings.remotion_engine_enabled` (**default on in V5**)
- Director V4 `director_execution.enforce_plan` inside resolve
- Transcript captions via `caption_phrases` → `attach_transcript_captions` → Remotion props
- `should_use_remotion(pid)` gates Create Video (project «e» always)
- V7: executes `shotPlan` (layouts, cardMode `progressive_one`, kinetic hook); caption Sequences skip empty text; bed duck ~0.34
- V8: dynamic N-beat `SceneRouter` for `long60`; `SemanticMotionClip` renders staged `semanticMotion.staged` webm (~520px cover, face-safe); verify audit pass + actual frames, not presets alone
- V9: `FloatingForeground` for transparent SVG/PNG; omit bordered webm shelves; `CleanSteps` speaker-led type; softer caption pills; honor `compositionPolicy=v9_clean`

## Contract

Director may choose: scene type, variant, asset ids, speaker treatment, localized text, timing intent, transition, energy.
Director must not choose: CSS, React, x/y, font files, raw animation code.

## Storage

`/mnt/volume_nyc1_1791446889637/lumen-motion` when mounted; else `motion/output` / `motion/public`.
