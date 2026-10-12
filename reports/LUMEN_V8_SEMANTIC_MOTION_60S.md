# Lumen V8 — Semantic Motion Activation (60s)

**Branch:** `feat/media-library-cleanup-v1`  
**Preview:** `output/director-v8/director-v8-e-preview-60s.mp4`  
**Desktop:** `~/Desktop/director-v8-e-preview-60s.mp4`  
**Git SHA:** `1f5c5a3db020661b71ddc4e2d1d417053b428802`

## Result

| Metric | Value |
| --- | --- |
| Duration | **60.05s** (58–62 ✓) |
| Resolution | 1080×1920 @ 30fps H.264 + AAC |
| Scenes | **10** (`long60`) |
| shotPlanVersion | **v8** |
| Unique layouts | **9** |
| Unique backgrounds | **4** |
| Semantic motion staged+resolved | **10 / 10** |
| Unique motion families (webm) | **5** — mobility, document, folder, compare, shield |
| maxSplitStreak | **1** (pass) |
| Captions | **20** RU; empty plates = 0 |
| languageValidation | ok (`ru-RU`) |
| directorMode | heuristic (RunPod not resumed) |
| Render time | ~4–4.5 min local |

## Story beats (source-faithful)

| Beat | Purpose | Layout | Motion family |
| --- | --- | --- | --- |
| hook | Strong hook | punch-in | mobility |
| context | Why it matters | foreground + door B-roll | mobility |
| problem | Tension | close-up | document |
| residency | Insight | split-right + approval plate | folder |
| consult | Explanation | with media + docs | compare |
| beside | Family / protection | split-left | shield |
| steps | Process | diagram | folder |
| proof | Visual proof | consult B-roll | folder |
| payoff | Conclusion | medium | mobility |
| return | Takeaway | fullscreen | mobility |

## Implementation

- `backend/director_v8.py` — 10-beat expansion, locale transcript filter, `MOTION_BINDINGS`, staging into Remotion `public/picked/`
- `backend/director_v3.py` / `remotion_engine.py` / `scripts/ordinary_director_render.py` — ≥45s → long60 expand + stage
- `motion/src/preview/DirectorV3.tsx` — dynamic N-beat `SceneRouter` + enlarged `SemanticMotionClip` (~520px cover)

## Source

Authentic project «e» (~107s available). First ~60s of speech used; EN glitch segment dropped by locale filter. **Not** a stretched 20s loop.

## Comparison

`output/director-v8/V7_V8_COMPARISON.md`

## Audio

Speech dominant (source-edit @ ~1.6); licensed bed ducked ~0.34 with fades. See `output/director-v8/audio-qa.md`.

## Deploy

lumen-test · `FAST_PROJECT_CREATION_ENABLED=1` · `REMOTION_ENGINE_ENABLED=1` · no RunPod restart · media volume preserved · strom-v2 untouched

## Tests

`pytest backend/tests/test_director_v8.py` — pass

## Remaining limitations

- B-roll stills can still cluster thematically (4 unique plates)
- Folder webm reused on steps/proof — acceptable semantically, not maximal diversity
- Full EN/ZH 60s needs target-language alignment transcripts
- Heuristic Director (not RunPod LLM) for this render
