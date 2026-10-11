# CINEMATIC DIRECTOR V3 — COMPLETE VIDEO QUALITY RECOVERY

> **MAIN product prompt** for Lumen editing / Remotion render QA (locked 2026-10-11).  
> Hypit handoff prompt remains `backend/assembly_prompt.txt` (constructor → Hypit).  
> Do not confuse the two.

## Status

We have completed MEDIA LIBRARY EXPANSION V2.

**STOP GENERATING NEW MEDIA.**

This is a quality-recovery task, not a new product development task.

## Reference outputs

| File | Role |
| --- | --- |
| `lumen-9a9c116d (22).mp4` | Original negative baseline (if available; typically Downloads) |
| `output/remotion-engine-v1/preview.mp4` + frames | Latest Remotion regression evidence |
| `output/director-v3/preview-v3.mp4` | Target redesigned 20s preview |

Inspect the latest implementation first; preserve improvements already completed.  
Report unavailable reference files explicitly; do not pretend to inspect them.

The original baseline was previously rated 2/10. Reassess the latest preview from actual evidence; do not reuse that score automatically.

**Objective:** transform the existing video generation pipeline into a professional, high-retention short-form editing system.

**IMPORTANT:** DO NOT generate another mediocre video and report success. Inspect the actual output, identify root causes, fix the pipeline, and prove improvements with rendered video.

---

## 1. Current problems

- **P1** — Repetitive talking head; insufficient editorial variation
- **P2** — Poor media library utilization despite large curated library
- **P3** — Broken caption layout (tiny, narrow bands, overflow, weak contrast)
- **P4** — Repetitive animation; lack of layered motion / reveals / choreography
- **P5** — Weak Director (timeline generator, not creative editor)
- **P6** — Weak audio (music, ducking, SFX, loudness)
- **P7** — No strong retention structure (hook → progression → payoff)

## 2. Absolute requirements

User original video remains the foundation (identity, meaning, facts, authentic footage, original audio when language matches).

Media library supports; never replace speaker with unrelated slideshow.

DO NOT: rewrite entire app; rebuild library; destroy multilingual; replace speaker; fabricate claims; fake lip-sync; auto paid media gen.

Preserve: en-US, ru-RU, zh-CN.

## 3. First: complete video autopsy

Analyze the ENTIRE current video. Extract frames throughout. Measure A–K (speaker-only %, B-roll %, info scenes %, visual-change interval, unique assets/motions, caption geometry, music, repeats, weak Director decisions).

Compare against Director plan, SceneDefinition[], asset logs, caption timeline, render config.

Create: `reports/video-quality-autopsy.md` and `output/director-v3/` artifacts.

## 4–8. Director V3 creative editing

Upgrade existing Director. Shot plan per scene: narrative + visual + motion + media + speaker + audio + retention.

Speaker treatments 01–15 (fullscreen → PIP → B-roll → return). No dead visual sections (flag 20–40s static talking-head). Caption changes ≠ visual change.

Use `media/library/search.py` + manifest; rank by semantic match, quality, scene role, composition, text-safe, diversity, energy, motion potential. Avoid overusing globe/passport/house/couple/docs.

## 9 / 9A. Composition + blocking rules

Layers: background / midground / speaker / foreground / MG / kinetic type / captions.

**Composition priority:** authentic meaning → subject visibility → readable text → relevant media → decoration.

**Subject protection:** protected face regions; validate overlays through entrance/hold/exit including overshoot. Resolve by reposition / resize / alternate layout / omit decoration. No jitter chase.

**Vertical composition:** one dominant idea; no wholesale landscape shrink into portrait.

**Timing:** 1.5–4s guidance is editorial, not quota. Support reading + full motion. No sub-second flashes for variety.

**Asset clarity:** no placeholder rectangle+circle as “document.”

**Caption contrast:** dark backing or verified contrast; stable phrase geometry; language-aware wrap; check at phone size.

