# Manual QA — second kinetic caption step

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a kinetic title still scales and moves the first owned word. When the owned speech has a second word, that word enters afterward as its own line. One owned word stays one line. Reference text is not used. The burned caption is checked on the server, where the ASS filter is available.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Write a kinetic caption for `Visa`, then for `Visa days`. | `Visa` is one dialogue line and still scales to 100. `Visa days` is two dialogue lines. The second line is `days` and starts later than the first. |
| 3 | On the server, render a 1.2 second slot whose kinetic text is `Visa days`. | The file exists, its duration is about 1.2 seconds, and the caption filter is the ASS filter. |
