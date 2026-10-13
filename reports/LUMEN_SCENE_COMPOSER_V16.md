# Lumen scene composer V16

**Date:** 2026-10-14
**Flag:** `SCENE_COMPOSER_V16_ENABLED=0` by default. Production picture stays the V11.2 / V14 / V15 path until the flag is turned on for a controlled test.
**Code:** `backend/scene_composer_v16.py`. Runs after V15 and before `stage_backgrounds`. It does not pick new facts and it does not replace Director.

## V14 / V15 gate

Checked before composer code. Not a stop.

| check | result |
| --- | --- |
| components | 15 rows in `media/library/catalogs/semantic_motion_v14.json` |
| variants | `galleryShots()` 15, `galleryShotsV15()` 30, 45 layout variants |
| locales | V14 galleries 37.5s and V15 galleries 75.0s, en/ru/zh, 1080×1920, playable |
| A/B | `output/semantic-motion-v15/origin1-motion-v15.mp4` 60.05s H.264+AAC |
| tests | `test_director_v14.py` and `test_director_v15.py` pass |
| flags | both motion flags default off |
| residual | overlay scrim still meets the caption plate; face stays clear |

## Layouts

The composer stamps `scene.sceneComposition` and, when a diagram exists, `semanticMotionV14.motionRect`, `speakerRect`, `faceRect`, `captionRect`, `enterFrame`, `columnScrim`.

| layout | when | picture |
| --- | --- | --- |
| `motion_overlay` | measured mouth leaves ≥240px above the caption plate | speaker full frame, diagram band under the mouth |
| `motion_beside` | the last two scenes were already `motion_overlay` | same full-frame speaker, diagram card on the lower left |
| `speaker_left` / `speaker_right` | the band would cover the face or the caption | speaker column 640px, diagram in the other column, plate clipped to that column |
| `speaker_fullscreen` | scene has no diagram and the Director framing is a PIP (`proof` on origin1) | speaker full frame, caption on the speaker |

Face box is the upper 42% of the largest warm-chroma skin blob on one downsampled frame (`scale=180:320`). Beige walls fail that test. Origin1 at 4s, 12s, 28s, and 45s measured about x=384–438, y=624–630, 312–330×282–288. If the blob is missing, the plan records `unmeasured_center` and still refuses the 360×480 PIP.

## Recipes

`recipes/scene-composer-v16.json`

| recipe | component | layouts |
| --- | --- | --- |
| speaker + capital flow | `motion.capital_flow.v1` | overlay, beside, speaker left/right |
| speaker + shareholder network | `motion.shareholder_network.v1` | speaker left/right |
| speaker + investment b-roll | `cev6_i2v_inv_glass_002` | speaker left/right |
| speaker + comparison | `motion.business_comparison.v1` | overlay, beside, speaker left/right |
| speaker + timeline | `motion.process_timeline.v1` | speaker left/right, overlay |
| speaker + financial metrics | `motion.financial_metrics.v1` | speaker left/right |

A background is swapped only when its `assetId` contains a banned token for that intent (`facade`, `passport`, `living`, `bedroom`, `harbor`). The replacement is an already-indexed V6 clip. On origin1, `problem` moved to `cev6_i2v_inv_glass_002`. Overlay scenes cover that plate with the speaker, so the swap is in the plan and is visible only if the layout is a split.

## Origin1 A/B

Same source `data/director_v5_original1/source`, en-US transcript, seed 42, duration 60, Remotion `DirectorV3Preview`, `--concurrency=1`. No RunPod.

| | V15 | V16 |
| --- | --- | --- |
| file | `output/semantic-motion-v15/origin1-motion-v15.mp4` | `output/semantic-motion-v16/origin1-motion-v16.mp4` |
| duration | 60.05s | 60.053333s |
| size | 26,419,824 | 33,832,518 |
| sha256 | prefix `0fafae83d3140b8c` | `be145fb3ec3d967729a8581785a9f18952c6d909645ef03ecfd9e23dbd7f5d29` |
| codec | H.264 + AAC, 1080×1920 | H.264 + AAC, 1080×1920 |
| wall | 246s | 245.72s |
| user CPU | 617s | 624.73s |
| peak RSS | 1,030,111,232 | 1,043,628,032 |
| CPU load | ~2.5 cores | 624.73 / 245.72 ≈ 2.54 cores |

