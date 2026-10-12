"""Transcript → Remotion caption phrases (no caption-pack, no LLM fragments).

Grouping targets phone-readable phrase lengths:
  en: 2–6 words · ru: 2–5 words · zh: natural CJK spans (no mid-word splits).
"""
from __future__ import annotations

import re
from typing import Any

_CJK = re.compile(r'[\u4e00-\u9fff]')
_WORD = re.compile(r"[\w%'’.-]+", re.UNICODE)
# Chinese phrase breaks after these punctuation marks / particles.
_ZH_BREAK = re.compile(r'([，。！？；、：]|呢|吗|吧|啊)(?!\s*$)')


def _locale_bucket(locale: str | None) -> str:
    raw = (locale or 'en').lower().replace('_', '-')
    if raw.startswith('zh'):
        return 'zh'
    if raw.startswith('ru'):
        return 'ru'
    return 'en'


def _row_text(row: dict, locale: str | None) -> str:
    """Locale-strict field pick — never silently serve EN speech under ru-RU."""
    from .locale_consistency import prefer_locale_field
    return prefer_locale_field(row, locale)


def _split_en_ru(text: str, *, lo: int, hi: int) -> list[str]:
    """Prefer clause boundaries; fall back to word windows. Never mid-word."""
    text = ' '.join(str(text or '').split())
    if not text:
        return []
    # Clause-first: split on punctuation, then pack clauses into phrase windows.
    clauses = [c.strip() for c in re.split(r'[,，;；:]+|\s+[—–-]\s+', text) if c.strip()]
    # Keep terminal ?! with previous clause.
    if len(clauses) == 1:
        clauses = [text]
    phrases: list[str] = []
    for clause in clauses:
        words = _WORD.findall(clause)
        if not words:
            continue
        # Preserve trailing punctuation from clause.
        trailing = ''
        if clause[-1:] in '?？!！.。':
            trailing = clause[-1]
        if len(words) <= hi:
            piece = ' '.join(words) + trailing
            phrases.append(piece)
            continue
        i = 0
        while i < len(words):
            remaining = len(words) - i
            take = hi if remaining > hi else remaining
            if remaining > hi and remaining - hi < lo:
                take = max(lo, remaining // 2)
            chunk = ' '.join(words[i:i + take])
            if i + take >= len(words) and trailing:
                chunk += trailing
            phrases.append(chunk)
            i += take
    return phrases or [text]


def _split_zh(text: str) -> list[str]:
    text = ''.join(str(text or '').split())
    if not text:
        return []
    parts = _ZH_BREAK.split(text)
    # re.split with capture keeps delimiters in odd slots when pattern has groups
    chunks: list[str] = []
    buf = ''
    for part in parts:
        if not part:
            continue
        buf += part
        if _ZH_BREAK.fullmatch(part) or len(buf) >= 8:
            if buf.strip():
                chunks.append(buf.strip())
            buf = ''
    if buf.strip():
        chunks.append(buf.strip())
    # Merge tiny leftovers into previous
    merged: list[str] = []
    for chunk in chunks:
        if merged and len(chunk) <= 1 and _CJK.match(chunk) is None:
            merged[-1] += chunk
        elif merged and len(chunk) < 2:
            merged[-1] += chunk
        else:
            merged.append(chunk)
    return merged or [text]


def group_phrase_texts(text: str, locale: str | None = None) -> list[str]:
    bucket = _locale_bucket(locale)
    if bucket == 'zh' or _CJK.search(text or ''):
        return _split_zh(text)
    if bucket == 'ru':
        return _split_en_ru(text, lo=2, hi=5)
    return _split_en_ru(text, lo=2, hi=6)


def phrases_from_transcript(
    transcript: list[dict] | None,
    *,
    locale: str | None = None,
    duration_s: float | None = None,
) -> list[dict[str, Any]]:
    """Return [{start, end, text, source}] in seconds for Remotion props."""
    rows = []
    for row in transcript or []:
        if hasattr(row, 'model_dump'):
            row = row.model_dump()
        if not isinstance(row, dict):
            continue
        try:
            start = float(row.get('start') or 0)
            end = float(row.get('end') or 0)
        except (TypeError, ValueError):
            continue
        text = _row_text(row, locale)
        if not text or end <= start:
            continue
        if duration_s is not None and start >= float(duration_s):
            continue
        if duration_s is not None:
            end = min(end, float(duration_s))
        pieces = group_phrase_texts(text, locale)
        if not pieces:
            continue
        # Prefer readable holds: at least ~0.85s per phrase; stretch the window if needed.
        min_piece = 0.85
        need = max(end - start, min_piece * len(pieces))
        span = need
        cursor = start
        for index, piece in enumerate(pieces):
            share = 1.0 / len(pieces)
            piece_end = (start + span) if index == len(pieces) - 1 else cursor + span * share
            piece_end = max(cursor + min_piece, piece_end)
            if duration_s is not None and piece_end > float(duration_s) and index == len(pieces) - 1:
                piece_end = float(duration_s)
            if piece_end <= cursor:
                continue
            rows.append({
                'start': round(cursor, 3),
                'end': round(piece_end, 3),
                'text': piece,
                'source': 'source_transcript',
            })
            cursor = piece_end
            if duration_s is not None and cursor >= float(duration_s):
                break
    # Drop flashes and incomplete crumbs ("and the", "Look at", "но не знаете").
    from .director_execution import is_incomplete_heading
    _LEAD_CONJ = re.compile(
        r'^(и|а|но|да|или|чтобы|когда|если|and|but|or|the|a|an|with|for|of)\b',
        re.I,
    )
    cleaned = []
    for r in rows:
        text = str(r.get('text') or '').strip()
        if (r['end'] - r['start']) < 0.35:
            continue
        if is_incomplete_heading(text):
            continue
        words = text.split()
        # Merge dangling conjunction-led crumbs into previous phrase.
        if cleaned and (_LEAD_CONJ.match(text) or len(words) <= 2):
            prev = cleaned[-1]
            prev['text'] = f"{prev['text']} {text}".strip()
            prev['end'] = r['end']
            continue
        cleaned.append(r)
    return cleaned


def caption_source_label(phrases: list[dict], *, dubbed: bool = False) -> str:
    if not phrases:
        return 'unavailable'
    if dubbed:
        return 'target_alignment'
    sources = {p.get('source') for p in phrases}
    if 'target_alignment' in sources:
        return 'target_alignment'
    if 'source_transcript' in sources:
        return 'source_transcript'
    return 'unavailable'
