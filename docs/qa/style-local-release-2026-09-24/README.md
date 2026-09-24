# Manual QA — overlay window, one stock clip, no generated picture, Approve copy

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a progress bar with a measured entrance and no measured exit stays to the end of the clip. A second Commons clip is not added. A generated picture is cleared before render. Approve says it renders the saved edit, does not publish, and does not copy the reference. An effect may start as late as 98% of the clip. The visual effect plaque and the sliding menu are included because the studio screen uses them.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Open a style-match report before frames are compared. | The fold says a score of 100 is not a picture match. Approve says it renders the saved edit, does not publish, and does not copy the reference. |
| 3 | Build a bar whose entrance is measured and whose exit is not. | The bar starts at the measured entrance and runs to the end of the clip. |
| 4 | Attach Commons footage twice. | One external clip remains. The second attach does not add another. |
| 5 | Run the picture attachment on a cut that already has generated art. | Every clip art field is empty. No image request is made. |
