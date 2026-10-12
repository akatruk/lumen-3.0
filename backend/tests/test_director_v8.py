from backend.director_v8 import (
    expand_plan_for_duration,
    filter_locale_transcript,
    fill_media_for_scenes,
)


def test_filter_drops_english_glitch_in_ru():
    rows = [
        {'start': 0, 'end': 5, 'ru': 'Планируете переезд сейчас', 'original': 'Планируете переезд сейчас'},
        {'start': 5, 'end': 8, 'en': 'I think this is shit', 'original': 'I think this is shit', 'ru': ''},
        {'start': 8, 'end': 12, 'text': 'Мы помогаем клиентам подобрать программу', 'ru': 'Мы помогаем клиентам подобрать программу'},
    ]
    cleaned = filter_locale_transcript(rows, 'ru-RU')
    assert len(cleaned) == 2
    assert all('shit' not in (r.get('ru') or r.get('original') or '') for r in cleaned)


def test_expand_60s_has_ten_beats_and_motion():
    plan = {
        'language': 'ru-RU',
        'visualSeed': 1,
        'scenes': [
            {'sceneId': 'hook', 'speaker': {}, 'background': {}, 'typography': {'headline': 'Планируете переезд'}, 'execution': {}},
            {'sceneId': 'beside', 'speaker': {}, 'background': {}, 'typography': {'cards': [{'title': 'Цели', 'explanation': 'куда'}]}, 'execution': {}},
            {'sceneId': 'steps', 'speaker': {}, 'background': {}, 'typography': {'stepsTitle': 'Сопровождение', 'steps': ['A', 'B', 'C']}, 'execution': {}},
        ],
    }
    transcript = [
        {'start': 0, 'end': 6, 'ru': 'Планируете переезд, второй вид на жительство', 'original': 'Планируете переезд, второй вид на жительство'},
        {'start': 7, 'end': 15, 'ru': 'Мы помогаем подобрать программу с учетом семьи и бюджета', 'original': 'Мы помогаем подобрать программу с учетом семьи и бюджета'},
        {'start': 16, 'end': 25, 'ru': 'Мы сопровождаем весь процесс от консультации до документов', 'original': 'Мы сопровождаем весь процесс от консультации до документов'},
    ]
    out = expand_plan_for_duration(plan, duration_seconds=60, transcript=transcript, locale='ru-RU')
    assert out['form'] == 'long60'
    assert len(out['scenes']) == 10
    assert out['shotPlanVersion'] == 'v8'
    assert out['antiRepetition']['pass'] is True
    assert out['semanticMotionAudit']['resolvedCount'] >= 3
    ids = [s['sceneId'] for s in out['scenes']]
    assert ids[0] == 'hook' and ids[-1] == 'return'
    assert any(s.get('semanticMotion', {}).get('staged') or s.get('semanticMotion', {}).get('file') for s in out['scenes'])


def test_short_form_unchanged_count():
    plan = {
        'language': 'ru-RU',
        'scenes': [
            {'sceneId': sid, 'speaker': {'layout': 'speaker_fullscreen', 'framing': 'fullscreen'}, 'background': {}, 'typography': {}, 'execution': {}, 'shotPlan': {}}
            for sid in ('hook', 'residency', 'consult', 'beside', 'steps', 'return')
        ],
    }
    out = expand_plan_for_duration(plan, duration_seconds=20, transcript=[], locale='ru-RU')
    assert out['form'] == 'short'
    assert len(out['scenes']) == 6
