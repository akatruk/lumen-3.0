"""One authoritative viewer locale for captions, cards, headlines, CTA.

Rejects silent language mixing (e.g. English speech captions under ru-RU cards).
"""
from __future__ import annotations

import re
from typing import Any

_CYR = re.compile(r'[\u0400-\u04FF]')
_CJK = re.compile(r'[\u4e00-\u9fff]')
_LAT = re.compile(r'[A-Za-z]')


def locale_bucket(locale: str | None) -> str:
    raw = (locale or 'en').lower().replace('_', '-')
    if raw.startswith('zh'):
        return 'zh'
    if raw.startswith('ru'):
        return 'ru'
    return 'en'


def script_of(text: str | None) -> str:
    s = str(text or '')
    cyr = len(_CYR.findall(s))
    cjk = len(_CJK.findall(s))
    lat = len(_LAT.findall(s))
    total = cyr + cjk + lat
    if total == 0:
        return 'empty'
    if cjk >= max(cyr, lat) and cjk > 0:
        return 'cjk'
    if cyr >= lat and cyr > 0:
        return 'cyrillic'
    if lat > 0 and cyr == 0 and cjk == 0:
        return 'latin'
    if lat and cyr:
        return 'mixed'
    return 'latin'


def text_matches_locale(text: str | None, locale: str | None) -> bool:
    """True when the visible script matches the target locale (proper nouns OK as latin islands)."""
    bucket = locale_bucket(locale)
    kind = script_of(text)
    if kind == 'empty':
        return False
    if bucket == 'ru':
        # Require Cyrillic dominance; allow short latin brands inside.
        return kind in ('cyrillic', 'mixed') and len(_CYR.findall(str(text or ''))) >= 3
    if bucket == 'zh':
        return kind == 'cjk' and len(_CJK.findall(str(text or ''))) >= 2
    # en-US: latin; reject Cyrillic/CJK-dominant strings
    return kind == 'latin'


def prefer_locale_field(row: dict, locale: str | None) -> str:
    """Pick transcript field for locale without falling back to another language's speech."""
    bucket = locale_bucket(locale)
    order = {
        'ru': ('ru', 'original', 'text'),
        'zh': ('zh', 'original', 'text'),
        'en': ('en', 'original', 'text'),
    }[bucket]
    for key in order:
        raw = ' '.join(str(row.get(key) or '').split())
        if not raw or '[segment' in raw.lower():
            continue
        if text_matches_locale(raw, locale):
            return raw
    return ''


def validate_viewer_locale(
    *,
    locale: str,
    captions: list[dict] | None = None,
    cards: list[dict] | None = None,
    headlines: list[str] | None = None,
) -> dict[str, Any]:
    """Return {ok, issues[], captionLocaleOk, cardLocaleOk}."""
    issues: list[str] = []
    cap_ok = True
    for row in captions or []:
        text = row.get('text') if isinstance(row, dict) else str(row)
        if text and not text_matches_locale(text, locale):
            cap_ok = False
            issues.append(f'caption_locale_mismatch:{text[:48]}')
            break
    card_ok = True
    for card in cards or []:
        for key in ('title', 'explanation', 'text', 'headline'):
            text = (card or {}).get(key) if isinstance(card, dict) else None
            if text and not text_matches_locale(text, locale):
                card_ok = False
                issues.append(f'card_locale_mismatch:{text[:48]}')
                break
        if not card_ok:
            break
    for headline in headlines or []:
        if headline and not text_matches_locale(headline, locale):
            issues.append(f'headline_locale_mismatch:{headline[:48]}')
    ok = not issues
    return {
        'ok': ok,
        'locale': locale,
        'captionLocaleOk': cap_ok,
        'cardLocaleOk': card_ok,
        'issues': issues,
    }
