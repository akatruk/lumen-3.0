# Visual QA — editorial_focus

Frames are 1080×1920 grabs from the four MP4s. Contact sheet: `output/responsive-editorial-layout/comparison-sheet.jpg`.

## original3 ProcessTimeline

Source plan `gen_631280367`. Steps 使用场景 / 家庭结构 / 代价. Same transcript, captions, and audio as the baseline.

| time | role | speaker_visual | editorial_focus |
| --- | --- | --- | --- |
| 3.0s | entry, first label | label ink 79px tall in the 504px column | label ink 121px tall, width 571 |
| 16.5s | second step | caption and speaker column | second label revealed, PIP clear of captions |
| 30.5s | 代价 fully on | label ink 79×161 | label ink 120×245 |
| 33.0s | hold | caption 这里不只是申请费 | same caption, PIP already ended at y=1370 |

Caption cues still fade in over 8 frames at each phrase start (existing `Caption` opacity). Frame 72 (2.40s) of the editorial file is the first frame of 第一层叫使用场景 and is dark; frame 80 is the readable plate. That fade is the caption component, not a layout collision.

The active word is larger. The quiet steps stay small and left-aligned. The right side of the graphic row and the area left of the PIP are empty `#12110F`. The speaker is a 360×640 portrait. Face and mic are in frame. The split-column baseline shows more of the body.

## original2 NumericRange

| time | speaker_visual | editorial_focus |
| --- | --- | --- |
| 2.0s | 1.5万 / 2.5万 ink 73px, bar 504px, no unit | ink 141px, bar 952px, no unit. Caption still says 泰国. No 泰铢. |
| 6.2s | 3千–4千 人民币 | same labels, larger figures, unit kept |
| 30.5s | 400 / 1200 ink 63px, bar 504px, 人民币 | ink 121px, bar 952px, 人民币 |

Digits about doubled. The bar is the full inset width. The speaker face is inside the PIP. The hand is cut by the box the same way cover-crop cuts a gesture in a 9:16 window. Captions sit at y≈1487–1530, 117px below the PIP.

## Verdict

Numeric range is a real readability gain. The timeline word is larger and still does not fill the 952×582 box. The black field is the remaining weakness. Do not treat the wider box as a better picture by itself.
