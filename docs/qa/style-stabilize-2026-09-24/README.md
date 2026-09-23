# Manual QA — deshake window from the measured shift

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: stabilization stays on the existing deshake filter. A shift of one column uses window 8. A shift across the frame uses window 32. A block that stays put is not stabilized. The word shaky uses window 16. Vidstab is not used. The rendered slot keeps its duration.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Measure a block that jumps from the left to the center, one that jumps from the left to the right, and one that stays on the left. | The short jump has shake and `shake_rx` 8. The long jump has shake and `shake_rx` 32. The still block has shake false and `shake_rx` 0. |
| 3 | Build a cut from the word shaky, one from a measured `shake_rx` of 32, and one from a still layout. | The word sets stabilize and `shake_rx` 16. The measurement sets stabilize and `shake_rx` 32. The still layout leaves stabilize false and `shake_rx` 0. |
| 4 | Render a 1.2 second slot with deshake window 32. | The file duration stays about 1.2 seconds. The filter is `deshake=rx=32:ry=32` and does not name vidstab. |
