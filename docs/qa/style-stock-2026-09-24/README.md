# Manual QA — automatic Commons insert

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a style cut that asks for B-roll searches Wikimedia Commons with the owner’s words and inserts one clip. Only CC BY, CC0, and public domain pass. The credit stays on the asset. Reference text is not the search query. A manual import still requires `license_reviewed`.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Load `/`. | The page references the bundle built for this commit. That bundle contains “A Commons clip with a CC BY, CC0, or public-domain license was inserted.” |
| 3 | On the deployed code, run the license filter against an all-rights-reserved page and a CC BY page. | The reserved page is rejected. The CC BY page is accepted and keeps the artist. |
| 4 | Sign in and open a style-match project whose reference asks for B-roll or stock, with words in the script. | The report shows the Commons sentence, or “No Commons clip with a CC BY, CC0, or public-domain license matched your words.” The job does not succeed by swapping in the raw camera file. |
| 5 | If a Commons clip was inserted, open the asset credit and download the main file. | The credit names the artist, the license, and the Commons source. The picture is that clip for part of the shot, then the presenter returns. Reference frames are absent. Reload and download again: both downloads are the same delivery. |
| 6 | Try a manual stock import with `license_reviewed` false. | The request is rejected. No file is saved. |
