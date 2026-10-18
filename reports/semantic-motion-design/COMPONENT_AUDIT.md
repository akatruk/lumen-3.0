# Component audit

Checkout: `experiment/semantic-motion-design`, branched from `experiment/responsive-editorial-layout` (`b8fba4f`).

Layouts present in `motion/src/semantic/layouts.ts`: `speaker_visual`, `full_frame`, `overlay`, `editorial_focus`. Ranking default remains `off`.

## motion.process_timeline.v1

Mounted only from `SemanticMotion` `Body` when `visualIntent === "process_timeline"`. Props are the existing `SemanticMotionPayload`: `steps[]` as strings or `{label, at, until}`, `evidence.sourceTimestamp`, `outputTime`, `locale`. No new fields.

Before this change the wide box (`>= 700`) put the active label on `theme.type.hook` (max 128) and the quiet rows at opacity 0.38, left-aligned in a tall column. One spoken word filled the type role. The other rows disappeared into the background. Timing already hid a row until `step.at`.

Minimum: the ranker still wants two labels. The component now draws one label if that is all it was given, and draws no second label.

## motion.numeric_range.v1

Mounted from the same `Body` for `visualIntent === "numeric_range"`. Props: `range.lowText`, `range.highText`, `range.unit`, `range.kind`, `labels`. `rangeKindLabel` is unchanged (`月薪` / `每天` / `金额` and the en/ru pairs).

Before: two stacked figures and a gray track that filled left to right. That track reads as a progress bar. It does not say "these two ends are the range."

## What was not a consumer

`componentsV15.tsx` has its own steps. Gallery layouts stay the original three. Director, optimizer, and ranking were not edited.
