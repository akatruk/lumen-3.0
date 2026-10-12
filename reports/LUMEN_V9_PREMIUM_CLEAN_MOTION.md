# Lumen V9 — Premium Clean Motion

**Branch:** `feat/media-library-cleanup-v1`  
**Preview:** `output/director-v9/director-v9-e-preview-60s.mp4`  
**Desktop:** `~/Desktop/director-v9-e-preview-60s.mp4`  
**Git SHA:** _(filled after commit)_  
**Reference:** `output/director-v8/director-v8-e-preview-60s.mp4` (user rated 6/10)

## Result

| Metric | Value |
| --- | --- |
| Duration | **60.05s** |
| shotPlanVersion | **v9** |
| compositionPolicy | **v9_clean** |
| Opaque motion boxes | **0** |
| Transparent float objects | **3** (suitcase, passport, pin) |
| compositionAudit.pass | **true** |
| Caption phrases | **12** (loop deduped) |
| Concept overlays | **off** |
| Hero globe | **off** |
| Steps | speaker + progressive type (no card wall) |

## What changed

Root cause of V8 clutter: Remotion wrapped **yuv420p** (non-alpha) webm in a dark bordered shelf → black rectangles over the speaker.

V9:

1. `backend/director_v9.py` — `simplifySceneComposition`, complexity budget, transparent SVG/PNG bindings, caption loop dedupe
2. Remotion `FloatingForeground` — no container chrome
3. Soft captions + transparent kinetic type
4. Steps = speaker-led progressive labels
5. `conceptTriggers=false`, `heroObject=null` under v9_clean

## Comparison

`output/director-v9/V8_V9_COMPARISON.md`

## Deploy

lumen-test · `FAST_PROJECT_CREATION_ENABLED=1` · `REMOTION_ENGINE_ENABLED=1` · no RunPod · volume preserved

## Remaining

- Split layouts still use rounded panels with some black canvas margin (geometry, not motion boxes)
- Beside still uses one progressive card (allowed for structured criteria)
- Full EN/ZH 60s needs target alignment transcripts
