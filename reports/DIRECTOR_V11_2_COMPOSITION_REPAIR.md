# Director V11.2 — Factual consistency & composition repair

**Date:** 2026-10-13  
**Branch:** `feat/media-library-cleanup-v1`  
**Flags:** `PREMIUM_3D_MODE=off`, no paid media, no RunPod restart  
**Source project:** `director_v5_original1` (origin1), not project e

## Problem

V11.1 removed BigFigure’s invented default `2`, but the finished origin1 MP4 still showed both **≥3 Shareholders** and **2 Shareholders**.

## Root cause

`CleanSteps` painted `{slot + 1}` immediately before the investment step label. The V11 investment steps pack used `Shareholders` as step index 1 → on-screen **“2 Shareholders”**. Separate from BigFigure.

## Fixes

| Area | Change |
| --- | --- |
| Steps pack | Capital / **Structure** / Control (RU/ZH equivalents) |
| CleanSteps | `Step N` on its own line; label below |
| `director_v11_2.py` | Scrub fake headcount labels; face-safe `placement` + `mediaSide` |
| BusinessMotion | Side rail / media column opposite speaker; transparent nodes; no `Math.max(2)` floor; simultaneous reveal when `showCount` |
| Captions | Softer plate (~0.55), 56–84px |
| Floats | Skip decorative `FloatingForeground` while BusinessMotion is mounted |

## Deliverables

- `output/director-v11-2/director-v11-2-origin1-60s.mp4`
- `output/director-v11-2/factual-validation.json`
- `output/director-v11-2/face-collision-report.json`
- `output/director-v11-2/caption-qa.json`
- `output/director-v11-2/V11_1_V11_2_COMPARISON.md`
- Desktop: `~/Desktop/director-v11-2-origin1-60s.mp4`

## Tests

`backend/tests/test_director_v11_1.py`, `backend/tests/test_director_v11_2.py` (EN/RU/ZH step scrub).
