"""Transcript phrase grouping for Remotion captions."""
from backend.caption_phrases import (
    caption_source_label,
    group_phrase_texts,
    phrases_from_transcript,
)


def test_finished_sentence_does_not_swallow_the_next_line():
    rows = phrases_from_transcript([
        {"start": 4.0, "end": 8.5, "text": "Which documents does a second passport actually require?"},
        {"start": 8.5, "end": 12.0, "text": "The filing fee is 500 dollars."},
    ], locale="en-US", duration_s=16)
    texts = [row["text"] for row in rows]
    assert not any("require" in text and "500" in text for text in texts)
    assert any(text.startswith("The filing fee") for text in texts)
    fee = next(text for text in texts if text.startswith("The filing fee"))
    assert fee.rstrip().endswith(".")
    assert "afraid" not in fee


def test_abutting_finished_sentences_stay_separate():
    en = phrases_from_transcript([
        {"start": 8.5, "end": 12.0, "text": "The filing fee is 500 dollars."},
        {"start": 12.0, "end": 16.0, "text": "I was afraid we would miss the deadline."},
    ], locale="en-US", duration_s=16)
    en_texts = [row["text"] for row in en]
    assert any(text.startswith("The filing fee") and "afraid" not in text for text in en_texts)
    assert any("afraid" in text and "500" not in text for text in en_texts)
    ru = phrases_from_transcript([
        {"start": 9.0, "end": 13.0, "text": "Срок проверки — шесть месяцев."},
        {"start": 13.0, "end": 17.0, "text": "Это риск, если пропустить срок."},
    ], locale="ru-RU", duration_s=17)
    ru_texts = [row["text"] for row in ru]
    assert any("месяцев" in text and "риск" not in text for text in ru_texts)
    assert any("риск" in text and "месяцев" not in text for text in ru_texts)


def test_english_groups_readable_mobile_phrases():
    parts = group_phrase_texts(
        'Many people think that foreign investment companies only change the language',
        'en-US',
    )
    assert parts
    assert all(2 <= len(p.split()) <= 10 for p in parts)
    # Never leave a dangling preposition on the phone caption.
    assert not any(p.rstrip().lower().endswith(' at') for p in parts)


def test_origin1_shareholder_phrase_stays_intact():
    rows = phrases_from_transcript([
        {
            'start': 22.66, 'end': 26.06,
            'en': 'Ordinary Thai companies usually need at least three shareholders',
        },
        {
            'start': 29.26, 'end': 34.46,
            'en': 'In other words, the control power is locked in from the moment of the investment',
        },
    ], locale='en-US', duration_s=60)
    blob = ' | '.join(r['text'] for r in rows)
    assert 'three shareholders' in blob.lower()
    # Must not glue shareholder line onto control-power across the pause.
    assert not any(
        'three shareholders' in r['text'].lower() and 'control power' in r['text'].lower()
        for r in rows
    )
    assert not any(r['text'].rstrip().lower().endswith(' at') for r in rows)


def test_russian_groups_readable_phrases():
    parts = group_phrase_texts(
        'Планируете переезд, второй вид на жительство, с чего начать?',
        'ru-RU',
    )
    assert parts
    # Target 2–5; merge may stretch one clause to avoid dangling prepositions.
    assert all(2 <= len(p.split()) <= 8 for p in parts)
    assert not any(p.rstrip().endswith(' с') for p in parts)


def test_unpunctuated_chinese_segment_does_not_become_one_caption():
    text = "现在办移民最难的早就不是你手头有没有钱而是你怎么向官方及其严苛的证明这笔钱究竟是从哪来的"
    words = []
    cursor = 0.0
    for char in text:
        words.append({"text": char, "start": round(cursor, 3), "end": round(cursor + 0.24, 3)})
        cursor += 0.24
    rows = phrases_from_transcript([
        {"id": "segment_001", "start": 0, "end": cursor, "text": text, "words": words},
    ], locale="zh-CN", duration_s=cursor)
    assert rows
    assert all(len(row["text"]) <= 12 for row in rows)
    assert rows[0]["end"] < 4
    assert abs(rows[0]["end"] - words[len(rows[0]["text"]) - 1]["end"]) < 0.05
    assert rows[-1]["end"] < cursor


def test_chinese_does_not_leave_a_one_character_line():
    parts = group_phrase_texts('买房送身份听起来是不是特别诱人', 'zh-CN')
    assert parts
    assert all(len(part) >= 2 for part in parts)


def test_chinese_keeps_cjk_phrase_boundaries():
    parts = group_phrase_texts('计划搬迁吗，第二居留身份从何开始？', 'zh-CN')
    assert parts
    assert all(parts)
    joined = ''.join(parts)
    assert '计划' in joined and '居留' in joined


def test_phrases_from_transcript_skips_placeholders():
    rows = phrases_from_transcript([
        {'start': 0, 'end': 2, 'en': '[segment 1]', 'original': '[segment 1]'},
        {'start': 2, 'end': 6, 'en': 'Capital must be paid before banking opens', 'original': 'x'},
    ], locale='en-US', duration_s=20)
    assert rows
    assert all('[segment' not in r['text'] for r in rows)
    assert caption_source_label(rows) == 'source_transcript'


def test_chinese_captions_use_the_speech_not_the_english_gloss():
    rows = phrases_from_transcript([
        {
            'start': 0, 'end': 4,
            'zh': '很多人以为外资公司只是换了一种语言',
            'original': '很多人以为外资公司只是换了一种语言',
            'en': 'Many people think that foreign investment companies only change the language',
        },
    ], locale='zh-CN', duration_s=20)
    assert rows
    assert '很多人' in rows[0]['text']
    assert 'Many people' not in rows[0]['text']


def test_attach_on_resolve_plan():
    from backend import remotion_engine
    plan = remotion_engine.resolve_scene_plan(
        visual_plan={'visualSeed': 1, 'language': 'en-US', 'scenes': []},
        locale='en-US',
        duration_seconds=20,
        generation_id='cap_test',
    )
    plan = remotion_engine.attach_transcript_captions(
        plan,
        [{'start': 0, 'end': 4, 'en': 'Foreign investment rules differ in Thailand'}],
        locale='en-US',
    )
    assert plan['renderer'] == 'remotion'
    assert plan['captionSource'] == 'source_transcript'
    assert plan['captions']
    assert plan['executionValidation'] in ('passed', 'repaired')
