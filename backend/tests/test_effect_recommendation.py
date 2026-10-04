from backend.effect_recommendation import apply_recommendation, proposal
from backend.manual import Edit
from backend.style_match import animate_for_render
from backend.timeline import motion_filter


def edit(**overrides):
    payload = {
        'clips': [{
            'id': 'one', 'start': 0, 'end': 6, 'text': '', 'approved': True,
            'zoom': 1, 'zoom_end': 1, 'x': 0.5, 'y': 0.5,
        }],
        'captions': [{'start': 0, 'end': 2, 'original': 'Hello', 'en': 'Hello', 'zh': '你好'}],
    }
    payload.update(overrides)
    return Edit.model_validate(payload).model_dump()


def test_a_still_picture_is_not_given_a_push_that_softens_the_frame():
    saved = edit()
    try:
        proposal(saved)
    except ValueError as exc:
        assert exc.args[0] == 'effect_unavailable'
    else:
        raise AssertionError('a still picture must not get a zoom, grade, vignette, or glow')
    pushed = apply_recommendation(saved, {
        'id': 'punch',
        'clips': {'one': {
            'zoom': 1, 'zoom_end': 1.26, 'x': 0.5, 'y': 0.5, 'x_end': 0.5, 'y_end': 0.5,
            'motion_seconds': 6,
        }},
        'edit': {},
    })
    held = animate_for_render(pushed)['clips'][0]
    assert held['zoom'] == 1 and held.get('zoom_end') is None
    assert 'zoompan=' not in motion_filter(held, 720, 1280, 6)
    split = animate_for_render({'clips': [{
        'start': 0, 'end': 6, 'zoom': 1, 'zoom_end': 1.26,
        'x': 0.5, 'x_end': 0.5, 'y': 0.5, 'y_end': 0.5, 'split': True,
    }]})['clips'][0]
    assert split.get('zoom_end') is None and split.get('split') is True


def test_a_moving_picture_is_not_given_a_grade():
    saved = edit(clips=[{
        'id': 'one', 'start': 0, 'end': 6, 'text': '', 'zoom': 1.15, 'zoom_end': 1.35,
        'x': 0.62, 'x_end': 0.38, 'y': 0.5,
    }])
    try:
        proposal(saved)
    except ValueError as exc:
        assert exc.args[0] == 'effect_unavailable'
    else:
        raise AssertionError('a measured move must not gain a grade')
    clip = saved['clips'][0]
    assert clip['zoom_end'] == 1.35
    assert 'zoompan=' in motion_filter(clip, 1080, 1920, 6)
    assert 'eq=contrast=' not in motion_filter(clip, 1080, 1920, 6)


def test_a_measured_grade_is_not_copied_onto_a_plain_shot():
    measured = {'brightness': 0.04, 'contrast': 1.2, 'saturation': 0.9, 'gamma': 1.05, 'rs': 0.08, 'gs': 0, 'bs': -0.04}
    saved = edit(clips=[
        {'id': 'held', 'start': 0, 'end': 2, 'text': '', 'zoom': 1.2, 'zoom_end': 1.4, 'x': 0.4, 'x_end': 0.6, 'y': 0.5, 'grade': measured},
        {'id': 'open', 'start': 2, 'end': 8, 'text': '', 'zoom': 1.1, 'zoom_end': 1.3, 'x': 0.3, 'x_end': 0.7, 'y': 0.5},
    ])
    try:
        proposal(saved)
    except ValueError as exc:
        assert exc.args[0] == 'effect_unavailable'
    else:
        raise AssertionError('the open shot must stay without a copied grade')
    assert saved['clips'][1].get('grade') is None


def test_vignette_and_card_motion_follow_when_the_picture_already_has_the_earlier_looks():
    grade = {'brightness': 0.02, 'contrast': 1.08, 'saturation': 1.1, 'gamma': 0.98, 'rs': 0.03, 'gs': 0, 'bs': -0.02}
    saved = edit(clips=[{
        'id': 'one', 'start': 0, 'end': 6, 'text': '', 'zoom': 1.15, 'zoom_end': 1.35,
        'x': 0.62, 'x_end': 0.38, 'y': 0.5, 'grade': grade,
        'card': {
            'kind': 'number', 'start': 0.2, 'end': 2, 'animation': 'none',
            'title': {'en': 'Price', 'zh': '价格'}, 'primary': {'en': '10%', 'zh': '10%'},
            'source': {'en': '—', 'zh': '—'},
        },
    }])
    cards = proposal(saved)
    assert cards['id'] == 'card_motion'
    assert cards['clips'] == {}
    assert cards['edit']['card_motion'] == 70
    applied = apply_recommendation(saved, cards)
    assert applied['card_motion'] == 70
    quieter = proposal({**applied, 'card_motion': 70})
    assert quieter['id'] == 'depth'
    assert quieter['edit']['animation_depth'] == 50
    shaped = apply_recommendation(applied, quieter)
    assert shaped['animation_depth'] == 50 and shaped['card_motion'] == 70
    assert applied['clips'][0]['zoom_end'] == 1.35
    assert 'vignette=' not in motion_filter(applied['clips'][0], 1080, 1920, 6)
    assert 'unsharp=' not in motion_filter(applied['clips'][0], 1080, 1920, 6)


def test_slider_picture_without_cards_still_offers_a_shorter_animation():
    saved = edit(card_motion=100, presentation_prompt='Будет добавлена анимация на 100% длины ролика.')
    picked = proposal(saved)
    assert picked['id'] == 'card_motion'
    assert picked['edit']['card_motion'] == 70


def test_locked_and_excluded_pieces_stay_untouched_and_a_closed_picture_fails():
    saved = edit(clips=[
        {'id': 'kept', 'start': 0, 'end': 3, 'text': '', 'locked': True, 'zoom': 1, 'zoom_end': 1},
        {'id': 'out', 'start': 3, 'end': 6, 'text': '', 'approved': False, 'zoom': 1, 'zoom_end': 1},
        {'id': 'open', 'start': 6, 'end': 9, 'text': '', 'zoom': 1, 'zoom_end': 1},
    ])
    try:
        proposal(saved)
    except ValueError as exc:
        assert exc.args[0] == 'effect_unavailable'
    else:
        raise AssertionError('a still open piece must not receive a softening look')
    assert saved['clips'][0]['zoom_end'] == 1
    assert saved['clips'][1]['approved'] is False
    closed = edit(clips=[{'id': 'out', 'start': 0, 'end': 4, 'text': '', 'approved': False}])
    try:
        proposal(closed)
    except ValueError as exc:
        assert exc.args[0] == 'no_open_picture'
    else:
        raise AssertionError('closed picture must not invent a look')
