# AI Director

## CURRENT STATE (V5)

- **Default production path:** Director V4 + Remotion when `REMOTION_ENGINE_ENABLED=1` (default). Hypit is explicit legacy only (`REMOTION_ENGINE_ENABLED=0`).
- Project create does **not** call the Director. Deferred source plan: `backend/source_analysis.ensure_analysis`.
- Semantic visual plan: `backend/visual_variation.resolve_plan(seed, energy, language=project.language)` — locale goes to `search_assets`. Card copy does not fall back to English (ADR-010, ADR-004).
- **Execution:** `backend/director_execution.enforce_plan` (PIP ≥324px, heading completeness, caption≠card, statistic dedupe) inside `resolve_scene_plan`
- **Captions:** transcript → `caption_phrases` → Remotion (not LLM caption fragments)
- **V6:** `locale_consistency` + `director_semantics` — one viewer locale; speech-backed headlines/cards; layout diversity; reject EN captions under RU cards
- **V7:** `director_shot_plan.py` — per-beat shot plans + choreography + keywords≠captions + anti-repetition (`maxSplitStreak < 3`). Progressive cards. Report: `reports/LUMEN_V7_PREMIUM_MOTION.md`
- **V8:** `director_v8.py` — `long60` (10 beats) for ≥45s; semantic concept → library webm bindings; stage + `semanticMotionAudit`; Remotion mounts `SemanticMotionClip`. Report: `reports/LUMEN_V8_SEMANTIC_MOTION_60S.md`. Do not stretch a 20s preview.
- **V9:** `director_v9.py` — composition intelligence (`primaryVisualRole`, complexity budget, `containerPolicy=minimal`, transparent floats, caption dedupe). Prefer fewer containers over more motion. Report: `reports/LUMEN_V9_PREMIUM_CLEAN_MOTION.md`.
- **V10:** `director_v10.py` — upgrades V9 floats to premium Blender 3D alpha (`premium_3d`) when registry available; keeps `v9_clean` hierarchy. Report: `reports/LUMEN_3D_ASSET_FACTORY_V1.md`.
- **V11:** `director_v11.py` — semantic content map from transcript; topic domain (`investment` / `immigration` / `mixed`); evidence-required visual selection; rejects immigration cards/queries on unrelated speech (e.g. origin1 capital/shareholder/Thailand). After V9, before optional 3D. Report: `reports/DIRECTOR_V11_SEMANTIC_INTELLIGENCE.md`.
- **V11.1:** `director_v11_1.py` — factual grounding + provenance (`sourceSegmentId/start/end/originalSourceText`) for numbers/legal/ownership claims; Remotion `BusinessMotion` components (shareholder_structure, equity_distribution, capital_investment, …); rejects invented counts (no BigFigure default `2`). After V11, before optional 3D. Report: `reports/DIRECTOR_V11_1_FACTUAL_GROUNDING.md`. Origin1: spoken **≥3 shareholders**, not 2.
- **V11.2:** `director_v11_2.py` — composition repair on V11.1. Remaining “2 Shareholders” was CleanSteps `{n}+Shareholders` step label (not BigFigure). Scrubs fake headcount labels; face-safe BusinessMotion placement; softer captions. Report: `reports/DIRECTOR_V11_2_COMPOSITION_REPAIR.md`.
- **V14 semantic motion** (`SEMANTIC_MOTION_V14_ENABLED`, default **0**): `backend/director_v14.py` runs after V10. Speech window → one evidence-backed component (`capital_flow`, `shareholder_network`, `business_comparison`, `ownership_split`, `process_timeline`) and a layout (`overlay` under the face, `speaker_visual` on splits, `full_frame` for a spoken percentage). Unsupported scenes stay talking-head. On a selected scene, text-card stacks and `businessMotion` panels are removed. 49% does not become 51%. No invented shareholder count, comparison side, or process step. Registry match works with pgvector off. Report: `reports/LUMEN_SEMANTIC_MOTION_V14.md`.
- **V11.2 + Media Factory V5:** stamps `sceneTheme` / `connectorBackground` on BusinessMotion from `backgroundPlate` for adaptive connector contrast. Editorial baseline stays V11.2; `PREMIUM_3D_MODE=off`; `quality_gate_v2.production_ready` empty. Origin1 A/B: `output/premium-media-v5/{baseline-v11-2,premium-motion-v12-test}.mp4`.
- Studio create-video stores `visual_plan` on `director_v3` when `should_use_remotion`
- **Experience memory** (`VISUAL_EXPERIENCE_MEMORY_ENABLED` or `VISUAL_INTELLIGENCE_ENABLED`, both default off): before a plan is stored, `attach_to_visual_plan` may attach at most 8 advisory hits (`experienceMemory`): similar successes, failures, incidents, and assets in the same project/domain. RunPod and OpenRouter prompts get the same bounded block. Memory does not rewrite scenes, captions, or spoken facts, and must not copy an unrelated scene. Off = those paths do not query pgvector. Hybrid asset search runs only when `VISUAL_INTELLIGENCE_ENABLED=1`: keyword retrieval, then a semantic rerank that keeps the spoken concept and does not sort by cosine. The beat id `residency` is not a topic. Investment speech replaces its default query before search. See `docs/architecture/AI_MEMORY.md`.
- Hypit model brief (legacy): `backend/assembly_prompt.txt` via `hypit_prompt.py`

## TARGET STATE

Director decides WHAT (scene purpose, assets, treatments, energy).
Remotion decides HOW (pixels, easing, typography).
`resolveScenePlan()` freezes a validated render plan before any Remotion call.

## IMPLEMENTED (V1)

- Seeded anti-repetition for backgrounds / layouts / transitions
- `backend/remotion_engine.resolve_scene_plan` wraps visual plan + motion metadata + locale
- Concept-trigger presets for spoken-concept viz
- Eligibility-before-rank library search; situational queries; no passport placeholder when photo exists
- Same-source ban: main plate and inset cannot share canonical identity (still + i2v)
- Premium motion V4 (`pm_*` deterministic WebM) is searchable via multilingual tags; prefer for conceptual/hero overlay beats when Remotion engine is enabled
- Consult beat: one cover plate + presenter PIP from original speaker timing (never duplicate library inset)
- Long-form captions follow `beatsFor` (not fixed 20s stamps); ordinary full-render helper: `scripts/ordinary_director_render.py`
- Recent-history anti-repeat scans all `visual-history/*.json` and prefers never-recent plates

## NOT IMPLEMENTED

- LLM-authored freeform scene graphs outside the registry
- Per-phrase dynamic beat length from full Whisper alignment for all projects
- **Director V4 production LLM** (DigitalOcean Gradient / `https://inference.do-ai.run/v1`) — blocked: no `MODEL_ACCESS_KEY` / `GRADIENT_MODEL_ACCESS_KEY` on lumen-test; OpenRouter forbidden for this track. Details: `reports/LUMEN_DIRECTOR_V4.md`.
