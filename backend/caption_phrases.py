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


_TRAIL_BAD = re.compile(
    r'\b(и|а|но|да|или|с|со|к|ко|у|о|об|от|по|за|для|на|из|'
    r'and|or|but|the|a|an|of|to|for|with|in|at|from|by|as|into|onto|than|need)\s*$',
    re.I,
)


def _normalize_caption_text(text: str) -> str:
    text = ' '.join(str(text or '').split())
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'\s+([?？!！.。,，])', r'\1', text)
    # Keep terminal .?! so a finished sentence cannot be glued to the next line.
    return text.strip().lstrip('.')


def _split_en_ru(text: str, *, lo: int, hi: int) -> list[str]:
    """Prefer clause boundaries; never end on dangling prepositions/conjunctions."""
    text = _normalize_caption_text(text)
    if not text:
        return []
    clauses = [c.strip() for c in re.split(r'[,，;；:]+|\s+[—–-]\s+', text) if c.strip()]
    if len(clauses) == 1:
        clauses = [text]
    phrases: list[str] = []
    for clause in clauses:
        words = _WORD.findall(clause)
        if not words:
            continue
        trailing = ''
        if clause[-1:] in '?？!！.。':
            trailing = clause[-1]
        if len(words) <= hi:
            phrases.append((' '.join(words) + trailing).strip())
            continue
        i = 0
        while i < len(words):
            remaining = len(words) - i
            take = min(hi, remaining)
            if remaining > hi and remaining - take < lo:
                take = max(lo, remaining // 2)
            # Avoid ending on a dangling function word — borrow one more if available.
            chunk_words = words[i:i + take]
            while take < remaining and _TRAIL_BAD.search(' '.join(chunk_words)) and take < hi + 2:
                take += 1
                chunk_words = words[i:i + take]
            # If still ends badly and we can shrink into previous… keep take>=lo.
            while take > lo and _TRAIL_BAD.search(' '.join(chunk_words)):
                take -= 1
                chunk_words = words[i:i + take]
            chunk = ' '.join(chunk_words)
            if i + take >= len(words) and trailing:
                chunk += trailing
            phrases.append(chunk.strip())
            i += take
    # Merge orphan phrases that still end badly into the next/previous.
    merged: list[str] = []
    for piece in phrases:
        if merged and (_TRAIL_BAD.search(merged[-1]) or len(merged[-1].split()) < lo):
            merged[-1] = f"{merged[-1]} {piece}".strip()
        elif _TRAIL_BAD.search(piece) and merged:
            merged[-1] = f"{merged[-1]} {piece}".strip()
        else:
            merged.append(piece)
    return merged or [text]


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
        elif merged and len(chunk) == 1:
            merged[-1] += chunk
        else:
            merged.append(chunk)
    # A one-character Chinese tail is an orphan line, not a phrase.
    if len(merged) >= 2 and len(merged[-1]) == 1:
        merged[-2] += merged[-1]
        merged.pop()
    return merged or [text]


def group_phrase_texts(text: str, locale: str | None = None) -> list[str]:
    bucket = _locale_bucket(locale)
    if bucket == 'zh' or _CJK.search(text or ''):
        return _split_zh(text)
    if bucket == 'ru':
        # Slightly longer windows reduce orphan words like «подачи» at segment tails.
        return _split_en_ru(text, lo=3, hi=7)
    # Mobile 1–2 lines: prefer fuller phrases; never end on dangling function words.
    return _split_en_ru(text, lo=3, hi=8)


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
        # Hold within the real speech window — do not invent empty caption plates in gaps.
        span = max(0.01, end - start)
        cursor = start
        weights = [max(1, len(_WORD.findall(p))) for p in pieces]
        weight_sum = sum(weights) or 1
        for index, piece in enumerate(pieces):
            share = weights[index] / weight_sum
            piece_end = end if index == len(pieces) - 1 else cursor + span * share
            piece_end = min(end, max(cursor + 0.45, piece_end))
            if duration_s is not None:
                piece_end = min(piece_end, float(duration_s))
            if piece_end <= cursor:
                continue
            text = _normalize_caption_text(piece)
            if not text:
                cursor = piece_end
                continue
            rows.append({
                'start': round(cursor, 3),
                'end': round(piece_end, 3),
                'text': text,
                'source': 'source_transcript',
            })
            cursor = piece_end
            if duration_s is not None and cursor >= float(duration_s):
                break
    # Drop flashes and incomplete crumbs; never keep empty / punctuation-only plates.
    from .director_execution import is_incomplete_heading
    _LEAD_CONJ = re.compile(
        r'^(и|а|но|да|или|чтобы|когда|если|and|but|or|the|a|an|with|for|of)\b',
        re.I,
    )
    cleaned = []
    for r in rows:
        text = _normalize_caption_text(r.get('text'))
        if not text or not _WORD.search(text):
            continue
        if (r['end'] - r['start']) < 0.35:
            continue
        if is_incomplete_heading(text):
            continue
        words = text.split()
        cjk_units = len(_CJK.findall(text))
        prev_text = cleaned[-1]['text'] if cleaned else ''
        gap = (r['start'] - cleaned[-1]['end']) if cleaned else 999.0
        # A Chinese sentence has no spaces, so split() is one token. Count glyphs.
        short = cjk_units <= 2 if cjk_units else len(words) <= 2
        combined_units = len(_CJK.findall(prev_text + text)) if (cjk_units or _CJK.search(prev_text)) else len((prev_text + ' ' + text).split())
        # Merge only within the same spoken breath — never glue across a pause.
        sentence_closed = bool(re.search(r"[.?!。？！]$", prev_text.strip()))
        can_merge = (
            cleaned
            and not sentence_closed
            and gap <= 0.35
            and (_LEAD_CONJ.match(text) or short or _TRAIL_BAD.search(prev_text))
            and combined_units <= 18
        )
        if can_merge:
            prev = cleaned[-1]
            prev['text'] = _normalize_caption_text(f"{prev['text']} {text}")
            prev['end'] = r['end']
            continue
        cleaned.append({**r, 'text': text})
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
