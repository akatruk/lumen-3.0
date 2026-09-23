# Manual QA — project tools on top, wider settings

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: the project tool row (Edit, Subtitles, Audio, Effects, Materials, Review) sits above the player. The settings column takes the width that row used to occupy. Labels in that column are larger and darker. The app sidebar, sign-in, and library stay as they are. No backend change and no service restart.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Open the site and read the stylesheet named by `index.html`. | The served CSS is the new build. Project tools use a top row (`tools tools`). The settings column is at least 520px wide on a desktop layout. Inspector labels are 14px in `#1c2740`. |
| 3 | On a desktop width, open a studio project. | The six tools are one row above the player. The settings panel is on the right. Timing and framing labels are dark and readable. The player and the scene list stay in the center. |
| 4 | Choose Subtitles, then Audio, then Effects, then Edit. | The right heading follows the tool. The top row stays in place. The player does not reload away. |
| 5 | Narrow the window to 390px and open the same project. | The page does not scroll sideways. Tools stay reachable above the settings. Settings use the full width. |
| 6 | Open the library and the sign-in screen. | The left workspace navigation is still on the side. Email and password sign-in are still there. |

## Production result

Passed on https://lumen-fix.universalgravity.org/ after the static deploy. Health returned `{"status":"ok","version":"0.1.0"}`. Served assets `index-CyUf6rQv.js` and `index-DnZ-Ynli.css` match the local build byte for byte. No service restart.

On a studio project at 1440px the six tools sit above the player, the settings column is 540px, and a settings label is 14px. Subtitles, Audio, Effects, and Edit each update the right heading and leave the player source in place. At 390px the page does not scroll sideways and the settings column uses the width. The library sidebar stays on the left at desktop width. Sign-in still asks for email and password. The temporary QA session was removed. No project was edited and no render was started.
