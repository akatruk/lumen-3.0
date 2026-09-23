# Manual QA — measured overlays, masks, and split screens

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: a split, an ellipse mask, and a lower-third band are applied only when the reference frame matches a filter the renderer already has. The words “split screen”, “mask”, and “icon” do not turn those effects on by themselves. A thin full-width progress bar stays a progress bar. Reference pixels are not copied.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | On the deployed code, measure an ellipse on a dark plate, a left/right split, a thick lower band, a thin bottom bar, and a flat frame. | The ellipse is `mask`. The split is `split` and not `mask`. The thick band is `lower` and not `mask`. The thin bar and the flat frame are not `lower` and not `mask`. |
| 3 | Build style clips from those measurements, and one clip whose text only says split screen, mask, and icon. | The measured split stores `split` and a panel. The measured mask stores `mask`. The measured band stores `lower` and the owned word. The word-only clip stores none of the three. |
