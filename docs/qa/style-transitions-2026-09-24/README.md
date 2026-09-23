# Manual QA — measured transitions

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a shot boundary is named only when the renderer already has that transition. Fade through black, a dissolve, a left-to-right wipe, and a circle opening from the center are recognized. A hard cut stays a cut. A wipe that enters from the right stays a cut, because the renderer only has a left wipe. Reference pixels are not copied.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | On the deployed code, classify a hard cut, a fade in from black, a left wipe, a right wipe, a center opening, and a dissolve. | They are `cut`, `fade`, `wipe`, `cut`, `circle`, and `crossfade`. |
| 3 | Build one style clip whose measured transition is `wipe`. | The clip’s transition is `wipe`, which the existing wipe filter can render. |
| 4 | Sign in, turn on style match, and render a project whose reference changes with a wipe or a fade. | The finished picture uses that transition between owned shots. The raw camera file is not substituted. Reload and download again: both downloads are the same file. Reference frames are absent. |
