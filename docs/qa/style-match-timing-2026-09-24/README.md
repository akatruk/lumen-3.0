# Manual QA — style-match timing on owned footage

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a measured effect at about 70% of the reference lands near 70% of the owned video. Color and exposure move only when they were measured. The effect score stays uncompared until frames are compared. A zoom or right wipe is visible and the clip does not grow. Words and numbers come from the owned script. The reference file is never an ffmpeg input. Style match stays off until it is requested, and the manual editor stays on the project. A failed render keeps the previous finished file.

Use an isolated project and synthetic color bars or tones. Do not open project `06d5a2c857b64082874d755f46560b53`. Do not treat a queued job as a pass.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Open `/#studio` signed in. Leave “Match the reference pacing…” unchecked, and create a project with a reference link and no reference file. | The box is unchecked. `style_match` is false. The manual editor is on the project: scene list, Approve, and the edit tools. |
| 3 | On an isolated style-match project, measure a reference effect at about 70% of the reference (a card, a callout, or a b-roll insert) against owned footage of at least 30 seconds. | That effect lands near 70% of the owned duration. At most one licensed stock clip is inserted, at that fraction. If no licensed clip matches, the essential b-roll gap stays and no extra clip is invented. The owned edit duration does not grow past the source. |
| 4 | Read the saved clip when the reference has no measured grade and no measured exposure. | `enhance` is false, `grade` is null, and `exposure` is 0. The filter has no `eq=` and no `exposure=`. |
| 5 | Read the style report before any render. | `compared` is false and the note is `Frames have not been compared yet.` An effect similarity of 100 is the rule score. `measured_effect_similarity` is absent. |
| 6 | Render that project with the reference still attached, then read the report. | `compared` can become true. Effect similarity is then the blend of the rule score and the measured frame score. |
| 7 | Use a reference whose join measures as zoom or wipe-right. Render the owned cut and play it. | A zoom or a right-side wipe is visible at the join. The finished duration stays within the owned source duration. |
| 8 | Put `SECRET REFERENCE LINE 999` only on the reference. Put owned words and a number, such as `Price 120000`, only in the script. | Captions, cards, and any stock query use the owned words and numbers. The reference phrase and `999` are absent from the edit and from burned text. |
| 9 | During that render, list every ffmpeg `-i` input. | Inputs are the owned source and, if one was inserted, the licensed stock file. The reference path is not an input. |
| 10 | After a finished file exists, make a later picture render fail. | The previous finished file is still the one played and downloaded. The source is not offered as that finished file. The page does not describe the failure as a successful new cut. |

## Production result

Passed on https://lumen-fix.universalgravity.org/ after deploying commit `59ae2ab` and checklist `f864115`. Health returned `{"status":"ok","version":"0.1.0"}`. Served assets stayed `index-CyUf6rQv.js` and `index-DnZ-Ynli.css`. Backup: `/opt/lumen-rebuild/backups/style-match-timing-20260924-072904.tar.gz`. `scripts/verify_release.py` was not run.

An isolated project used a 32-second blue picture with a 440 Hz tone and a 2-second synthetic reference whose yellow chip starts at 70% of that file. The reference was read from the downloaded-reference path. No live Douyin, speech, or music provider was called. Commons returned no licensed clip, so the essential b-roll gap stayed and no clip was invented.

1. Health was HTTP 200.
2. The served studio left “Match the reference pacing…” unchecked. A signed-in project with a reference link and no reference file had `style_match` false. The manual editor returned a scene.
3. The measured callout was 0.70 and landed at 0.70 of the owned duration. The edit stayed 32.00 seconds.
4. With no measured grade or exposure, `enhance` was false and the filter had no `eq=` and no `exposure=`.
5. Before render, `compared` was false, the note was `Frames have not been compared yet.`, and effect similarity 100 was the rule score.
6. After render, `compared` was true. Effect similarity was the blend of the rule and the measured frame score.
7. The reference joins measured as zoom and wipe-right. Both were visible on owned clips, and those clips stayed about 1 second. The finished owned file was 32.03 seconds.
8. The edit and the burned text contained `Price` and `120000`. `SECRET REFERENCE LINE` and `999` were absent.
9. FFmpeg inputs included the owned source. The reference path was not an input.
10. A later render failed with `media_processing_failed`. The player and the download stayed on the previous file. The source was not substituted.

The temporary user, session, and projects were removed. No customer project was edited.
