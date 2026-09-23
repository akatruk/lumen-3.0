# Manual QA — effect timing inside a shot

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a lower plate that appears after the opening of a reference shot turns the owned effect on at that fraction. A plate that is present from the first frame stays on for the whole slot, with hold `0`. The word blur still blurs the whole slot. A gated blur leaves the opening sharp and the later frames soft. A kinetic line that is delayed starts at that time. Reference pixels stay out of the file.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Measure a 1.8 second shot whose lower plate appears at 1.0 second, and a flat 1.2 second shot. | The late plate is `lower` with hold between 0.35 and 0.7. The flat shot has hold `0` and `lower` false. |
| 3 | Build one edit from a measured hold of `0.5` with a lower plate, and one from the word blur with no measurement. | The measured clip has `effect_at` `0.5` and `lower` true. The word-only clip has blur `2` and `effect_at` `0`. |
| 4 | Render a 1.6 second slot with blur `8` starting at `effect_at` `0.5`, and write a kinetic caption for `Visa days` beginning at 0.5 seconds. | The file duration stays about 1.6 seconds. The frame at 0.2 seconds has stronger edges than the frame at 1.2 seconds. The first caption line starts at `0:00:00.50`. |
