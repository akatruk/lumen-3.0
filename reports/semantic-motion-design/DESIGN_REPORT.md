# Design

One iteration. A second pass was not justified: the remaining dark field is the editorial layout's unused area around short labels, and filling it with panels would be the stock-card look this pass was meant to avoid.

## Shared language

Stroke is the existing accent from `inkFor`. Nodes are 16px circles on a 2px stem. Type stays on `theme.type.title` for the active timeline word and the range figures, `support` for quiet rows and a verified unit, `label` for the kind word. No cards, no gradient, no glow. Entrance is the existing `rise` (12 frames, cubic out).

## Timeline

A vertical stem connects rows that are already on screen. A row stays hidden until its source `at` time. The active row is title-sized and full ink. Quiet rows stay at 0.72 opacity in the support role, so the other layers remain readable. There is no "步骤" prefix. `第一层` stays in the caption, which is where the speaker says it.

One verified label draws a single node and no stem, so a missing second item is not invented.

Column math is `timelineColumn`. Editorial (952) and the split (504) both keep `rail + gutter + label` inside the box. Active height 96 / 72, quiet 52 / 44. Labels are left-aligned, max 2 lines.

## Range

The two spoken strings sit at the ends of a stem. The stem draws from the low end to the high end across frames 8–24. The high figure comes in across frames 16–26. Both ends are held together after that. There is no gray track, no midpoint, no percent.

Wide boxes place the figures on either side of the stem. Narrow boxes stack them with the same stem between. `range.unit` is painted only when the payload has one. `每天` / `月薪` remain the existing kind labels.

## API

`Label` gained optional `align` and `maxLines`. Defaults match the old centered single-line call. `NumericRange` and `ProcessTimeline` props are unchanged.
