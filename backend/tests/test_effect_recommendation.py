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


def test_a_still_picture_gets_one_push_the_renderer_keeps():
    saved = edit()
    pick = proposal(saved)
    assert pick['id'] == 'punch'
    assert 'transition' not in pick['clips']['one']
    applied = apply_recommendation(saved, pick)
    clip = applied['clips'][0]
    assert clip['approved'] is True
    assert clip['zoom'] == 1
    assert clip['zoom_end'] == 1.26
    assert clip['x'] == clip['y'] == clip['x_end'] == clip['y_end'] == 0.5
    assert 'zoompan=' in motion_filter(clip, 1080, 1920, 6)
    assert animate_for_render(applied)['clips'][0]['zoom_end'] == 1.26


def test_a_moving_picture_gets_a_grade_the_filter_applies():
    saved = edit(clips=[{
        'id': 'one', 'start': 0, 'end': 6, 'text': '', 'zoom': 1.15, 'zoom_end': 1.35,
        'x': 0.62, 'x_end': 0.38, 'y': 0.5,
    }])
    pick = proposal(saved)
    assert pick['id'] == 'grade'
    applied = apply_recommendation(saved, pick)
    clip = applied['clips'][0]
    assert clip['grade']['contrast'] == 1.08
    assert clip['zoom_end'] == 1.35
    chain = motion_filter(clip, 1080, 1920, 6)
    assert 'eq=contrast=' in chain and 'colorbalance=' in chain


def test_a_measured_grade_is_copied_instead_of_inventing_one():
    measured = {'brightness': 0.04, 'contrast': 1.2, 'saturation': 0.9, 'gamma': 1.05, 'rs': 0.08, 'gs': 0, 'bs': -0.04}
    saved = edit(clips=[
        {'id': 'held', 'start': 0, 'end': 2, 'text': '', 'zoom': 1.2, 'zoom_end': 1.4, 'x': 0.4, 'x_end': 0.6, 'y': 0.5, 'grade': measured},
        {'id': 'open', 'start': 2, 'end': 8, 'text': '', 'zoom': 1.1, 'zoom_end': 1.3, 'x': 0.3, 'x_end': 0.7, 'y': 0.5},
    ])
    pick = proposal(saved)
    assert pick['id'] == 'grade'
    assert 'held' not in pick['clips']
    assert pick['clips']['open']['grade']['rs'] == 0.08
    assert pick['clips']['open']['grade'] is not measured


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
    vignette = proposal(saved)
    assert vignette['id'] == 'vignette'
    shaded = apply_recommendation(saved, vignette)
    assert 'vignette=' in motion_filter(shaded['clips'][0], 1080, 1920, 6)
    glow = proposal(shaded)
    assert glow['id'] == 'glow'
    lit = apply_recommendation(shaded, glow)
    assert 'unsharp=' in motion_filter(lit['clips'][0], 1080, 1920, 6)
    cards = proposal(lit)
    assert cards['id'] == 'card_motion'
    assert cards['clips'] == {}
    assert cards['edit']['card_motion'] == 70
    assert apply_recommendation(lit, cards)['card_motion'] == 70


def test_locked_and_excluded_pieces_stay_untouched_and_a_closed_picture_fails():
    saved = edit(clips=[
        {'id': 'kept', 'start': 0, 'end': 3, 'text': '', 'locked': True, 'zoom': 1, 'zoom_end': 1},
        {'id': 'out', 'start': 3, 'end': 6, 'text': '', 'approved': False, 'zoom': 1, 'zoom_end': 1},
        {'id': 'open', 'start': 6, 'end': 9, 'text': '', 'zoom': 1, 'zoom_end': 1},
    ])
    pick = proposal(saved)
    assert list(pick['clips']) == ['open']
    applied = apply_recommendation(saved, pick)
    assert applied['clips'][0]['zoom_end'] == 1
    assert applied['clips'][1]['approved'] is False
    closed = edit(clips=[{'id': 'out', 'start': 0, 'end': 4, 'text': '', 'approved': False}])
    try:
        proposal(closed)
    except ValueError as exc:
        assert exc.args[0] == 'no_open_picture'
    else:
        raise AssertionError('closed picture must not invent a look')
