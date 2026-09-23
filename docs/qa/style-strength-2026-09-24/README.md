# Manual QA — measured blur, glow, and shadow strength

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: blur, glow, and shadow keep the existing filters, and their strength follows the frame when the frame separates the effect. A heavier blur scores higher than a light blur. A deeper vignette scores higher than a milder one. A bright core with a lifted ring gets a glow amount. A sharp frame, a flat frame, and a hard card do not. Reference pixels are not copied.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | On the deployed code, measure a light blur, a heavy blur, a sharp frame, a flat frame, a mild vignette, a deep vignette, and a halo. | Heavy blur is greater than light blur, and both are above 0. Sharp and flat blur are 0. Deep shade is greater than mild shade, and both are above 0. The halo glow is above 0 and its blur is 0. |
| 3 | Build a style clip from blur `4.5`, glow `1.1`, and shade `1.2`. | The clip stores those three strengths, with glow and shadow on. |
