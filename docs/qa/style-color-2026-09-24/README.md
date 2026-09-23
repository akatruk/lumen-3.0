# Manual QA — measured color and light

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: the grade and exposure move the owned picture toward the reference YUV using the existing sliders. A matching pair stays neutral. A brighter reference raises brightness to the slider cap and adds exposure for the luma that cap cannot cover. A warmer, more saturated reference raises the red balance and saturation. The grade stores only those numbers. Reference pixels are not copied.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | On the deployed code, grade a bright gray frame against a dark gray frame, a warm frame against that dark frame, and the dark frame against itself. | Bright: brightness `0.2` and exposure above `0.5`. Warm: red balance and saturation are higher than the bright grade. Match: brightness `0`, contrast `1`, saturation `1`, red balance `0`, exposure `0`. |
| 3 | Read the grade keys. | Only `brightness`, `contrast`, `saturation`, `gamma`, `rs`, `gs`, and `bs`. |
