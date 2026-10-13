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
- Remotion captions (V5/V6/V11.1): transcript → `backend/caption_phrases.py` (EN ~3–8 words, no dangling `at`/`of`; RU 3–7; ZH CJK). No cross-pause merges (&gt;0.35s). Prefer `visualPlan.captions`; pack strings are legacy fallback only. Dubbed: target alignment → `captionSource=target_alignment`.
- V6: `locale_consistency` rejects wrong-script fields; do not fall back EN→RU. Cards/headlines must match `project.language`.
- V11.1 factual cards: localized titles (`≥3 Shareholders` / `≥3 акционеров` / `≥3名股东`) keep the **same numeral** across locales.
