# V7 vs V8 comparison

| | V7 20s | V8 60s |
| --- | --- | --- |
| Duration | 20.05s | **60.05s** |
| Scenes / beats | 6 | **10** (`long60`) |
| shotPlanVersion | v7 | **v8** |
| Semantic motion webm staged+rendered | 0 | **10 / 10** (`semanticMotionAudit.pass`) |
| Motion families (webm) | n/a (layout families only) | **mobility, document, folder, compare, shield** |
| Unique layouts | 6 | **9** |
| Unique backgrounds | (few) | **4** distinct B-roll plates |
| maxSplitStreak | 1 | **1** |
| Captions | ~10 RU | **20 RU** (EN glitch filtered) |
| languageValidation | ok | ok |
| Form | short preview | **full edit** — authentic source through ~60s |

## First-20s overlap (same source «e»)

Both open with punch-in / close-up + kinetic «Планируете переезд».  
V7 stays a 6-beat short with layout/choreography variety but no staged library webm.  
V8 stages `pm_scene_mobility_001` / document plates on hook→problem and continues past 20s into residency / consult / beside / steps / proof / payoff / return with real speech — **not a looped or stretched 20s**.

## Fair read

Duration alone is not the win. Over the shared opening, V8 adds resolved semantic motion clips at speaker-safe cover size. Over the full minute, V8 keeps maxSplitStreak=1, 9 layouts, 5 webm motion families, and 20 locale-clean captions.

## Evidence

- `director-v8-e-preview-60s.mp4` (1080×1920 @ 30fps, H.264 + AAC)
- `motion-usage-report.json` · `asset-selection-report.json` · `caption-qa.json`
- `v8-contact-sheet.jpg` · Desktop: `~/Desktop/director-v8-e-preview-60s.mp4`
