# Manual QA — screen border follows the measured frame

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a reference that looks like a screen still holds an owned frame inside a dark border. A thicker measured border makes a thicker border in the export. A named screenshot with no measurement keeps a border of one tenth. Reference pixels and reference text stay out of the file.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Measure a dark frame with a bright picture inset by 28 pixels, and one inset by 16 pixels, both 180 by 240. | Both are screens. The thicker border’s bezel is larger than the thinner one, and the thinner one is at least 0.06. |
| 3 | Build a cut from a measured screen whose bezel is 0.18, and one from the word screenshot with no measurement. | The measured clip keeps bezel `0.18` and a screen time. The word clip keeps bezel `0.1`. The reference line is absent. |
| 4 | Render a 1.2 second owned frame with bezel `0.18`. | The duration stays about 1.2 seconds. A sample inside the picture is brighter than a sample in the border. |
