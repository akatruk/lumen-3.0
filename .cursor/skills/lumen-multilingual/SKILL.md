---
name: lumen-multilingual
description: >-
  RU/EN/ZH localization for Lumen: cards, AutoFitText, voice mapping, and
  target-language timing. Never silent wrong-voice fallback.
---

# Multilingual

Locales: `ru-RU`, `en-US`, `zh-CN`.

- Project create does not run AI; language/voice apply at Create video. Source transcript cache is language-independent.
- Motion cards: `motion/src/cards/`, `motion/src/localization/`
- Backend voice: `backend/language.py` — `VOICE_SETUP_REQUIRED` fails closed
- Hypit prompt module: `backend/prompt_modules/localization.py` attached when
  `manual.language` is set (`assemble_hypit_prompt`). Single `targetLocale` for
  VO + all visible text; timing from target VO; cache under
  `data/<pid>/localization/<locale>/`.
- EN/RU: never split words; ZH: CJK wrap without spaces
- Library queries expand to English tags; binaries stay language-neutral
- Remotion DirectorV3 caption *strings* may still be RU-pack until transcript
  wiring — mark EN/ZH string checks unavailable there; Hypit path uses modules.