**Quality gates:** face obstruction, unreadable text, clipped required content, accidental flashes = **blocking**.

## 10–14. Motion, anti-repetition, captions

Motion families A–F (kinetic type, object, info, camera, transitions, layered). Anti-repetition across 3 consecutive scenes.

Caption engine V3: large readable, 1–2 lines, safe margins, sync to target-language alignment, no shrink-to-unreadable. Timing from target locale. Test EN/RU/ZH phrases with real frames.

## 15–17. Music / audio

Reuse licensed library; MUSIC_ASSET_REQUIRED if none. Ducking, speech-priority mix, subtle SFX. Prove from actual audio, not config.

## 18–22. Multilingual, source timeline, structure, hook, density

Preserve locale pipeline. Source provenance. Editorial structure adapted to speech. Deliberate first 3s hook. Meaningful scale; one dominant idea.

## 23. Expand motion selectively

No new clip generation this pass. Record gaps. Prefer Remotion/SVG presets.

## 24–28. Scoring, reference, 20s preview, visual/audio QA

Structured QA scores from observations. Baseline = negative. Preview must show speaker reframe, kinetic type, library media, layered scene, info motion, pro captions, music if available. Inspect moving video + frames. Audio QA from file.

## 29–30. Tests; no paid gen

Regression: captions, safe zones, anti-rep, music, collisions, contrast, aspect ratios. No paid APIs by default.

## 31. Outputs (`output/director-v3/`)

- video-quality-autopsy.md
- director-shot-plan.json
- asset-selection-report.json
- motion-usage-report.json
- caption-qa.md
- audio-qa.md
- preview-v3.mp4
- preview-v3-contact-sheet.jpg
- quality-comparison.md
- remaining-issues.md

Also: `reports/video-quality-autopsy.md`

## 32–34. Comparison + priorities + success

Work order: diagnose → face/caption safety → dead sections → Director/media → motion → music → render → fix → multilingual tests.

Success: speaker central; no long static; multiple treatments; library use; motion variety; readable captions; no broken words/overflow/lang mix; sync; mix; music when available; story-driven; clearly better than baseline.

## 34A. Docs + skills

Update architecture docs and agent skills with implemented behavior (subject protection, captions, timing, gates). Not aspirations.

## 35. Final instruction

DO NOT create infrastructure for its own sake.  
DO NOT generate media to hide poor editing.  
DO NOT solve typography with LLM prompts.  

FIX THE DIRECTOR. FIX THE CAPTION RENDERER. IMPROVE MOTION. USE THE LIBRARY. ADD SOUND DESIGN. PROVE WITH RENDERED VIDEO.

The 20s preview validates platform-wide improvements; do not claim universal reliability from one clip.

---

## Implementation notes (repo)

| Piece | Path |
| --- | --- |
| Remotion composition | `motion/src/preview/DirectorV3.tsx` |
| Composition id | `DirectorV3Preview` |
| Hero overlays | `motion/src/cinematic/HeroObject.tsx` |
| Concept viz | `motion/src/concepts/ConceptViz.tsx` |
| Hypit assembly prompt | `backend/assembly_prompt.txt` |
| Engine flag | `REMOTION_ENGINE_ENABLED` |

Known regression (2026-10-11): centered `DocumentStamp` / `HeroObject` covers presenter face; white/gold captions on light clothing lose contrast.

Recovery validation (same day): failed delivery `lumen-9a9c116d (31).mp4` autopsy in `output/director-v3/`; fixes in `portraitLayouts.ts` + `DirectorV3.tsx` caption pill / split fill / criteria explanations / consult cover. Prove with `output/director-v3/preview-v3-r2.mp4` — do not claim full-minute PASS without a new full render.

Semantic coverage pass: `preview-v3-r4.mp4` (+ excerpts) — situational retrieval, eligibility-before-rank, shared scrim/ProgressSteps fixes; reports under `output/director-v3/semantic-selection-r4.md`. Stop new media; no auto-deploy from this pass.
