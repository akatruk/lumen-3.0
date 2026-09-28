# Manual QA — effect score before and after frames

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: before frames are compared, a score of 100 is a rule score and is not presented as a picture match. After a render, effect similarity is the average of that rule and the measured frames, and the overall score uses the average. A missing frame measurement leaves the rule in place. The rendered file is unchanged by this report.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Open a style-match report whose frames have not been compared and whose effect rule is 100. | The page says a score of 100 is not a picture match and that frames have not been compared yet. The effect line is the rule score. It is not labeled effect similarity. |
| 3 | Blend that rule of 100 with a frame measurement of 40, the way a finished render does. | Effect similarity is 70. The overall score is 95. The page shows the rule, the frame measurement, and says they were averaged. It says this is not a copy of the reference. |
| 4 | Blend again with no frame measurement. | The rule stays. The report stays uncompared. It is still not a picture match. |

## Production result

Passed on https://lumen-fix.universalgravity.org/ after deploying commit `972650d`. Health returned `{"status":"ok","version":"0.1.0"}`. Served assets `index-DLtLXRg8.js` and `index-DnZ-Ynli.css` match the local build. Backup: `/opt/lumen-rebuild/backups/style-score-honesty-20260924-150420.tar.gz`. `scripts/verify_release.py` was not run. This change does not select a delivery or replace a finished file.

1. Public health was HTTP 200.
2. The deployed page, with a style report whose frames had not been compared and whose effect score was 100, said a score of 100 is not a picture match and that frames have not been compared yet. The effect line was the rule score. It was not labeled effect similarity.
3. After that report was marked compared, with a rule of 100 and a frame measurement of 40, the deployed page showed effect similarity 70, the rule score, and the frame measurement. It said the rule and the measured frames were averaged, and that this is not a copy of the reference. On the host, the deployed blend of those same numbers set effect similarity to 70 and the overall score to 95.
4. A blend with no frame measurement kept the rule at 100, left the report uncompared, and did not store a frame measurement.

No customer project was edited. The page check used the deployed bundle with a stubbed studio response. The blend check used the deployed Python module and the numbers above, not a live picture.
