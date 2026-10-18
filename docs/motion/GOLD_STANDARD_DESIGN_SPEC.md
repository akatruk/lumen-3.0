# Gold standard design spec

Measured from the two reference files on 2026-10-15. Values marked **estimate** were read from frames, not from a project file. Easing curves, font names, and layer structure cannot be recovered from an MP4.

Sources:

- Reference A: `Hayek-Law-English (2).mp4`, 1080×1920, 30 fps, 58.100 s. sha256 `25c13489073b823c7a20d08d6834a091c5f2bebf00bc7b7818c3bd106cfce29b`.
- Reference B: `video_2026-10-14_15-41-20.mp4`, 480×848, 30 fps, 174.433 s. sha256 `e6e4662f41daa30ff07ef3c0f65bf61fd289d3a1bfd59e9197605b1d629fbde1`. Ratios below are frame fractions so they survive the resolution difference.

This spec extracts scale, hierarchy, and motion. It does not reproduce either film's branding, palette, or layout.

## What the references actually do

Reference A cuts from a full-frame speaker to a full-bleed graphic plate. During plates the speaker is a small portrait, about 200×226 px at x 808–1006, y 82–308 (measured skin pixels on the 8 s, 14 s, 25 s, and 43 s frames). That is 18.5% of the frame width. The explanation is the frame. Cards, a list, a globe, or a document stack occupy the middle. Type sits in the upper third and again near the bottom.

Reference B spends long stretches on the speaker with a caption and a small topic chip. When it explains, it cuts to a plate: a building with a round portrait, or a paper document at x 42–414, y 90–614 on the 52 s frame (372×524 px, 77.5% of width, 61.8% of height). The speaker inset on that frame is about 62×90 px (13% of width). A highlight travels down the list while the document stays. A later plate adds one colored bar at a time.

Neither reference explains a 14-second idea with a 64 px icon in a chip above the hairline.

## Grid (1080×1920)

| Band | y | Role |
| --- | --- | --- |
| Top margin | 0–96 | Index and brand-free kicker. Reference A type starts well below a ~48 px edge. **Proposal:** 48 px inset. |
| Speaker window, graphic mode | varies by dimension | 28–40% of frame width. Not a circle. Not full frame. |
| Hero object | center of the free field | Union box at least 42% of width (≥454 px) and 28% of height (≥538 px). From B's 78% document and A's globe, whose light pixels run roughly y 720–1360 (**estimate** ~500–680 px). |
| Caption | 1660–1860 | Lower 15%, matching both references. Height 160. Side inset 48. |

Safe area: 48 px from each edge. Caption and hero must not overlap. Speaker window and caption must not overlap.

## Typography

Measured glyph sizes are not available. **Proposal**, set against the reference hierarchy (kicker, then a headline that dominates the card labels, then a caption):

| Role | Size | Use |
| --- | --- | --- |
| Dimension title | 64–76 px | One line. The name of the current dimension. |
| Object label | 36–44 px | One short phrase under the hero. |
| Caption | 40–56 px | Spoken line, high contrast, max two lines. |
| Kicker | 22–28 px | 第一层 / Layer 1 / Слой 1. |

CJK and Cyrillic use the existing locale font stack. Do not bake words into SVG.

## Color and contrast

Do not reuse the reference navy, gold, magenta, or yellow highlight.

**Proposal:**

- Plate `#241e1a` (warm charcoal, not black, not a full-frame void over the face during the opening).
- Paper `#f3eee6`.
- Ink `#1c1612`.
- Accent `#9c3b2e`.
- Mute `#a3988c`.

Paper on the plate is the contrast pair. Captions are light type on a 0.72 ink pill. One accent, used for the active object only.

## Depth

Three planes:

1. Plate.
2. Hero object, with a soft offset shadow (y 18, blur 28, alpha 0.28).
3. Speaker window, 2 px light edge, radius 28. Above the plate, never over the hero.

No generic gradient fills. No second decorative background.

## Motion

Reference A changes plates on hard cuts (scene hits at 6.63, 14.33, 25.17, 33.60, 43.10, 51.43 s). Inside a plate, captions change while the structure holds for several seconds.

Reference B holds a document and moves a highlight over ~8 s (item 01 at 52 s, item 05 at 60 s), and adds bars one at a time between 97 s and 110 s.

**Proposal:**

- New dimension: 14 frames (0.47 s), cubic ease-out. Opacity and a 36 px rise. Not a bounce.
- Object inside a dimension: swap on the spoken sub-phrase, 10-frame crossfade. A dimension that lasts ~14 s must change object at least three times.
- Exit: 10 frames, fade plus 24 px rise. No spin, no continuous zoom.
- Speaker window moves between dimensions over 16 frames. It does not jump.

## Three treatments

These are original. They are not the reference layouts.

1. **使用场景.** One hero at a time in the free field: a house, then a workplace, then a school, then a short-stay versus long-stay path. Words only from the excerpt.
2. **家庭结构.** Large silhouettes that assemble, then a highlight moves from the three-person household to the parents. Not a row of chips.
3. **代价.** A large application sheet, then further sheets fan out behind it. No amounts, no currency. The excerpt only says the cost is not just the application fee.

Opening (0–2.4 s) is the speaker full frame. The speaker remains visible in a window for the rest of the excerpt.
