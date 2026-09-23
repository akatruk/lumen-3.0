# Manual QA — speed change inside a shot

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a shot speeds up or slows down only when its two halves move differently. The clip stores a start speed and an end speed, and the render keeps the slot duration. A still shot stays at one speed. The words “speed ramp” alone do not change the speed. Reference pixels are not copied.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | On the deployed code, measure a still half followed by a jumping block, the reverse, and a flat frame. | They are start `1` end `1.45`, start `1.45` end `0.8`, and no ramp. |
| 3 | Build a style clip from a measured ramp, and one whose text only says speed ramp. Render the measured ramp for a 1.5 second slot. | The measured clip stores speed `1` and speed end `1.45`. The word-only clip stays at speed `1` with no end speed. The rendered slot is 1.5 seconds. |
