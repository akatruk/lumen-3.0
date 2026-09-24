# Manual QA — Approve renders the saved style-match edit

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: Approve in style match renders the edit that is already saved and makes that file the selected delivery. Regenerate video and Regenerate selected section stay. A failed render keeps the previous finished file and does not put the source in its place. Style match stays off until it is requested. The manual editor stays on the project. The report does not say the file copies the reference. The player and the main download are the same selected delivery. A second picture render keeps the voice and music already selected.

Use an isolated project. Do not edit an existing customer project. Do not treat a queued job or a green status as a pass. Compare the played file with the downloaded file.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Open `/#studio` signed in. Leave “Match the reference pacing…” unchecked. | The box is unchecked. One presenter file field is shown. No reference file field. |
| 3 | Open a studio project that already has a plan. | The manual editor is on the page: scene list, Approve, and the edit tools. Style match does not hide it. |
| 4 | On a style-match project, open Automatic style match. | Approve this cut, Regenerate video, and Regenerate selected section are all there. The text says the cut uses your footage and does not say the file copies the reference. |
| 5 | With no job running, choose Approve this cut. | The saved edit is queued for render. The scene ranges already in the editor are the ones rendered. The project does not rebuild a different cut first. |
| 6 | When that render finishes, play the finished video and download the main file. Reload, then play and download again. | The player and the download are the same selected delivery. The duration follows the saved edit. The file is not the original upload. |
| 7 | Select a voice and a music track on that delivery, then render the picture again. | The new file is the selected delivery. The same voice and the same music are still in the player and in the download. |
| 8 | Cause a later picture render to fail, or inspect a project whose latest render failed after a finished file existed. | The previous finished file is still the one played and downloaded. The source is not offered as that finished file. The page does not describe the failure as a successful new cut. |

## Production result

Passed on https://lumen-fix.universalgravity.org/ after deploying commit `92cedf5`. Health returned `{"status":"ok","version":"0.1.0"}`. Served assets were `index-CyUf6rQv.js` and `index-DnZ-Ynli.css`. Backend `style_match.py` on the host queues a render from Approve. `scripts/verify_release.py` was not run.

An isolated project used a 4-second red picture with a 110 Hz tone, a previous green finished file, a selected Russian male voice at 440 Hz, and a synthetic music track at 220 Hz. No live speech or music provider was called.

1. Health was HTTP 200.
2. Studio left “Match the reference pacing…” unchecked, with one presenter file field and no reference file field.
3. The manual editor stayed on the project: scene list, Approve, and the edit tools.
4. Automatic style match showed Approve this cut, Regenerate video, and Regenerate selected section. The report said the cut uses your footage only, and that reference music and the reference grade were not copied.
5. Approve queued the saved edit. The job payload kept zoom 1.05 and the 0–4 s range, with the selected music and voice. It did not rebuild a different cut first.
6. The finished file was a red mix, about 4.0 s, with the 440 Hz voice and the 220 Hz track. The player and the main download were the same file. Reload kept that match. The file was not the original upload and not the previous green cut.
7. Regenerate video built a second picture. The new selected delivery still played the Russian male voice and the same music track. The player and the main download matched again.
8. A later render was made to fail by replacing that project's source with invalid bytes. The job failed with `media_processing_failed`. The player and the download stayed on the previous mix. The page said the attempt failed and that finished versions are safe.

The temporary user, session, and project were removed. No customer project was edited.
