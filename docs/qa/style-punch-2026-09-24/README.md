# Manual QA — punch-in follows subject size

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a small bright subject is cropped tighter than a subject that already fills the frame. A flat frame stays at zoom 1. Reference pixels are not copied.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | On the deployed code, measure a small bright block, a bright block that fills most of the frame, and a flat color frame. | The small block has a higher zoom than the large block. Both are at least 1. The flat frame has zoom 1 and `y` 0.5. The small block keeps `y` 0.78. |
| 3 | Build one style clip from the small-block picture. | The clip stores that zoom, above 1.3, and `y` 0.78. |
| 4 | Sign in, turn on style match, and render a project whose reference subject is small in the frame. | The finished picture is cropped toward that subject, tighter than a subject that fills the frame. The raw camera file is not substituted. Reload and download again: both downloads are the same file. Reference frames are absent. |
