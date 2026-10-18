# Reference comparison

Reference B is `/Users/akatruk_macbook/Desktop/video_2026-10-14_15-41-20.mp4`. Tonight's probe: 480×848, 174.433s. The research report's sha256 is `e6e4662f41daa30ff07ef3c0f65bf61fd289d3a1bfd59e9197605b1d629fbde1`. The file was opened at 52s. It was not re-hashed tonight.

Sheet: `output/webstudio-editorial-proofs/comparison-sheet.jpg`

Left: reference B at 52s. Middle: original3 list proof at 31.2s (`代价` active). Right: original2 range proof at 2.0s (`1.5万` / `2.5万`).

| Criterion | Reference B at 52s | List proof | Range proof |
| --- | --- | --- | --- |
| Object share of the frame | Prior measurement in `reports/GOLD_STANDARD_V2_REFERENCE_ANALYSIS.md`: the page at 52s is 372×524 px, 77.5% of the 480px width. Tonight's frame still shows that page. | Dark column from the left edge at mid-frame is 552/1080 = 51.1% (`o3-31.2.jpg`). Layout constants: speaker column 500px, media column 504px (46.7%). | Same split. A dark-pixel run stops on the light glyphs, so that method is not the column width. The type sits in the left column. |
| Readability | Row 01 is a highlighted line on a page, readable at phone size. | The active label is large type. Dim rows stay readable. | `1.5万` and `2.5万` are large. `泰国` is smaller, under the bar. |
| Hierarchy | Page is the subject. Speaker is a small inset. Caption is under the page. | List column is the subject. Speaker is the right-hand window, face clear. Caption sits on the lower part of the speaker window, not on the list and not on the eyes. | Same split. Caption sits on the speaker's torso. |
| Change with speech | The highlight moves down a fixed page. Not re-timed tonight. | Rows appear at the naming line and the highlight ends when that line ends. See `timing-original3.csv`. | Each range replaces the previous one at the next spoken band. The gap at 10s has no range. |
| State change | One page, one moving highlight. | Revealed rows stay dim. The current row is the only filled mark. | The old band is gone, not dimmed, when the next sentence starts. |
| Noise | Page, highlight, caption, inset. | Empty black in the column before the first row and around a single row. No doorway, no consult couple, no 步骤 counter. | No equity chart, no doorway, no skyline. The unit string is the ASR token (`泰国`, `泰诸`), which looks unfinished next to the reference page. |

The proofs use the split that already exists in `speaker_visual`. They do not reach the reference page's 78% width. They do put the explanation in the larger column and keep the face visible.
