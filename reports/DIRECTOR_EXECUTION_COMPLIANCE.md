# DIRECTOR V4 — Execution Compliance & Automatic Repair

**Date:** 2026-10-12  
**Host:** local Remotion + lumen-test deploy  
**Baseline reference:** `~/Downloads/lumen-32012faa (3).mp4` (sha256 `4ed9555e…8831a`)  
**Git commit:** _(filled at push)_  

## Phase 1 — Audit (baseline)

| Defect | Frame evidence | Root cause layer |
| --- | --- | --- |
| Tiny speaker circle PIP | t3, t12, t28 — host ≪ 20% frame | **Hypit interpretation** of freeform prompt (circle recipe ~180px). Not Remotion `conceptPip`. |
| Incomplete headings (`Look at`) | proof frames earlier; pack captions | **Hypit** + **caption pack** strings; planner lacked heading validation |
| Subtitle fragments as cards | t3 caption cut mid-phrase; dual-card UI | **Hypit** treating speech fragments as graphic plates |
| Duplicate `49%` (headline+card+bar) | t28 | **Hypit** density / figure stacking |
| Weak hierarchy | B-roll dominates, host decorative | **Hypit** composition; no post-plan enforce |

**Not Remotion layout bugs** for this baseline — file is a Hypit delivery. Remotion path already used larger rounded PIP; V4 makes that contract **validated + repaired** before render.

## Phase 2 — Structured Director plan

Each scene now carries `execution`:

- `scenePurpose`, `speakerFraming`, `speakerVisibility`, `mediaRole`
- `headline`, `cardText`, `caption`, `captionMode`
- `motionPreset`, `pip`, `safeZones`, `timing`, `expectedResult`

Emitted from `visual_variation.resolve_plan`; normalized in `director_execution.normalize_execution`.

## Phases 3–7 — Rules (deterministic)

Implemented in `backend/director_execution.py` (not prompt text):

| Rule | Behavior |
| --- | --- |
| Speaker min PIP | `MIN_PIP_WIDTH_PX = 324` (~30% of 1080); Remotion `pipRect()` / `conceptPip` 360×480 |
| Tiny circle | Repair → split (if media) or fullscreen |
| Fragment cards | Reject incomplete / speech-substring cards → caption-only or drop |
| Incomplete headings | Reject `Look at`, `but this…`, clause tails → drop headline |
| Redundant stats | `49%` + `49%` → keep headline, clear card |
| Typography locales | Remotion `AutoFitText` + dark caption pill (existing); mid-word hyphen trim |

## Phases 8–9 — Visual QA + repair

- `validate_scene` / `repair_scene` / `enforce_plan` (max 3 attempts, then fail-closed fullscreen)
- `qa_sample_points` — entrance / hold / exit timestamps
- Wired into `remotion_engine.resolve_scene_plan` → `executionCompliance` on render plan

## Phase 10 — 20s preview

| | |
| --- | --- |
| **Output** | `output/director-v4/preview-20s.mp4` |
| **Desktop** | `~/Desktop/director-v4-preview-20s.mp4` |
| **Source** | `Desktop/original1.mp4` (same semantic track family; Remotion speaker) |
| **sha256** | `bd1816cc5befeb96d971a89ab28ae1ebaebbf19c3a0935b776feacb3a1e7538a` |
| **Probe** | 1080×1920 · 20.0s video + audio |
| **Plan** | `executionCompliance.version = director_execution_v4`; PIP width stamped 360 |

**vs baseline:** larger rounded speaker PIP (not tiny green circle); split/fullscreen layouts available; no Hypit fragment dual-cards / triple-49% in this Remotion cut.

## Remaining failures

1. **DirectorV3 caption pack** still emits short RU/EN marketing lines (`the right program`, letter flashes) — not wired to project transcript yet (known gap in `lumen-director` skill).
2. **Hypit ordinary Create Video** still uses `assembly_prompt.txt` freeform path — V4 enforce does **not** rewrite Hypit pixels; flag Remotion (`REMOTION_ENGINE_ENABLED`) for enforcement on ordinary projects.
3. Automated **pixel** face-collision CV not added — geometry gates are plan/layout deterministic; frame sampling is for human/agent QA.

## Components changed

- `backend/director_execution.py` _(new)_
- `backend/remotion_engine.py` — `enforce_plan` in resolve
- `backend/visual_variation.py` — execution contract fields
- `motion/src/preview/portraitLayouts.ts` — larger PIP + `pipRect()`
- `motion/src/preview/DirectorV3.tsx` — use `pipRect()`
- `backend/tests/test_director_execution.py` _(new)_

## Regression tests

```
pytest backend/tests/test_director_execution.py \
       backend/tests/test_director_media_rules.py \
       backend/tests/test_remotion_engine.py
→ 16 passed
```

## Deployment

- Fast AI-free create preserved (`FAST_PROJECT_CREATION_ENABLED`)
- No RunPod restart for this Remotion-only change
- lumen-test: backend modules + motion sync; `lumen-web` / `lumen-worker` restart only

## Success criteria (honest)

| Criterion | Status |
| --- | --- |
| Director intent in structured plan | **Pass** |
| Remotion enforces min speaker PIP | **Pass** (layout constants + pipRect) |
| Validate/repair before render | **Pass** (unit + plan stamp) |
| Final video passes Hypit-defect patterns | **N/A for Hypit** until Remotion is default ordinary path; Remotion 20s preview shows improved speaker scale |
| Caption/transcript completeness | **Partial** — pack strings remain |
