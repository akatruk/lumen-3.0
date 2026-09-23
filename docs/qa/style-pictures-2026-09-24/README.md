# Manual QA — supporting pictures

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a reference screen holds an owned frame in a border; an illustration request draws shapes from owned words; one generated picture may replace those shapes. Reference pixels and reference text stay out of the file. Studio without style match does not gain this path.

Do not treat a green job status as a pass. Check the page, the report sentences, and a rendered file.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Open `/#studio` signed in. Leave “Match the reference pacing…” unchecked. | One presenter file field. No reference field. |
| 3 | Check that box. | A second file field labeled “Reference video” appears. Unchecking it removes that field. |
| 4 | Open a style-match project whose reference frame is a dark border around a bright picture. | The report includes “A screen-like reference shot holds your frame inside a border, then lets it go.” The download shows your frame inside a border, then returns to the presenter. The border is not a copy of the reference picture. |
| 5 | Open a style-match project whose reference asks for an illustration, diagram, or infographic, with speech in that moment. | The report includes “An illustration of equal shapes is drawn from your words and fades out.” The shapes use a word from that speech. Reference observation text is absent. |
| 6 | Render that illustration project on a host that has the image key and remaining budget. | The report can include “One generated picture uses your words. It has no text from the reference.” The picture has no letters. If the key, budget, or provider fails, the equal shapes from step 5 are still in the file and the job is not marked successful by swapping in the raw camera file. |
| 7 | Download the main file, reload the project, and download again. | Both downloads are the same selected delivery. Duration stays within the edit. Audio from the owned video is still present when the source had audio. |
