# Manual QA — cards, icons, and progress from owned figures

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a chart card is titled with the first owned figure. A measured progress bar uses an owned percent when the speech has one, and keeps the shot index when it does not. A lower-third icon plate grows to that percent. Days and other units do not become a fill. Reference wording stays out of the card.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Build a style edit whose script is `Price 120000 and deposit 30000` and whose speech is `The visa takes 120 days`. | The card title is `Price`, the primary line is `120000`, and the items are 120000, 30000, and 120. The reference line is absent. |
| 3 | Build a bar layout for `Complete 80%`, a lower-third for `Saved 40 percent`, and a bar layout for `Visa takes 120 days`. | Every bar clip is progress `0.8`. The icon clip has mark `0.4` and progress `0`. The days clip still ends at progress `1`. |
| 4 | Render a 1.2 second lower-third whose icon mark is `0.8`. | The file duration stays about 1.2 seconds. A sample inside the plate is brighter than a sample past the plate. |
