---
name: lumen-director
description: >-
  AI Director semantic planning, seeded visual variation, motion presets, and
  resolveScenePlan. Director chooses WHAT; Remotion chooses HOW. For Director
  V3 / Remotion / video QA recovery, load docs/prompts/cinematic-director-v3-quality-recovery.md first.
---

# Director

**MAIN prompt (Director V3 / Remotion / video quality recovery):**  
load and follow `docs/prompts/cinematic-director-v3-quality-recovery.md` before planning or coding.  
Index: `docs/prompts/README.md`. Hypit handoff is separate: `backend/assembly_prompt.txt`.

- Plans: `backend/visual_variation.py` (`resolve_plan`, `plan_for_request`)
- Editing prefs: `prompt_modules/editing_controls.py` → `apply_editing_controls`
  (Animation/Intensity/Motion/Density + Calm/Balanced/Dynamic). Create-video
  passes `editing=` into `plan_for_request`; Remotion reads
  `visualPlan.editingControls` (motion gain, concept cap, `animateGraphics`).
- Engine wrap: `backend/remotion_engine.resolve_scene_plan`
- Composition: `motion/src/preview/DirectorV3.tsx` (`DirectorV3Preview`)
- Shared portrait geometry: `motion/src/preview/portraitLayouts.ts` (splits fill 1080×1920; face band; criteria explanations RU/EN/ZH)
- Registry types/variants: `motion/src/types/scene.ts`
- Concept triggers: `motion/src/concepts/` + `media/library/concept_triggers.py`

Director runs at **Create video**, not at project upload. Default plan builder is local heuristic (`backend/providers/director.py`). Optional LLMs: `LLM_PROVIDER=openrouter` (forbidden on the RunPod Director track) or `LLM_PROVIDER=runpod` (Ollama on `lumen-hypit-4090`, fail-closed). Source transcript/cache: `backend/source_analysis.py`.

**RunPod Native Director V1 (2026-10-12):** replaces DO Inference blocker for this track — model `qwen2.5:7b-instruct`, runtime Ollama `/v1`, SSH tunnel only. See `reports/RUNPOD_DIRECTOR_V1.md`. When `LLM_PROVIDER=runpod`, never silent-heuristic; raise `RUNPOD_LLM_UNAVAILABLE`.

Speaker presence is required. Same seed + versioned inputs → same visuals.
Never emit CSS, React, or x/y from the Director.
Subject protection and caption contrast are blocking (see MAIN prompt §9A).

