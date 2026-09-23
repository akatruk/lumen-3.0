# Manual QA — unusable holds and the best frame

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a near-identical hold is marked unusable, and a moving picture is not. The opening to move forward is the frame with picture detail, so a flat white frame does not beat a later detailed frame. A black opening is still removed, and the frame after it can still open the cut. A hold that covers spoken words stays in the cut.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Measure a 0.4 second dark frame, a 1.2 second white hold, then a 0.4 second different frame. Measure 1.6 seconds of a moving test picture. | The white hold is one freeze span starting before 0.6 seconds and ending after 1.4 seconds. The moving picture has no freeze span. |
| 3 | Measure a black second followed by a solid color, and a white second followed by a detailed picture. | The highlight after the black frame starts at or after 0.8 seconds. The highlight after the white frame starts at or after 0.9 seconds. |
| 4 | Build a cut that removes 8–14 seconds, one that is asked to remove 1–3 seconds while those seconds are spoken, and one whose highlight is 30–34 seconds. | The 8–14 second removal shortens the cut below 39 seconds. The spoken span stays about 40 seconds. The highlight opens the cut at or after 28 seconds. |
