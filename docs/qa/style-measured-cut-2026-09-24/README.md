# Manual QA — measured frame, shake, cutout, holes, owned color, column, best take

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a plan moves only from a measured frame. The word shaky does not stabilize. A request to replace the background does not cut out and does not close that report gap. Black or frozen holes of at least 0.4s leave the file, and speech inside them stays. Existing graphics take the owned frame color and the first word of the project title. A bright column shifts the frame only when no picture was measured, and the track flag stays off. A repeated line is kept only when speech and a usable frame were both measured.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Build a shot whose words are punch, pan, zoom and shaky, with no measured frame or shake. | Zoom stays 1, the center stays 0.5, stabilize stays off, and the stabilize gap stays non-essential. The motion filter has no deshake. |
| 3 | Build the same shot with a measured shake radius of 32. | Stabilize is on and the filter is `deshake=rx=32:ry=32`. |
| 4 | Ask to replace the background on a green plate. | Cutout stays off, the plate is empty, and the background-replacement gap stays non-essential. A green-screen cutout on that plate does cut out onto `1A1F1C`. |
| 5 | Render a 4s picture with a measured unusable span from 1s to 2s, then render it again with speech covering that span. | The first file is 3s. The second file stays 4s. |
| 6 | Follow a measured column when the shot has no picture, and again when a picture sets x to 0.4. | Without a picture, x moves from 0.22 to 0.78 and track stays false. With a picture, x stays 0.4 and zoom stays 1.2. |
| 7 | Choose between two copies of one spoken line when one copy sits on an unusable span. | The clean copy remains. With no unusable measurement, or with no speech, both copies remain. |
| 8 | Prefix an existing lower-third word with the project title, and render a progress bar with ink `224466` beside the default cream bar. | The existing word starts with the title word. An empty line is not invented. The ink bar measures darker than the cream bar. |

## Production result

Passed on https://lumen-fix.universalgravity.org/ after deploying commit `1545632`. Health returned `{"status":"ok","version":"0.1.0"}`. Backup: `/opt/lumen-rebuild/backups/style-measured-cut-20260924-094620.tar.gz`. Frontend assets were not replaced. `scripts/verify_release.py` was not run. This check used synthetic color pictures, not a customer project and not a live voice or music bed.

1. Public health was HTTP 200.
2. On the host, punch, pan, zoom and shaky left zoom at 1, x at 0.5 and stabilize off. The motion filter had no deshake. The stabilize gap stayed non-essential.
3. A measured shake radius of 32 turned stabilize on. The filter was `deshake=rx=32:ry=32`.
4. Replace-the-background on green left cutout off and the plate empty. The background-replacement gap stayed non-essential. Green-screen cutout on the same plate set cutout and plate `1A1F1C`.
5. A rendered 4s picture with an unusable span from 1s to 2s came out at 3.0s. The same span covered by speech rendered at 4.0s.
6. A measured column with no picture set x from 0.22 to 0.78 and left track false. A measured picture at x 0.4 and zoom 1.2 kept those values.
7. Of two copies of one line, the copy on the unusable span was dropped. With no unusable list, or with no speech, the cuts stayed as they were.
8. An existing lower-third word gained the project title word. A shot with no words stayed blank. A progress bar painted `224466` measured Y 67.1. The same bar with no ink measured Y 208.1.

No customer project was edited.
