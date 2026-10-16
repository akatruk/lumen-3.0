# Baseline

Source videos are the stem-design renders on `experiment/semantic-motion-design` (`8d96789`).

| file | sha256 | duration | audio md5 |
| --- | --- | --- | --- |
| `output/semantic-motion-design/original3-after.mp4` | `ed73a0cb22e1a020e40bdbbee4b748738ffdc816998fabf47c64f4b9832c025a` | 34.048s | `fe661600593927118c37c0b5298ff74e` |
| `output/semantic-motion-design/original2-after.mp4` | `721d4e7eb372d19a6f76259dbf4ebd8938664aec2ae85ee834708e73d4610a91` | 33.045s | `aa950a4f5dfd31ed17cb58a6132d53a4` |

Geometry in `editorialFocusRects()`: graphic `{64,128,952×582}`, speaker `{656,730,360×640}`, caption band top `y=1390`. Canvas 1080×1920.

## Measured

Pixels with luminance above 40 inside the graphic rect.

| frame | what is on screen | ink box | fraction of graphic |
| --- | --- | --- | --- |
| original3 3.2s | 使用场景, one node | 369×81 | 0.027 |
| original3 16.8s | two labels and a stem | 367×156 | 0.034 |
| original3 30.8s | three labels and a stem | 206×229 at x=202 | 0.023 |
| original2 0.35s | 1.5万 and the start of the stem | 554×183 | 0.027 |
| original2 2.0s | 1.5万 and 2.5万, no unit | 892×183 | 0.053 |
| original2 30.8s | 400 and 1200, 人民币, a short stem | 862×242 | 0.057 |

Caption ink sits around y=1478–1538. Speaker mean luminance inside the PIP is about 140 (original3) and 100 (original2), so the face is in the box.

## Judgment

The stem proved the items belong together. It did not make a composition. Three short words occupy a blob about 200px wide in a 952px band. The range already places the ends apart, and the connector is still a short stroke between two figures.
