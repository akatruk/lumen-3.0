# Motion art direction

Branch `experiment/motion-art-direction`. Code commit `32d15ed169bb842055c3763abd4ac0f4401242af`. Not merged. Not deployed. Default drawing is still the stem. `spatial_v1` is opt-in on the scene payload.

## Answers

1. A is a type stack. B is one spatial object. C is a hero word plus a small index, and a range split across two corners.

2. The stills are in `output/motion-art-direction/concept-a|b|c/`. A stays left-weighted. B spans the graphic. C's range does not connect.

3. B. A does not leave the cluster. C loses the relationship between the two numbers.

4. `designProfile: "spatial_v1"` switches the same two components. Anything else keeps the stem.

5. Yes on the complete timeline: the active row is marked and the other two stay in order down the band. The content box at 30.8s grew from 206×229 to 952×485. The filled fraction stayed about 0.025, because the new width is a hairline, not a panel.

6. The range is clearer. 400 and 1200 are the ends of one line, 每天 is in the gap, 人民币 is under the line. The salary frame is 1.5万 and 2.5万 with 月薪 and no unit.

7. The line grows from the low end to the high end inside the existing beat. Timeline rows appear at the existing `at` times and do not move to a new slot when the next row opens.

8. Captions at 3.2s, 16.8s, and 30.8s are the source lines and sit in the bottom band, clear of the PIP.

9. The profile uses `AutoFitText` and the existing font stacks. The wrap test still covers Chinese punctuation, a long Russian word, and a two-line English phrase. The four MP4s are zh-CN only.

10. The range yes. The timeline is a clearer sequence and is still mostly dark ground to the right of four-character words.

11. The hairlines can read as a menu. The right side of each row is empty. The speaker is still the small PIP from `editorial_focus`.

12. No. Studio does not send `designProfile`. A plan that already contains it will render it. That is not a studio control.

13. No.

## Files

| file | duration | sha256 | audio md5 |
| --- | --- | --- | --- |
| `output/motion-art-direction/original3-before.mp4` | 34.048s | `ed73a0cb22e1a020e40bdbbee4b748738ffdc816998fabf47c64f4b9832c025a` | `fe661600593927118c37c0b5298ff74e` |
| `output/motion-art-direction/original3-after.mp4` | 34.048s | `8ebc85270095b4092fe43835c92cc96ad9709abc1c9f9d7bb960e7175dfeb503` | `fe661600593927118c37c0b5298ff74e` |
| `output/motion-art-direction/original2-before.mp4` | 33.045s | `721d4e7eb372d19a6f76259dbf4ebd8938664aec2ae85ee834708e73d4610a91` | `aa950a4f5dfd31ed17cb58a6132d53a4` |
| `output/motion-art-direction/original2-after.mp4` | 33.045s | `4a12908b9865bb9be08935e4d8040415bdbf4811204eb76db73267633f31e842` | `aa950a4f5dfd31ed17cb58a6132d53a4` |

Sheet: `output/motion-art-direction/comparison-sheet.jpg`.

Before files are copies of the previous stem renders. Plans `gen_631280367` and `gen_856109875`. Layout `editorial_focus`. The only plan change on the after renders is `designProfile`.

## Tests and cost

Motion design, numeric labels, and layout tests: 15 passed, including the profile default. Python director, semantic profile, optimizer, and ranking: 56 passed.

Two after renders: 180.6 s wall. Parent Python maximum resident set size 1,100,578,816 bytes. Remotion is a child, so that is not the renderer peak. Output 1080×1920. Same audio hashes as the before files. `rangeMotionAt` is deterministic in the unit test.

## Limits

Not the default. Not Web Studio. The dark field is smaller as a bounding box and just as empty as a fill.
