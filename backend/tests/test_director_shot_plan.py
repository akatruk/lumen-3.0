from backend.director_shot_plan import apply_shot_plans, anti_repeat_ok, extract_keywords, motion_usage_report
from backend.caption_phrases import phrases_from_transcript, group_phrase_texts
from backend.director_semantics import enrich_plan_from_transcript


def test_shot_plan_forces_return_fullscreen_and_varied_framing():
    plan = {
        'language': 'ru-RU',
        'scenes': [
            {'sceneId': 'hook', 'speaker': {}, 'background': {}, 'typography': {}, 'execution': {}},
            {'sceneId': 'residency', 'speaker': {}, 'background': {}, 'typography': {}, 'execution': {}},
            {'sceneId': 'consult', 'speaker': {}, 'background': {}, 'typography': {}, 'execution': {}},
            {'sceneId': 'beside', 'speaker': {}, 'background': {}, 'typography': {}, 'execution': {}},
            {'sceneId': 'steps', 'speaker': {}, 'background': {}, 'typography': {}, 'execution': {}},
            {'sceneId': 'return', 'speaker': {}, 'background': {}, 'typography': {}, 'execution': {}},
        ],
    }
    out = apply_shot_plans(plan, locale='ru-RU', transcript_text='Планируете переезд и программу')
    framings = [(s.get('speaker') or {}).get('framing') for s in out['scenes']]
    assert framings[0] == 'fullscreen'
    assert framings[-1] == 'fullscreen'
    assert framings.count('split') < 3
    assert out['antiRepetition']['pass'] is True
    assert all(s.get('shotPlan') for s in out['scenes'])
    report = motion_usage_report(out)
    assert report['uniqueLayouts'] >= 4
    assert report['choreographyActions'] >= 10


def test_keywords_not_caption_crumbs():
    keys = extract_keywords('Планируете переезд, второй вид на жительство и бюджет семьи')
    ids = {k['id'] for k in keys}
    assert 'relocation' in ids
    assert 'budget' in ids or 'family' in ids


def test_captions_do_not_end_on_dangling_preposition():
    phrases = group_phrase_texts(
        'Мы помогаем клиентам подобрать подходящую иммиграционную программу с учетом их целей',
        'ru-RU',
    )
    for p in phrases:
        assert not p.rstrip().endswith(' с')
        assert not p.rstrip().endswith(' или')


def test_enrich_wires_shot_plans():
    plan = {
        'language': 'ru-RU',
        'scenes': [
            {'sceneId': 'hook', 'speaker': {'layout': 'speaker_medium', 'framing': 'fullscreen'}, 'execution': {}, 'typography': {}},
            {'sceneId': 'residency', 'speaker': {'layout': 'speaker_split_right', 'framing': 'split'}, 'execution': {}, 'typography': {}},
            {'sceneId': 'consult', 'speaker': {'layout': 'speaker_with_media', 'framing': 'pip'}, 'execution': {}, 'typography': {}},
            {'sceneId': 'beside', 'speaker': {'layout': 'speaker_split_left', 'framing': 'split'}, 'execution': {}, 'typography': {}},
            {'sceneId': 'steps', 'speaker': {'layout': 'speaker_with_diagram', 'framing': 'pip'}, 'execution': {}, 'typography': {}},
            {'sceneId': 'return', 'speaker': {'layout': 'speaker_fullscreen', 'framing': 'fullscreen'}, 'execution': {}, 'typography': {}},
        ],
    }
    transcript = [{
        'start': 0, 'end': 6,
        'ru': 'Планируете переезд, второй вид на жительство?',
        'original': 'Планируете переезд, второй вид на жительство?',
    }]
    out = enrich_plan_from_transcript(plan, transcript, locale='ru-RU')
    assert out.get('shotPlanVersion') == 'v7'
    assert (out['scenes'][-1].get('speaker') or {}).get('framing') == 'fullscreen'
    assert anti_repeat_ok(out['scenes'])['pass']


def test_empty_caption_text_filtered():
    rows = phrases_from_transcript([
        {'start': 0, 'end': 2, 'ru': '...', 'original': '...'},
        {'start': 2, 'end': 5, 'ru': 'Планируете переезд сейчас', 'original': 'Планируете переезд сейчас'},
    ], locale='ru-RU', duration_s=20)
    assert all(r['text'].strip() for r in rows)
    assert all(r['end'] <= 5.01 for r in rows)
