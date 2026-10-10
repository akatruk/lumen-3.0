# Multilingual pipeline

## CURRENT STATE

- Locales: `ru-RU`, `en-US`, `zh-CN` (`motion/src/localization/`, backend `language.py`)
- Cards: `motion/src/cards/` registry + validation
- Voice: `resolve_voice` — fails closed on `VOICE_SETUP_REQUIRED`
- Captions: studio plan transcript → FFmpeg ASS for Hypit path; Remotion `AutoFitText` for Director V3
- Library search expands RU/ZH phrases to English tags

## Rules

- Never split Latin/Cyrillic words; CJK wraps without inserted spaces
- Never invent statistics the source did not state
- Never silently fall back to the wrong voice
- Important text is Remotion text, not pixels in generated images