Implemented (not aspirational):
- Captions use a dark pill (`data-caption-backing="dark"`); locale from `visualPlan.language`.
- Split layouts use `splitSpeakerRect` / `splitMediaRect` — no landscape shrink into a black void.
- Beside cards are title + relationship explanation (`criteriaCardsFor`), not single-word labels.
- Concept overlays are beat-gated; speaker PIP is skipped when a primary speaker panel is already on screen.
- Consult prefers full-bleed `consult.mp4`; sparse stamp `.webm` plates are not mounted as panels.
- Validation: `preview-v3-r5.mp4` (preserve r2–r4) + ordinary fulls under `output/director-v3/ordinary/` (`e-full` / `b-full` / `c-full`).
- Ordinary path script: `scripts/ordinary_director_render.py` (= resolve_plan→resolve_scene_plan→render_with_plan). Default create-video duration is 20s unless `duration_seconds` set to max step.
- Prompt load: Hypit → `assembly_prompt.txt`; Remotion → `visual_variation` + `remotion_engine`. MAIN brief in docs only.
- Rules: `director_media_rules.py`; captions keyed to `beatsFor`; RouteLink under face band; caption bottom = `captionClearance`.
- `recent_asset_ids` reads all `visual-history/*.json` (not only `gen_*`); prefer non-recent plates; FG skips `concept_*`.
- Consult: one cover + presenter PIP from `speakerFile` — never duplicate library inset.
- **Director V4 execution compliance:** `backend/director_execution.py` validates/repairs structured `execution` (min PIP ≥324px, incomplete headings, fragment cards, redundant stats) inside `remotion_engine.resolve_scene_plan`. Remotion `pipRect()` enforces layout floor. Report: `reports/DIRECTOR_EXECUTION_COMPLIANCE.md`.
- **V5 cutover:** `REMOTION_ENGINE_ENABLED` defaults **on**; `should_use_remotion` is the Create Video gate. Captions from `caption_phrases` / transcript (`captionSource`), not LLM fragments. Transparency: `renderer`, `directorMode`, `executionValidation`, `captionSource`. No silent Hypit fallback. Report: `reports/REMOTION_PRODUCTION_CUTOVER_V5.md`.
- **V6 quality:** `locale_consistency` + `director_semantics` (speech headlines/cards, layout diversity). Never EN captions with RU cards. RCA: `reports/LUMEN_V6_ROOT_CAUSE.md`. Preview: `output/director-v6/`.
- **V7 motion:** `director_shot_plan.py` stamps choreography + anti-repetition; Remotion progressive cards; no empty caption plates. Preview: `output/director-v7/`. Report: `reports/LUMEN_V7_PREMIUM_MOTION.md`.
- **V8 semantic motion (60s):** `backend/director_v8.py` expands ≥45s plans to `long60` (10 beats), binds spoken concepts → library webm (`MOTION_BINDINGS`), stages into Remotion `public/picked/`, audits `semanticMotionAudit`. Remotion `SemanticMotionClip` must actually mount staged files — preset alone ≠ rendered. Preview: `output/director-v8/director-v8-e-preview-60s.mp4`. Report: `reports/LUMEN_V8_SEMANTIC_MOTION_60S.md`. Do not stretch a 20s preview.
- **V9 premium clean:** `backend/director_v9.py` — one primary idea/scene, complexity budget, omit opaque webm boxes, prefer transparent SVG/PNG floats, dedupe caption loops, disable concept stack. Remotion `FloatingForeground` (no black shelf). Preview: `output/director-v9/`. Report: `reports/LUMEN_V9_PREMIUM_CLEAN_MOTION.md`. Quality = composition, not more objects.
- **V10.2 premium 3D:** default `PREMIUM_3D_MODE=v10.2` → `quality_gate_v2.json`, **no auto 3D** until `production_ready`. V2 factory (`l3d_v2_*`) improved alpha/framing; materials still NEEDS_REWORK. Skill: `lumen-3d-assets`. Rollback baseline: V9.
- **V11 semantic intelligence:** `backend/director_v11.py` — speech-first topic map (`build_semantic_map`), evidence-gated cards/queries/motion, scrub immigration defaults off investment speech. Runs after V9, before premium 3D.
- **Evidence gate:** `backend/director_evidence.apply_evidence_gate` runs in `director_v3.run_job` after V14–V18. A card or step label is kept only when that scene's quote contains it. Domain packs (目标/家庭/预算, 全程陪同) are not shown otherwise. `director_v11._concepts_for_scene` only uses concepts whose timestamps overlap the beat (1.5s pad). A template query with no local concept is cleared. `drop_repeated_assets` keeps the first plate identity and drops later copies. `director_quality_shadow.diagnose` writes findings and does not change the plan. V14–V18 stay default off.
- **V11.1 factual grounding:** `backend/director_v11_1.py` — spoken-fact extraction; every factual visual needs provenance; Remotion `motion/src/preview/BusinessMotion.tsx` (ownership nodes, equity bar, capital flow, control lock — labels RU/EN/ZH, numerals identical). Never invent shareholder counts (`BigFigure` has no default `2`). Origin1 quote: «普通泰国有限公司通常需要至少三名股东» / “at least three shareholders” (`seg_006`). Artifacts: `output/director-v11-1/{source-fact-validation,business-motion-usage,caption-qa}.json`. Report: `reports/DIRECTOR_V11_1_FACTUAL_GROUNDING.md`.
- **V11.2 factual + composition repair:** `backend/director_v11_2.py` — remaining “2 Shareholders” came from CleanSteps painting `{n} {label}` on investment step pack `Shareholders` (slot 1 → **2 Shareholders**), not BigFigure. Scrubs numbered headcount step/card labels; Structure pack; face-safe `BusinessMotion` placement (`media_column` / `below_face_band`); softer caption plates. Artifacts: `output/director-v11-2/{factual-validation,face-collision-report,caption-qa}.json`. Report: `reports/DIRECTOR_V11_2_COMPOSITION_REPAIR.md`.
- **Experience memory:** `backend/experience_memory.py`. Flags `VISUAL_EXPERIENCE_MEMORY_ENABLED` and `VISUAL_INTELLIGENCE_ENABLED` default off. When on, Director receives at most 8 untrusted advisory hits and prefers verified reviews. Memory must not override source facts or copy an unrelated scene. Intelligence search is keyword retrieval plus `media/library/rerank.py`. Cosine does not outrank a keyword hit. The beat id `residency` is internal; investment speech replaces its default query. Video ratings are 1–10 in `generation_reviews`. Scene flags go to `scene_feedback`. Doc: `docs/architecture/AI_MEMORY.md`.
- **V14 semantic motion:** `backend/director_v14.py`, flag `SEMANTIC_MOTION_V14_ENABLED` default **0**. After V10. One diagram per spoken fact: capital flow, shareholder network (count only if spoken), comparison (both sides + contrast), ownership split (spoken % only, no complement), process timeline (named steps only, including Chinese 第N层 / 第N步 labels copied from the quote). Else talking head. Report: `reports/LUMEN_SEMANTIC_MOTION_V14.md`.
- **V15:** `backend/director_v15.py`, flag `SEMANTIC_MOTION_V15_ENABLED` default **0**. Adds risk, allocation, ecosystem, document workflow, metrics, decision, geography, milestones, contract, before/after only with source evidence. Origin1 document steps replace the generic timeline. Report: `reports/LUMEN_SEMANTIC_MOTION_V15.md`.
- **V16 scene composer:** `backend/scene_composer_v16.py`, flag `SCENE_COMPOSER_V16_ENABLED` default **0**. Layout only. Speaker stays large. No tiny PIP, no navy full-frame plate. Recipes: `recipes/scene-composer-v16.json`. Report: `reports/LUMEN_SCENE_COMPOSER_V16.md`.
- **V17:** `backend/motion_quality_v17.py`, flag `MOTION_QUALITY_V17_ENABLED` default **0**. pgvector retrieves verified scene flags. It does not train Director and does not score a component from one review. Report: `reports/LUMEN_MOTION_QUALITY_V17.md`.
- **V18 motion design:** `backend/motion_design_v18.py`, flag `MOTION_DESIGN_V18_ENABLED` default **0**. Runs after V16. A scene keeps a diagram only when that scene's quote supports it. `泰国` alone does not draw `股权结构`. Unsupported beats stay a full-frame talking head. Same component is not repeated on the next beat unless that quote requires it, and three identical compositions are dropped. Report: `reports/LUMEN_MOTION_DESIGN_V18.md`.
- **Adaptive connector contrast (Media Factory V5):** Remotion `adaptiveLineStyle` + Director stamps `sceneTheme`/`connectorBackground` from `backgroundPlate`. Do not redesign Director; keep `PREMIUM_3D_MODE=off` until `quality_gate_v2.production_ready` non-empty.
