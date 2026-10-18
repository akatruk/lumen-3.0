# Browser test

Local only. Vite `127.0.0.1:5178`, API `127.0.0.1:8018`, `FAST_PROJECT_CREATION_ENABLED=1`, `LLM_PROVIDER=none`, `PUBLIC_ORIGIN=http://127.0.0.1:5178`. No worker, so transcription stays queued. That is the point of the status split: the project is ready while the transcript is not.

| Check | Result |
| --- | --- |
| Open Create Project | `#studio` heading “New project”. Hash change to that heading returned in a 400ms wait. A later project-page navigation reported `loadEventEnd` 56ms. |
| Upload a valid video | `咨询-Обзор.mp4`, 360×640, 31.0s, 295122 bytes, attached through the file input |
| Generated name | `咨询-Обзор` |
| Long filename | 130 CJK characters plus `.mp4` produced a 120-character title |
| Output language | Select set to Русский in the form |
| Create | Landed on `#project/d88c0800992b400fb7eada3cfa2701df`. The follow-up poll saw the project 252ms after it started; the 288KB local transfer had already finished inside the click. App time is under a second. This is not a timed 10–15s user session. |
| Project appears | Title `咨询-Обзор`, status `ready`, stage `ready` |
| Reload | Same title, `language=ru`, Create video still enabled |
| Source attached | `GET /media/original` 200, 295122 bytes, checksum `a3dcb1d252db586932935a3c0ac4f0bd528823560fbc25261525f47b49101374` |
| Ready vs transcript | Project `ready`. Metadata `transcription=transcription_pending`. Page text: “Source uploaded. Speech is being transcribed.” |
| Create video | Button present and enabled. Video language radio Русский checked. Voice line “Original speaker audio” while source language is still empty |
| Invalid file | `notes.txt` → “This file could not be read as a supported video.” Stayed on the create form. No project row. |
| Mobile 390×844 | File, language, name, and Advanced stack. The error sits under the card. Screenshot `after-mobile.png` |
| Keyboard | File input accepted focus. A synthetic Tab press did not move focus, so tab order past the file input was not proven |

Not run: a dropped connection mid-upload, a duplicate `request_id` retry, a horizontal video (`owned_vertical`), and a clip under 30s (`owned_duration`). Those server errors already have copy in `Studio.tsx` (`not_a_video`, `owned_vertical`, `owned_duration`, `upload_too_large`, `upload_interrupted`).

Clicks for the ordinary path, if the shown language is kept: choose file, Create project. Two clicks plus the system file dialog.
