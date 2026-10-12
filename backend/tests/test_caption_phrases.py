"""Transcript phrase grouping for Remotion captions."""
from backend.caption_phrases import (
    caption_source_label,
    group_phrase_texts,
    phrases_from_transcript,
)


def test_english_groups_2_to_6_words():
    parts = group_phrase_texts(
        'Many people think that foreign investment companies only change the language',
        'en-US',
    )
    assert parts
    assert all(2 <= len(p.split()) <= 6 for p in parts)


def test_russian_groups_readable_phrases():
    parts = group_phrase_texts(
        'Планируете переезд, второй вид на жительство, с чего начать?',
        'ru-RU',
    )
    assert parts
    # Target 2–5; merge may stretch one clause to avoid dangling prepositions.
    assert all(2 <= len(p.split()) <= 8 for p in parts)
    assert not any(p.rstrip().endswith(' с') for p in parts)


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
