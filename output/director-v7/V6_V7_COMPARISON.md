# V6 vs V7 comparison — project «e» 20s

| Metric | V6 | V7 |
| --- | --- | --- |
| uniqueLayouts | 4 | **6** |
| uniqueMotionFamilies | ~4 treatments | **6** (`camera+kinetic`, `media+mask`, `broll`, `info_reveal`, `infographic`, `camera`) |
| consecutive split streak | up to 2 | **1** (antiRepetition pass) |
| return framing | forced split | **fullscreen medium** |
| hook | close-up + headline | **punch-in + kinetic headline** |
| cards | 3 stacked dense panels | **progressive_one** hero cards |
| captions | 12, some dangling «с» | **10**, no empty plates, no `<3w` orphans in QA |
| shotPlanVersion | absent | **v7** |
| choreography actions | none stamped | **18** |
| bed level | ~0.26 | **~0.34** |
| languageValidation | ok | ok |

## Evidence
- Plan: `director-v7-scene-plan.json`
- Motion: `motion-usage-report.json` (`pass: true`)
- Captions: `caption-qa.json` (`emptyPlates: []`)
- Contact: `v7-contact-sheet.jpg`
- Desktop: `~/Desktop/director-v7-e-preview-20s.mp4`