V16 selections:

| scene | window | layout | graphic | enterFrame |
| --- | --- | --- | --- | --- |
| problem | 9.22–16.39 | motion_overlay | capital → company | 0 (line starts 8.86, just before the scene) |
| residency | 16.39–26.63 | motion_overlay | ≥3 shareholders | 188 (22.66 − 16.39) |
| consult | 26.63–34.83 | motion_beside | ≤49% | 0 (line starts 26.06) |
| beside | 34.83–40.97 | motion_overlay | China ≠ Thailand | 0 |
| steps | 40.97–46.09 | motion_overlay | bank / permits / visa | 0 |
| proof | 46.09–52.24 | speaker_fullscreen | none | — |

Values stayed `[{value: 49, qualifier: at_most}]`. No 51.

## Frame QA

Frames pulled from the delivered MP4s at 12, 24, 30, 37, 43, and 48 seconds. Near-black pixels (RGB < 18) on a 108×192 sample:

| t | V15 | V16 |
| --- | --- | --- |
| 12 | 2.23% | 2.39% |
| 24 | 63.52% | 2.87% |
| 30 | 0.01% | 2.40% |
| 37 | 60.64% | 2.91% |
| 43 | 3.00% | 3.22% |
| 48 | 0.29% | 2.09% |

What the frames show:

- 12s: full-frame speaker. Capital → Company on a dark scrim under the mouth. Gold connector on the scrim. Caption word "Under" sits below the card. Card luminance breaks at y≈1352; caption backing starts near y≈1440. No overlap.
- 24s: V15 is a black left panel with the speaker cropped to the right. V16 is the full speaker, ≥3 network above the caption "Ordinary Thai companies usually need at least three". Eyes and mouth clear.
- 30s: V16 lower-left card reads ≤49% Foreign capital. Speaker and the pointing hand stay full frame. The card does not cover the face.
- 37s: V15 is a black right panel. V16 is China ≠ Thailand on a band above the caption. Hands sit under the band.
- 43s: Bank accounts / Work permits / Visa applications on the band. Caption is the same sentence, below the band, not through it.
- 48s: V15/V16-before-fix was a small PIP on a harbor skyline with the caption across the window. The delivered V16 frame is the speaker full frame and the caption on the shirt.

Contrast: `columnScrim` forces `sceneTheme: ink` and `connectorBackground: #12110F`, and the card paints `rgba(12,11,10,0.62)`. Gold and white type sit on that plate. `adaptiveLineStyle` still chooses the stroke.

## Tests

- `pytest backend/tests/test_scene_composer_v16.py backend/tests/test_director_v14.py backend/tests/test_director_v15.py` — 25 pass
- `cd motion && npx tsc --noEmit` pass
- `node --import tsx --test src/semantic/layouts.test.ts src/semantic/format.test.ts` — 10 pass

Composer tests cover flag-off (full_frame kept), face/caption clearance, three-peat break, banned facade → `cev6_i2v_inv_glass_002`, beige wall rejected as skin, EN word wrap, zh punctuation kept on the line, 49% not rewritten, PIP scene forced full frame.

## Known limitations

- Face measurement is one skin blob, not landmarks. A very warm background can still miss or widen the box; a miss is labeled `unmeasured_center`.
- Four of five diagram scenes use the lower band. Diversity only moves the third one to a left card. That is intentional: a cropped split was showing `people_review_001` under the 49% ring.
- Scenes that are already full-frame speaker and have no diagram are left alone. `return` stays the existing speaker shot.
- RU and ZH were not re-rendered as origin1 video in this pass. Wrapping is unit-tested. V15 galleries remain the locale picture check for the diagrams.
- The ink scrim still sits close to the caption plate. The 12s frame has a gap of shirt between them.

## Git

Recorded after the implementation commit on `feat/media-library-cleanup-v1`.

## Deployment

Not deployed in this commit. Flag stays off. Do not set `SCENE_COMPOSER_V16_ENABLED` on lumen-fix until this picture is accepted. strom-v2 and RunPod were not touched.
