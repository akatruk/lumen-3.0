---
name: lumen-multilingual
description: >-
  RU/EN/ZH localization for Lumen: cards, AutoFitText, voice mapping, and
  target-language timing. Never silent wrong-voice fallback.
---

# Multilingual

Locales: `ru-RU`, `en-US`, `zh-CN`.

- Motion cards: `motion/src/cards/`, `motion/src/localization/`
- Backend voice: `backend/language.py` — `VOICE_SETUP_REQUIRED` fails closed
- EN/RU: never split words; ZH: CJK wrap without spaces
- Library queries expand to English tags; binaries stay language-neutral
