# Manual QA — similarity of the applied frame

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: the rule score still reports whether the planned zoom and transition match. After a render, effect similarity also compares the applied frame with the reference on spread and edge strength. The same picture scores high. A heavily blurred copy scores lower. The rule score on an unrendered plan stays in place.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Compare a detailed test picture with itself, then with the same picture blurred by sigma 8. | The matching pair scores at least 90. The blurred pair scores at least 15 points lower. |
| 3 | Build a style plan whose first shot asks for a fade and a punch-in, before any render. | `effect_similarity` stays 100 from the rules. |
