# Director V11 — Semantic Intelligence & Topic-Aware Visual Storytelling

**Date:** 2026-10-13  
**Branch:** `feat/media-library-cleanup-v1`  
**Test project:** `director_v5_original1` (origin1 / original1) — **not** project e  
**Flags:** `FAST_PROJECT_CREATION=1`, `PREMIUM_3D_MODE=off`, no RunPod / paid providers

## Problem

origin1 speech is about **foreign / Chinese investment companies, capital investment, shareholder structure, Thailand company formation, foreign ownership, control** — but Director injected **immigration / relocation** criteria cards and B-roll (`family home doorway relocation`, “Family who travels with you”).

## Root cause (contamination path)

| Layer | File:line (pre-fix) | Failure |
|-------|----------------------|---------|
| Hardcoded long60 beats | `backend/director_v8.py` `LONG_BEATS` (~L36–65) | Every ≥45s plan got `keywordPref=('relocation','residency')` and queries like `family home doorway relocation` / `residence permit application desk` **regardless of transcript** |
| Stock criteria cards | `backend/director_semantics.py` `_criteria_for` (~L102–109) | Always returned Goals/Family/Budget immigration pack; comment explicitly kept immigration cards on investment/China speech |
| Keyword lexicon | `backend/director_shot_plan.py` `_KEYWORD_RULES` (~L134–146) | Only immigration needles (`переезд`, `паспорт`, …) — investment speech produced **empty** keywords, so beat defaults dominated |
| Remotion fallback | `motion/src/preview/portraitLayouts.ts` `criteriaCardsFor` | Immigration cards if plan omitted speech-backed cards |
| V9 float bindings | `backend/director_v9.py` `OBJECT_BINDINGS` | Relocation → suitcase/pin once keywordPref leaked |

**Not** caused by premium 3D (V10.2 correctly refused passport/suitcase on origin1).

## Fix — Director V11

New module: `backend/director_v11.py`

1. **`build_semantic_map(transcript)`** — stable concept IDs per spoken segment with evidence + domain scores  
2. **`detect_topic_domain`** — `investment` | `immigration` | `mixed` | `generic`  
3. **`apply_semantic_intelligence`** — after V9 composition, before premium 3D:  
   - replace criteria/steps with topic packs (RU/EN/ZH)  
   - scrub immigration queries / motion / floats / passport hero when domain is investment  
   - stamp `semanticConcepts` with segment provenance  
4. **`validate_semantic_alignment`** — fail closed on mismatched cards/assets  
5. **`export_semantic_artifacts`** — writes map / selection / validation JSON

Also patched:

- `director_v8.expand_plan_for_duration` — topic-aware beat prefs; no immigration hero on investment  
- `director_semantics` — topic-aware `_criteria_for` / query triggers for investment & Thailand  
- `director_shot_plan` — investment/shareholder/capital/Thailand keyword rules  
- `director_v9.OBJECT_BINDINGS` — corporate keyword → transparent icons  
- Wire: `scripts/ordinary_director_render.py`, `backend/director_v3.py`

## Provenance rule

Every selected visual concept must map to a transcript segment. No invented percentages or legal claims. Mixed-topic speech keeps both domains with per-scene evidence gating.

## Verification (origin1)

| Artifact | Path |
|----------|------|
| MP4 | `output/director-v11/origin1-60s.mp4` |
| Semantic map | `output/director-v11/semantic-map.json` |
| Asset selection | `output/director-v11/asset-selection.json` |
| Validation | `output/director-v11/semantic-validation.json` |
| Baseline compare | `output/cross-project-origin1/baseline-v9.mp4` |

- Duration: **~60.05s** (accept band 58–62s)  
- Domain: **investment**  
- Concepts: foreign/chinese investment company, capital investment, government leadership, deferred payment, shareholder responsibility, capital judgment, Thailand structure  
- Validation: **ok**, issueCount **0**  
- No relocation / passport / “travels with you” cards  
- Captions: English from transcript (`captionSource` / `captionCount` ≥ 6)  
- 3D: off / empty production_ready — V9-clean composition retained  

### Tests

```text
pytest backend/tests/test_director_v11.py \
  backend/tests/test_director_v8.py \
  backend/tests/test_director_v9.py \
  backend/tests/test_locale_consistency.py \
  backend/tests/test_director_shot_plan.py \
  backend/tests/test_director_v10_experimental.py
# all passed
```

## Pipeline order

```text
enrich_plan_from_transcript
  → director_v8.expand (≥45s → long60, topic-aware)
  → fill_media
  → director_v9 composition
  → director_v11 semantic intelligence   ← NEW
  → fill_media (re-resolve scrubbed queries)
  → director_v9 composition (re-bind floats)
  → director_v10 premium 3D (optional; off here)
  → stage + Remotion
```

## Rollback

Omit `director_v11.apply_semantic_intelligence` in ordinary/director_v3 paths; V9 composition remains the visual baseline. Immigration packs still available when speech evidence is immigration.

## Not done / out of scope

- No new media generated  
- No forced experimental 3D  
- Remotion `criteriaCardsFor` fallback still immigration-shaped for empty plans — production plans must carry V11 cards (enforced on create-video path)
