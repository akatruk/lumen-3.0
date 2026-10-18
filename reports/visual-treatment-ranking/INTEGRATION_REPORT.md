# Visual treatment ranking

Branch: `experiment/visual-treatment-ranking`
Base: `607eed9f9322406c63e4ada46b2ff5c59d418944`
Not merged. Not pushed. Not deployed.

`visual_treatment_mode` defaults to `off`. Existing jobs are unchanged. `shadow` attaches `treatmentRanking` and keeps the same scene list. `apply` changes `layout` and `mediaSide` only when a different existing layout passes the gates. It does not change steps, evidence, lifecycle, captions, language, or audio.

## Layouts that already render

`motion/src/semantic/layouts.ts`, used by `SemanticMotion` inside `DirectorV3Preview`. Canvas 1080×1920.

| layout | graphic box | speaker | gate |
|---|---|---|---|
| `speaker_visual` | 504×1214 at x=28 (46.7% of width) | 500×1424 column | passes |
| `full_frame` | 592×1220 at x=64 | PIP 360×480, top=1072 | rejected: PIP overlaps the caption band (top 1390) |
| `overlay` | 936×298 under the face band | full frame | rejected for a 3-step timeline: height 298 < 300px step stack |

No fourth layout exists. V16's split uses a 640px speaker and a smaller diagram, and its flag stays off.

## Baselines

| file | sha256 | duration |
|---|---|---|
| `output/webstudio-editorial-proofs/original3-list-proof.mp4` | `4c7cd62aa93e2a8902f023cc5b147b20ca7116f3be84a40f5230d646794b8a55` | 33.920s |
| `output/webstudio-editorial-proofs/original2-range-proof.mp4` | `703a28d4adc542f3ae8452e722f3dcb4de77ec2fa3d9d8635eab2ec6764abc2d` | 20.053s |
| original1 optimizer A | `ab89b049678fb597ac4b89ac4f3e732f897fa1845e431c03eed4cf24fd00e84c` | 36.459s |

original3 excerpt source `c3feafb8fe2b7dc3c84a57ff29e1057442753e052ee0ad819c727f6a9c68cb7c`. Plan `gen_631280367`, locale zh-CN, `motion.process_timeline.v1`, steps 使用场景 / 家庭结构 / 代价, display 0–33.432s, layout `speaker_visual`.

original2 excerpt source `428aa51a0e26059f2fade7fb54eb859d4f67808e2c72e81d5c99d455f0693f7c`. Plan `gen_856109875`.

## Ranking

Three candidates per scene. Hard rejects: missing source labels, invented currency, caption/face/speaker overlap, graphic box smaller than the component's painted size. Among the rest, a layout needs 48px of width slack and then the larger speaker wins. Area is not a score.

original3 timeline: only `speaker_visual` survives. `full_frame` fails the caption gate. `overlay` fails the step-stack gate. `apply` does not change the plan. Rank time 0.045ms.

original2 numeric ranges: same result. The 480px figures fit the 504px column with 24px of slack, which is under the comfort margin, but `full_frame` is still illegal because of the caption, so the column stays. Rank time 0.081ms. No second render. The range proof already shows that column.

## Render

Same plan, same speaker, same captions, same component. A is the current layout. B forces `full_frame` so the rejected candidate is visible. C was not rendered.

| | path | sha256 | duration | audio md5 |
|---|---|---|---|---|
| A | `output/visual-treatment-ranking/variant-a.mp4` | `b20140ca72abaa81519c68aafa2fb8e8568591a57a2ff65a6066e097584f5096` | 34.048s | `fe661600593927118c37c0b5298ff74e` |
| B | `output/visual-treatment-ranking/variant-b.mp4` | `aa0bda9878d24307f5beb0c6afb5acc6173f50139abefd14dae4fd421a6f7508` | 34.048s | `fe661600593927118c37c0b5298ff74e` |

Both 1080×1920. Wall clock for the pair: 170s. Contact sheet: `output/visual-treatment-ranking/comparison-sheet.jpg`. Frames at 3.0s, 16.5s, 30.5s, 33.0s.

Measured on A at y=900: the dark graphic runs to x=552, 552/1080 = 51.1%. That matches the earlier list-proof measurement. The type does not get wider in B. `ProcessTimeline` paints a 440px label. B leaves that label on an empty field and puts the speaker in a PIP that covers the caption at 30.5s (`第三层叫代价`).

Selected treatment: `speaker_visual`. It is what the resolver already emits. B is not selected.

## Tests

48 passed: `test_visual_treatment_ranking.py`, `test_visual_quality_optimizer.py`, `test_director_v14.py`.

## Production

Not ready. Turning `apply` on does not change these two plans, because the only larger layout fails caption safety. A wider graphic needs a layout the renderer does not have: more than 504px for the diagram without parking the speaker on the caption. That is the gap. Do not enable the mode to chase width.

MP4s and frames stay local. They are not in the commit.
