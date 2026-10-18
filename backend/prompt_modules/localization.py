"""Localization prompt module (RU / EN / ZH).

Refines language, voice, captions, cards, and typography only. Does not change
core QUALITY ENFORCEMENT in assembly_prompt.txt.
"""
from __future__ import annotations

from .base import ModuleAttachment

ID = 'localization'
VERSION = '1.0.0'
DOMAIN = 'localization'

# Shared rules for every targetLocale. Locale-specific wording comes from language.py.
_SHARED = """--- MODULE LOCALIZATION RULES ---

Single targetLocale for voiceover AND all viewer-facing text in this run.

Translate / localize every visible surface into that locale:
cards, headlines, diagrams, insets, captions, kinetic type, process labels,
comparison columns, timeline marks, CTA, supporting copy.

Keep facts and source meaning. Do not invent claims, numbers, or eligibility.
Timing for captions, cards, and motion follows the target-language voiceover —
never reuse source-language word timestamps after a dub.

No accidental language mix on screen or in speech (brands / proper nouns OK).
Use language-appropriate fonts, wrapping, and typography profiles
(latin / cyrillic / cjk). Prefer language-neutral library plates; if an asset
has baked-in text, it must match targetLocale or be omitted.

UI language of Lumen Studio is independent of this video language.
Missing target voice is a hard error (VOICE_SETUP_REQUIRED) — never silently
swap to another language.

--- END MODULE LOCALIZATION RULES ---"""


class LocalizationModule:
    id = ID
    version = VERSION
    domain = DOMAIN

    def applicable(self, manual: dict) -> bool:
        from ..language import LanguageError, resolve_locale
        raw = (manual or {}).get('language')
        if not raw:
            return False
        try:
            return resolve_locale(raw) is not None
        except LanguageError:
            return False

    def attach(self, manual: dict) -> ModuleAttachment:
        from ..language import (
            LanguageError,
            audio_instruction,
            build_language_directive,
            config_for,
            director_context_blocks,
            resolve_locale,
            short_code,
        )
        from ..library_clips import media_block

        locale = resolve_locale((manual or {}).get('language'))
        if not locale:
            raise LanguageError('unsupported_language')
        cfg = config_for(locale)
        cards, motion, media, context = director_context_blocks(locale)
        listed = media_block()
        if listed:
            media = listed
        audio = audio_instruction(manual, locale)
        directive = build_language_directive(locale)
        instructions = "\n\n".join((
            f"--- MODULE: {ID} @{VERSION} ---",
            _SHARED,
            directive,
            audio,
            cards,
            motion,
            media,
            context,
            f"--- END MODULE: {ID} ---",
        ))
        # Core QUALITY ENFORCEMENT already forbids inventing facts / replacing the
        # host video. Localization only refines language — no hard conflict.
        conflicts: tuple[str, ...] = ()
        return ModuleAttachment(
            id=ID,
            version=VERSION,
            domain=DOMAIN,
            instructions=instructions,
            conflicts=conflicts,
            run_params={
                'targetLocale': locale,
                'localeCode': short_code(locale),
                'typographyProfile': cfg['typographyProfile'],
                'voiceLocale': cfg['voiceLocale'],
                'defaultVoiceId': cfg['voice'],
                'promptName': cfg['promptName'],
            },
        )
