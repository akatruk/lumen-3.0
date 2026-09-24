# Manual QA — effect score before and after frames

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: before frames are compared, a score of 100 is a rule score and is not presented as a picture match. After a render, effect similarity is the average of that rule and the measured frames, and the overall score uses the average. A missing frame measurement leaves the rule in place. The rendered file is unchanged by this report.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Open a style-match report whose frames have not been compared and whose effect rule is 100. | The page says a score of 100 is not a picture match and that frames have not been compared yet. The effect line is the rule score. It is not labeled effect similarity. |
| 3 | Blend that rule of 100 with a frame measurement of 40, the way a finished render does. | Effect similarity is 70. The overall score is 95. The page shows the rule, the frame measurement, and says they were averaged. It says this is not a copy of the reference. |
| 4 | Blend again with no frame measurement. | The rule stays. The report stays uncompared. It is still not a picture match. |
