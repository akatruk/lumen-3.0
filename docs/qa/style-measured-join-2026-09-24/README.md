# Manual QA — measured joins and a bottom arrival

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a fade, wipe, or zoom sentence does not set the join. A measured bottom arrival uses the upward wipe. A measured top arrival stays a cut and leaves a non-essential gap.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Build a shot whose transition sentence says fade, wipe, or zoom and whose frames did not measure a join. | The clip stays a cut. |
| 3 | Build a shot whose measured join is a bottom arrival. | The clip transition is `wipe-up` and the upward-wipe gap is closed. |
| 4 | Build a shot whose measured join arrives from the top. | The clip stays a cut. The report keeps a non-essential `wipe_down` gap. |
| 5 | Render two owned color clips with `wipe-up`. | The filter is `wipeup`. Early in the incoming clip, the bottom is brighter than the top. |
| 6 | Open the served studio bundle. | It includes `wipe-up` and the Russian label for that option. |

## Production result

Passed on https://lumen-fix.universalgravity.org/ after deploying commit `7644d04`. Health returned `{"status":"ok","version":"0.1.0"}`. Served assets `index-BEg0aEzL.js` and `index-rB-9jG7e.css` match the local build. Backup: `/opt/lumen-rebuild/backups/style-measured-join-20260924-101740.tar.gz` and `/opt/lumen-rebuild/backups/style-measured-join-dist-20260924-101740.tar`. `scripts/verify_release.py` was not run. The render used synthetic color pictures, not a customer project.

1. Public health was HTTP 200.
2. On the host, fade, wipe, and zoom sentences left the clip as a cut.
3. A measured bottom arrival set `wipe-up` and did not leave the upward-wipe gap.
4. A measured top arrival stayed a cut and kept a non-essential `wipe_down` gap.
5. The owned render command contained `wipeup`. At 0.08s the incoming bottom measured Y 212.0 and the top measured Y 105.5.
6. The live page loaded `index-BEg0aEzL.js`, which contains `wipe-up` and «Появление снизу».

No customer project was edited.
