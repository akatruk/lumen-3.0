# Multilingual card audit

The motion library already draws viewer-facing text through `AutoFitText`. Before this pass, that text was English copy supplied by the caller, measured with a Latin font stack, and wrapped on spaces. Photography, icons, and B-roll stay language-neutral. This layer adds locale, dictionaries, and CJK line breaking on top of the same components.

Locales: `en-US`, `ru-RU`, `zh-CN`.

## Components that show text

| Component | Text props | Hardcoded viewer strings | Font | Wrapping | Animation | Locale before | Change |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `KineticHook` | `text`, `emphasis` | none in the component; showcase and films pass English | Arial stack | `word` puts each whitespace word on its own line | fade, mask, scale, slide | not ready for Chinese, because a sentence without spaces is one line | `AutoFitText` now takes `locale`. Chinese segments with `Intl.Segmenter`. |
| `BigNumber` | `value`, `label`, `prefix`, `suffix` | none | Arial stack | label wraps on spaces | count, scale | label is caller copy | Card `big_number` resolves `process.steps` from the dictionary. |
| `ProgressSteps` | `title`, `steps[].label` | none | Arial stack | one label per row | step reveal | caller copy | Card `progress_steps` uses the process glossary. |
| `BrollCaption` / `AnimatedCaption` | `text`, timed words | none | Arial stack | phrase wrap on spaces | fade, karaoke | caller copy | Caption card uses the CJK profile when `locale` is set. |
| `Timeline` | `events[].date`, `events[].label` | none | Arial stack | short labels | along the line | dates were raw strings | Card `timeline` formats dates with `formatDate`. |
| `Comparison` | `left`, `right` labels | none | Arial stack | on spaces | split | caller copy | `before_after` and `buy_vs_rent` take labels from the dictionary. |
| `SplitScreen` | `text` | none | Arial stack | on spaces | slide | caller copy | Uses the same `AutoFitText` locale path. |
| `Checklist` | `items[].label` | none | Arial stack | on spaces | check reveal | caller copy | Card `checklist` uses due-diligence keys. |
| `StatReveal` | `headline`, `context` | none | Arial stack | on spaces | count | caller copy | Card `stat_reveal` uses occupancy copy. |
| `SpeakerFocus` | `caption` | none | Arial stack | on spaces | with the plate | caller copy | Caption is still director copy. The font follows `locale` when passed. |
| `PriceCounter`, `PriceChange`, `RentalYield` | currency, numbers, label | `toLocaleString("en-US")`, label prop `"Asking price"` | Arial stack | on spaces | count | English formatting only | Labels come from `t()`. Money uses `formatCurrency`. Currency is an ISO code, not a hardcoded `$`. |
| `PropertyComparison` | side names | the word `vs` | Arial stack | on spaces | fade | English | `vs` is `comparison.versus`. Side names stay director copy. |
| `PurchaseProcess` | `stages: string[]` | default English stage names in the demo root | Arial stack | on spaces | step fade | English list | Stages are glossary keys. |
| `Placeholder` | role name | `Speaker`, `Footage`, `Image`, `Screen` | theme sans | none | none | internal plate, not a card | Left as authoring chrome. Not a production card. |
| Deferred: `quote`, `final_cta`, `process_flow` | not rendered | — | — | — | — | — | Rendered now as cards `quote`, `cta`, and the process card. |

Showcase script and `RealEstateFilm` still contain English creative lines for those specific films. Those lines are director copy for an existing cut, not semantic UI labels. They were not rewritten.

## What changed

- `motion/src/localization/` holds `LANGUAGE_CONFIG`, the three locale packs, the glossary ids, formatters, segmentation, layout hints, and `validateLocalizedCard()`.
- A missing key throws `LocalizationError`. The English string is not returned.
- `AutoFitText` measures with the locale font. English and Russian wrap only on spaces. Chinese breaks on characters, and closing punctuation stays with the previous character.
- `segmentTextForMotion()` keeps Russian words whole and splits Chinese into phrases.
- `motion/src/cards/` is one card view plus a registry. Every priority card lists `supportedLocales: ["en-US", "ru-RU", "zh-CN"]`.
- The scene catalog entries declare the same three locales. The Director still passes copy. Semantic labels are resolved inside the card.

## Asset search, next phase

`media/library/search.py` still matches English tags. Do not duplicate files or tags per language. A later pass can normalize a Russian or Chinese query into the existing English tag vocabulary before search. The photographs, icons, and clips stay shared.

## Terminology notes

Russian location uses «Расположение», not the calque «Локация». Yield uses «Доходность аренды». Buy versus rent uses «Купить» and «Арендовать». Chinese listing type for a condominium card uses «公寓».
