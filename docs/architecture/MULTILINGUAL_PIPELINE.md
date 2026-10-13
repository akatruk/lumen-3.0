# Multilingual pipeline

## CURRENT STATE

- Locales: `ru-RU`, `en-US`, `zh-CN` (`motion/src/localization/`, backend `language.py`)
- Cards: `motion/src/cards/` registry + validation
- Voice: `resolve_voice` — fails closed on `VOICE_SETUP_REQUIRED`
- Captions (V5/V6): **transcript-driven** — `backend/caption_phrases.py` groups source / target-aligned speech; Remotion reads `visualPlan.captions`. Caption-pack strings are legacy fallback only. Hypit path still uses ASS from studio plan.
- **V6 locale gate:** `backend/locale_consistency.py` — captions/cards/headlines must match `project.language` script; mismatched captions are dropped (never silent EN+RU mix).
- Library search expands RU/ZH phrases to English tags
- **V14 motion labels** are props (`locale` + localized strings), one component for ru-RU / en-US / zh-CN. `AutoFitText` keeps EN/RU words whole and wraps CJK. No per-language component copies and no text baked into PNG. V15 reuses those props. `formatMetric` groups currency for en-US, ru-RU, and zh-CN and prints a unit only when the payload has one.

## Rules

- Language is chosen on the project / Create video — not by creating separate projects
- Source transcript is cached and reused across target languages; changing language does not retranscribe
- Phrase groups: EN 2–6 words, RU 2–5, ZH natural CJK spans; never mid-word splits; do not isolate CJK punctuation
- Never invent statistics the source did not state
- Never silently fall back to the wrong voice
- Important text is Remotion text, not pixels in generated images
- Dubbed versions: target script + target audio alignment → `captionSource=target_alignment`
