# Manual QA — vertical composition

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a measured reference subject in the top or bottom third sets the owned frame’s vertical position. A flat frame stays centered. Left/right framing is unchanged. Reference pixels are not copied.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | On the deployed code, measure a dark frame with a bright block in the bottom third, and a flat color frame. | The bottom block reports `y` 0.78 and zoom above 1. The flat frame reports `y` 0.5 and zoom 1. |
| 3 | On the deployed code, measure a shot that starts with the bright block at the top and ends with it at the bottom. Build one style clip from that picture. | `y` is 0.22 and `y_end` is 0.78. The clip stores both values and zoom 1.35. |
| 4 | Sign in, turn on style match, and render a project whose reference subject sits low in the frame. | The finished picture is cropped toward that lower area. The raw camera file is not substituted. Reload and download again: both downloads are the same file. Reference frames are absent. |
