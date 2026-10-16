# Semantic motion design

Branch `experiment/semantic-motion-design`. Design commit `8d96789bf66233af83ed9eda023b7a8a4b59449e`. Not merged. Not deployed. `visual_treatment_mode` still defaults off.

## What changed

`motion.process_timeline.v1` draws the spoken labels on a vertical stem. The current label is the large one. Earlier labels stay visible and quieter. Rows appear at their existing `at` times. The words are not renamed to 步骤.

`motion.numeric_range.v1` places the two spoken ends on a stem that draws from low to high inside the same beat. A verified unit is painted only when `range.unit` is set. The gray progress track is gone.

`Label` accepts optional `align` and `maxLines`. Existing callers stay centered.

## What stayed

Payload fields, evidence timestamps, captions, speaker crop, layouts, ranking, optimizer, director. Kind labels `月薪` / `每天` / `金额`.

## Files

| file | duration | sha256 | audio md5 |
| --- | --- | --- | --- |
| `output/semantic-motion-design/original3-before.mp4` | 34.048s | `8a27ae7efa4f278db06db95f0db6d10fec7164ebb9fbcb135a3a526275754e24` | `fe661600593927118c37c0b5298ff74e` |
| `output/semantic-motion-design/original3-after.mp4` | 34.048s | `ed73a0cb22e1a020e40bdbbee4b748738ffdc816998fabf47c64f4b9832c025a` | `fe661600593927118c37c0b5298ff74e` |
| `output/semantic-motion-design/original2-before.mp4` | 33.045s | `f0ed2956562c1e1a0acb6b28fa2546c73b45c82315838e824d580ce33860dbc3` | `aa950a4f5dfd31ed17cb58a6132d53a4` |
| `output/semantic-motion-design/original2-after.mp4` | 33.045s | `721d4e7eb372d19a6f76259dbf4ebd8938664aec2ae85ee834708e73d4610a91` | `aa950a4f5dfd31ed17cb58a6132d53a4` |

Before files are copies of the previous editorial renders. Sheet: `output/semantic-motion-design/comparison-sheet.jpg`.

Plans: original3 `gen_631280367`, original2 `gen_856109875`. Layout on the A/B pair: `editorial_focus`.

## Evidence

Timeline labels in the after frames: 使用场景, 家庭结构, 代价. Range strings: 1.5万–2.5万 with no unit; 400–1200 with 人民币 and 每天. Caption on the salary line still says 泰国. No invented currency.

## Safety

Captions readable and below the PIP. Speaker face in frame on both editorial sources and on the split-column 8s check. Graphic timing follows the existing step clocks and the scene exit already in `SemanticMotion`.

## Type

zh-CN is what the four files show. The wrap test covers a long Chinese line (punctuation stays on the previous character), a long Russian word (kept whole, scaled into the 504px column), and a two-line English phrase. No font files added. No EN/RU video.

## Performance

Two after renders: 182.0 s wall. `/usr/bin/time -l` on the parent Python process: maximum resident set size 1,103,413,248 bytes. Remotion is a child process, so that figure is not the renderer peak. Output 1080×1920, 30 fps, durations above. No per-frame component probe exists in this path.

## Tests

7 new design/range tests passed, 8 layout tests passed, 56 Python tests passed. See `REGRESSION_RESULTS.md`.

## Limits

The editorial frame still has a large dark field around a short three-word stack. The stem makes the relationship visible. It does not turn the black into content. `business_comparison` was not part of this pass. Not turned on by default. Not Web Studio verified through HTTP.

## Readiness

Do not enable globally. The range graphic is the clearer of the two. The timeline is better than the single oversized word and is still sparse on a 952×582 stage.
