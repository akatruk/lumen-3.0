# V11.1 → V11.2 comparison (origin1 / director_v5_original1)

**Flags:** `PREMIUM_3D_MODE=off`, no RunPod / paid media  
**Source:** `director_v5_original1` (NOT project e)

| | V11.1 | V11.2 |
| --- | --- | --- |
| MP4 | `output/director-v11-1/director-v11-1-origin1-60s.mp4` | `output/director-v11-2/director-v11-2-origin1-60s.mp4` |
| Desktop | `~/Desktop/director-v11-1-origin1-60s.mp4` | `~/Desktop/director-v11-2-origin1-60s.mp4` |
| Duration | ~60.05s | ~60.05s |
| Shareholder claim | `≥3 Shareholders` (seg_006) + **on-screen “2 Shareholders”** from CleanSteps | `≥3 Shareholders` only; steps are Capital / **Structure** / Control |
| Face overlays | Shareholder diagram centered over speaker face on split-right | Diagram in **left media column** (opposite speaker); fullscreen → **left side rail** |
| Captions | dark plate opacity ~0.72, min 64px | softer plate ~0.55, min 56 / max 84 |
| Black boxes | opaque Formation-path stack + Credit/Risk plates over center | lighter fills; process rows on side rail; Credit/Risk upper-left |

## Where “2 Shareholders” still came from (V11.1)

Not BigFigure (fixed in V11.1). Remaining source:

1. **Investment steps pack** stamped `['Capital', 'Shareholders', 'Control']` onto the steps scene.
2. **CleanSteps** rendered `{slot+1}` adjacent to `{label}` → accent **2** + **Shareholders** = literal **“2 Shareholders”**.
3. Secondary ambiguity: staggered shareholder-node reveal + `Math.max(2,…)` topology floor could flash two nodes before the third.

V11.2 scrub: Structure pack + `Step N` on its own line + simultaneous node reveal when `showCount` + face-safe rails.

## Spoken fact (unchanged)

> Ordinary Thai companies usually need at least three shareholders  
> 普通泰国有限公司通常需要至少三名股东  
> `seg_006` · 22.66–26.06s · card `≥3 Shareholders`

## Gate results

| Gate | Result |
| --- | --- |
| factual-validation.json | `ok: true`, spokenCount 3, rejected invented two |
| face-collision-report.json | overlays stamped `media_column`/`side_rail` + `mediaSide` opposite speaker |
| caption-qa.json | 28 captions, source_transcript, soft soft backing |
| Unit tests RU/EN/ZH | `test_director_v11_1` + `test_director_v11_2` pass |

## Frame QA (watched)

- t14 Formation path: left rail, labels Capital/Structure/Control (no Shareholders headcount)
- t18–t24 Shareholders diagram: left column, speaker face clear on right; caption “at least three”
- Plan blob: `"2 Shareholders"` absent; `"≥3 Shareholders"` present
