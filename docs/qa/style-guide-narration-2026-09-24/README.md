# Manual QA — style-guide narration

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: the English and Chinese style-match guide use the refreshed narration. The trend-engine commits were already on main. Raw wav and aiff intermediates stayed out of the merge.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Open `/#guide` and choose Style match in English. | The tab says 2:02. The player uses `lumen-style-en-v5.mp4` and `lumen-style-en-v5.vtt`. The second caption starts at 1.830s. |
| 3 | Switch the interface to Chinese and keep Style match selected. | The tab says 1:29. The player uses `lumen-style-zh-v5.mp4` and `lumen-style-zh-v5.vtt`. |

## Production result

Passed on https://lumen-fix.universalgravity.org/ after deploying commit `7ade450`. Health returned `{"status":"ok","version":"0.1.0"}`. Served assets `index-DFcWORD6.js` and `index-rB-9jG7e.css` match the local build. English video is 7079272 bytes. Chinese video is 5271734 bytes. Backup: `/opt/lumen-rebuild/backups/style-guide-narration-20260924-095109.tar`. Services were not restarted. `scripts/verify_release.py` was not run. No customer project was edited.

1. Public health was HTTP 200. The page script was `index-DFcWORD6.js`.
2. Style match in English showed 2:02 and loaded `/tutorial/lumen-style-en-v5.mp4` with `/tutorial/lumen-style-en-v5.vtt`. The public caption file starts the second line at 00:00:01.830.
3. Style match in Chinese showed 1:29 and loaded `/tutorial/lumen-style-zh-v5.mp4` with `/tutorial/lumen-style-zh-v5.vtt`.
