# Director V7 — Premium Motion Choreography

**Branch:** `feat/media-library-cleanup-v1`  
**Preview:** `output/director-v7/director-v7-e-preview-20s.mp4`  
**Desktop:** `~/Desktop/director-v7-e-preview-20s.mp4`  
**SHA:** _(filled after commit)_

## Changes
- `backend/director_shot_plan.py` — per-beat shot plans, choreography, keywords≠captions, anti-repetition
- Wired through `director_semantics.enrich_plan_from_transcript`
- Caption engine: no empty plates, no dangling prepositions, speech-window timing
- Remotion: progressive hero cards, caption lifecycle, louder bed duck
- Tests: `test_director_shot_plan.py` (+ caption/locale suites)

## Gates
- antiRepetition.pass
- motionUsage.pass (6 unique layouts, 6 motion families)
- languageValidation.ok
- empty caption plates = 0

## Deploy
lumen-test · FAST_PROJECT_CREATION=1 · REMOTION=1 · no RunPod restart

## Remaining
- Concept viz still can stack mid-hook
- Caption mid-clause density can improve further for long RU sentences
- Transitions remain mostly cut/crossfade (intentional, not random)
