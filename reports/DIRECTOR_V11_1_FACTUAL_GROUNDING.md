# Director V11.1 — Factual Grounding & Semantic Business Motion

**Date:** 2026-10-13  
**Branch:** `feat/media-library-cleanup-v1`  
**Test project:** `director_v5_original1` (origin1) — **not** project e  
**Flags:** `PREMIUM_3D_MODE=off`, no paid media, no RunPod restart

## Problem

V11 correctly scrubbed immigration contamination, but:

1. Project transcript stopped at 20s — missing spoken **≥3 shareholders** and **&lt;49%** foreign capital.
2. Remotion `BigFigure` defaulted to **`value = 2`**, inventing a headcount the source never stated.
3. No source-to-visual provenance on factual claims; no deterministic business motion for ownership / capital / control.

## Fix

| Layer | Change |
|-------|--------|
| Transcript | `data/director_v5_original1/source.transcript.json` — 13 bilingual segments aligned to ZH ASR timing |
| Backend | `backend/director_v11_1.py` — extract spoken facts, stamp `businessMotion` + provenance, factual gate |
| V11 lexicon | Match `至少三名股东` / `不超过49` / control-lock ZH |
| Remotion | `motion/src/preview/BusinessMotion.tsx` — 8 generic components (not Thailand-hardcoded) |
| Captions | `caption_phrases.py` — longer mobile phrases; block dangling `at`; no cross-pause merges |
| BigFigure | No default `2`; render only when `spokenNumber` evidence exists |
| Wire | `ordinary_director_render.py`, `director_v3.py`, `remotion_engine` pass-through |

## Shareholder verdict

**At least three shareholders** — source quote:

> 普通泰国有限公司通常需要至少三名股东  
> Ordinary Thai companies usually need at least three shareholders  
> (`seg_006`, 22.66–26.06s)

**Do not show “2 Shareholders.”**

## Artifacts

- `output/director-v11-1/director-v11-1-origin1-60s.mp4` (60.05s)
- `source-fact-validation.json` · `business-motion-usage.json` · `caption-qa.json`
- `V11_V11-1_COMPARISON.md`
- Desktop: `~/Desktop/director-v11-1-origin1-60s.mp4`

## Tests

```text
pytest backend/tests/test_director_v11_1.py \
  backend/tests/test_director_v11.py \
  backend/tests/test_caption_phrases.py \
  backend/tests/test_director_shot_plan.py \
  backend/tests/test_locale_consistency.py
```

## Pipeline order

```text
… → director_v11 semantic intelligence
  → director_v11_1 factual business motion   ← NEW
  → fill_media / v9 / premium3d(off)
  → Remotion (BusinessMotion + captions)
```

## Rollback

Omit `director_v11_1.apply_factual_business_motion`; V11 semantic scrub remains.
