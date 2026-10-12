from backend.locale_consistency import (
    prefer_locale_field,
    text_matches_locale,
    validate_viewer_locale,
)
from backend.caption_phrases import phrases_from_transcript
from backend.director_semantics import enrich_plan_from_transcript, motion_diversity_summary


def test_ru_rejects_english_caption_field():
    row = {
        'start': 0, 'end': 2,
        'en': 'Many people think that',
        'ru': 'Many people think that',
        'original': 'Many people think that',
    }
    assert prefer_locale_field(row, 'ru-RU') == ''
    assert phrases_from_transcript([row], locale='ru-RU') == []


def test_ru_accepts_cyrillic():
    row = {
        'start': 0, 'end': 3,
        'ru': 'Планируете переезд, второй вид на жительство?',
        'original': 'Планируете переезд, второй вид на жительство?',
        'en': '',
    }
    assert text_matches_locale(row['ru'], 'ru-RU')
    phrases = phrases_from_transcript([row], locale='ru-RU', duration_s=20)
    assert phrases
    assert all(text_matches_locale(p['text'], 'ru-RU') for p in phrases)


def test_validate_blocks_en_captions_with_ru_cards():
    report = validate_viewer_locale(
        locale='ru-RU',
        captions=[{'text': 'Many people think'}],
        cards=[{'title': 'Цели', 'explanation': 'куда и зачем'}],
    )
    assert report['ok'] is False
    assert report['captionLocaleOk'] is False


def test_enrich_sets_hook_headline_and_diverse_layouts():
    plan = {
        'language': 'ru-RU',
        'scenes': [
            {'sceneId': 'hook', 'speaker': {'layout': 'speaker_medium', 'framing': 'fullscreen'}, 'execution': {}, 'typography': {}},
            {'sceneId': 'residency', 'speaker': {'layout': 'speaker_split_right', 'framing': 'split'}, 'execution': {}, 'typography': {}, 'query': None},
            {'sceneId': 'consult', 'speaker': {'layout': 'speaker_with_media', 'framing': 'pip'}, 'execution': {}, 'typography': {}},
            {'sceneId': 'beside', 'speaker': {'layout': 'speaker_split_left', 'framing': 'split'}, 'execution': {}, 'typography': {}},
            {'sceneId': 'steps', 'speaker': {'layout': 'speaker_with_diagram', 'framing': 'pip'}, 'execution': {}, 'typography': {}},
            {'sceneId': 'return', 'speaker': {'layout': 'speaker_fullscreen', 'framing': 'fullscreen'}, 'execution': {}, 'typography': {}},
        ],
    }
    transcript = [{
        'start': 0, 'end': 6,
        'ru': 'Планируете переезд, второй вид на жительство или новый международный статус?',
        'original': 'Планируете переезд, второй вид на жительство или новый международный статус?',
    }]
    out = enrich_plan_from_transcript(plan, transcript, locale='ru-RU')
    hook = next(s for s in out['scenes'] if s['sceneId'] == 'hook')
    assert 'переезд' in (hook.get('typography') or {}).get('headline', '').lower() or 'Планируете' in (hook.get('execution') or {}).get('headline', '')
    beside = next(s for s in out['scenes'] if s['sceneId'] == 'beside')
    assert (beside.get('typography') or {}).get('cards')
    report = motion_diversity_summary(out['scenes'])
    assert report['uniqueLayouts'] >= 3
