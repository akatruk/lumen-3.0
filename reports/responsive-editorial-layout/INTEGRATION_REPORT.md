# editorial_focus

Branch `experiment/responsive-editorial-layout`. Not merged. Not deployed. Production flags untouched.

## Answers

1. The full_frame PIP is 360×480 with bottom inset `320+48`, so its top is y=1072 and its bottom is y=1552. The caption band starts at y=1390. `layoutIsSafe` only kept the graphic off that PIP. The PIP itself was allowed to cover the caption.

2. New layout `editorial_focus` in `motion/src/semantic/layouts.ts`, drawn by the existing `V14Stage` speaker (`objectFit: cover`, `objectPosition: center 22%`, zoom 1). Ranking geometry in `backend/visual_treatment_ranking.py` matches it. Wide boxes (`boxWidth >= 700`) use existing type roles: timeline active label `theme.type.hook` (max 128), numeric figures `theme.type.number`. Narrow `speaker_visual` (504px) stays on `title`.

3. Computed graphic `{left:64, top:128, width:952, height:582}` = 88.1% of 1080. A 70% side column leaves 286px, under the 324px speaker floor, so the graphic takes the inset row and the speaker stacks under it. Speaker `{left:656, top:730, width:360, height:640}` (9:16). Rendered PIP on both sources measured the same pixels.

4. Yes, after the existing 8-frame caption fade. Editorial caption ink: original3 at 3.0s `{291,1479,500×60}`; original2 at 30.5s `{246,1487,589×43}`. PIP bottom is 1370. Caption pixels inside the PIP: 0. Chinese punctuation is still the caption component's wrap, not a new line-breaker.

5. Portrait PIP matches the source aspect, so the head is in frame. It is smaller than the 500×1424 split column. No face detector. A landscape or low-res source still uses this box with cover; the ranker does not invent a crop. Minimum speaker gate remains 324×400.

6. ProcessTimeline and NumericRange both rendered through `render_assembly` after `visual_treatment_ranking.apply(mode='apply')`. Timeline active ink 79px → 120px. Range figures 63px → 121px, bar 504px → 952px. `business_comparison` is an eligible candidate in the ranker (two plates, existing component) and was not rendered.

7. zh-CN is what the four files show. ru-RU and en-US are covered by the ranking wrap test and `fontFamilyFor` (CJK: PingFang / Noto Sans SC / Hiragino / Source Han; Latin and Cyrillic: Arial). No EN/RU render. No font binaries added.

8. Yes, when `visual_treatment_mode=apply` and the evidence checks pass. original3: one timeline scene → `editorial_focus`. original2: six range scenes → `editorial_focus`. Empty steps or a unit absent from the quote stay on `speaker_visual` (`changed: false`). `full_frame` stays rejected. Mode `off` does not change the plan.

9. original2 yes: the numbers and the bar are larger, 人民币 stays, 泰国 does not gain a guessed unit, audio matches. original3 the active word is larger and the caption stays clear; the frame is still mostly empty black and the speaker is smaller than the split. That timeline picture is not an upgrade of the whole frame.

10. Empty field left of the PIP and around the short timeline stack. Timeline labels stay left-aligned. Speaker presence is weaker than `speaker_visual`. Comparison was not filmed. EN/RU were not filmed.

11. `pytest` `test_visual_treatment_ranking.py` `test_visual_quality_optimizer.py` `test_director_v14.py` `test_semantic_motion_profile.py`: 56 passed. `node --import tsx --test src/semantic/layouts.test.ts`: 8 passed. No failures suppressed. Peak RSS was not sampled.

12. No. Studio Create Video only reaches this layout when the job payload sets `visual_treatment_mode=apply`. That was not run through the HTTP studio. The renders are `render_assembly` of the ranked plan, which is the Remotion half of the same pipeline.

13. No. Leave `visual_treatment_mode=off`.

## Renders

Isolated sources, not modified. Public copies `editorial-o3.mp4` and `editorial-o2.mp4` deleted after render.

| file | duration | sha256 | audio md5 |
| --- | --- | --- | --- |
| `output/responsive-editorial-layout/original3-baseline.mp4` | 34.048s | `0af3966f65f63122d682b225d3bd709a8952efa2c278ba9ece6b904c7ce0c284` | `fe661600593927118c37c0b5298ff74e` |
| `output/responsive-editorial-layout/original3-editorial-focus.mp4` | 34.048s | `8a27ae7efa4f278db06db95f0db6d10fec7164ebb9fbcb135a3a526275754e24` | `fe661600593927118c37c0b5298ff74e` |
| `output/responsive-editorial-layout/original2-baseline.mp4` | 33.045s | `3e662b7ce59c9b385891284b711a8022c483409c15386affef788cd24a45f41a` | `aa950a4f5dfd31ed17cb58a6132d53a4` |
| `output/responsive-editorial-layout/original2-editorial-focus.mp4` | 33.045s | `f0ed2956562c1e1a0acb6b28fa2546c73b45c82315838e824d580ce33860dbc3` | `aa950a4f5dfd31ed17cb58a6132d53a4` |

Plans: original3 `gen_631280367`, original2 `gen_856109875`.

## Performance

Rank + apply: original3 0.191 ms (rank_plan 0.049 ms), original2 0.685 ms (rank_plan 0.133 ms). No network, no GPU. First four renders 382 s wall. Revised editorial pair 177 s wall. Peak RAM not sampled. Output sizes: 11.0 MB, 5.5 MB, 24.9 MB, 19.2 MB.

## Recommendation

Keep it experimental. `apply` may be used on a numeric-range job. Do not turn it on for every project. The timeline case still needs the type to occupy the box before it is a better default than `speaker_visual`.
