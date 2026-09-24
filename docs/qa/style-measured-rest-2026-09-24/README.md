# Manual QA — measured effects, wipe-down, placement, and stills

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: blur, glow, shadow, and slow motion turn on only from a measured picture. A measured top arrival is `wipe-down` (`wipedown`). Words do not set it. Card, lower plate, and chart bars follow a measured center. The editor can show frame, text, card, and progress tracks. One speaking cut can win a small overlap. A measured photo, illustration, or extra cutaway may add up to two licensed Commons stills.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | On the deployed code, classify a wipe-down sentence and a measured top arrival. | The sentence stays `cut`. The measured join is `wipe-down`. |
| 3 | Render two owned color clips with `wipe-down`. | The filter is `wipedown`. At 0.16s the incoming top is brighter than the bottom. |
| 4 | Open the served studio bundle. | It includes `wipe-down` and «Появление сверху». |

## Production result

Passed on https://lumen-fix.universalgravity.org/ after deploying commit `8e77ad6`. Health returned `{"status":"ok","version":"0.1.0"}`. Served assets `index-DUgtVOjF.js` and `index-CjgqP3ll.css` match the local build. Backup: `/opt/lumen-rebuild/backups/style-measured-rest-20260924-110253.tar.gz`. `lumen-web` and `lumen-worker` were restarted while the queue was idle. `scripts/verify_release.py` was not run. The render used synthetic color pictures, not a customer project.

1. Public health was HTTP 200.
2. On the host, a wipe-down sentence stayed `cut`. A measured top arrival set `wipe-down`.
3. The owned render command contained `wipedown`. At 0.16s the incoming top measured Y 212.0 and the bottom measured Y 170.3.
4. The live page loaded `index-DUgtVOjF.js`, which contains `wipe-down`, «Появление сверху», «Полоса прогресса», and «Время слоёв».

Local checks before deploy: 84 pytest cases in `test_style_match.py`, `test_style_vision.py`, `test_style_stock.py`, `test_style_pictures.py`, and `test_transitions.py`; frontend locale and layer-timing tests; production frontend build. Those fixture tests do not score live editorial quality. Commons retrieval was mocked. Blur, glow, shadow, slow motion, graphic centers, overlapping takes, and still slots were not re-rendered on a customer project.

No customer project was edited.
