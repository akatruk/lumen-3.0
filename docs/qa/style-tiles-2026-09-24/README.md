# Manual QA — illustration tile count

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: an illustration still draws equal shapes from the owned words. When the reference shows one bright block, the export draws one shape. When it shows four, the export draws four. Without a measured count, two owned words still draw two shapes. Reference text stays out of the file.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Measure a dark frame with one gold block in the first illustration slot, and one with a gold block in all four slots. | The first frame has `tiles` 1. The second has `tiles` 4. |
| 3 | Build an illustration cut whose picture has `tiles` 4 and whose speech is `Visa`, and one with no tile count whose speech is `Visa days`. | The measured cut draws 4 shapes and the text is `Visa`. The word cut draws 2 shapes. The reference line is absent. |
| 4 | Render a 1.2 second slot with 1 shape and one with 4 shapes. | The four-shape file lasts about 1.2 seconds. The fourth slot is brighter than the same point on the one-shape file. |
