# Visual QA

Objective checks are separate from the look of the frame.

## Objective

| check | A `speaker_visual` | B `full_frame` (rejected) |
|---|---|---|
| Frame | 1080×1920 | 1080×1920 |
| Graphic vs caption band | 504×1214 ends at y=1374; caption band starts at y=1390 | motion rect clears the band; the PIP does not |
| PIP vs caption | no PIP | PIP top 1072, height 480, overlaps the band from y=1390 |
| Labels in the quote | 使用场景, 家庭结构, 代价 | same |
| Audio md5 | `fe661600593927118c37c0b5298ff74e` | same |
| Duration | 34.048s | 34.048s |
| Empty field | column is filled by the type | label stays ~440px wide; the rest of the dark field is empty |

Measured dark run on `a-3.png` at y=900 ends at x=552 (51.1% of 1080).

## Frames

Times are seconds in both files. A is left, B is right, in `pair-3.png`, `pair-16_5.png`, `pair-30_5.png`, `pair-33.png`.

- 3.0s. First step `使用场景` is lit. Caption `第一层叫使用场景`. A: speaker column, face clear of the type. B: same words, speaker PIP bottom right, caption still clear of the face.
- 16.5s. `使用场景` is dim. `家庭结构` has not lit yet (it reveals at 16.52s). Both sides match that timing.
- 30.5s. `代价` is lit. Caption `第三层叫代价`. On B the PIP covers the right side of that caption.
- 33.0s. Hold. Caption `这里不只是申请费`. On B the PIP sits on the right end of the caption plate. The face in the PIP is visible. The type is the same size as A.

## Judgment

B is not an improvement. The graphic is not larger in any way the viewer can read, and the caption collides with the speaker window. A keeps the face large and the caption on the speaker column. Neither frame is a 77% graphic. The renderer has no layout that does that without this collision.
