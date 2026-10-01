from backend.hypit_picture import _broll_layers
from backend.presentation_graphics import animation_brief
from backend.manual import Edit
from backend.thematic_broll import relevant, windows


def test_motion_percent_names_the_card_travel_and_the_inserts():
    quiet = animation_brief(Edit.model_validate({
        'clips': [{'start': 0, 'end': 60}],
        'animation_motion': 40,
    }))
    full = animation_brief(Edit.model_validate({
        'clips': [{'start': 0, 'end': 60}],
        'animation_motion': 100,
    }))
    assert 'Движение 40%: карточки выезжают на эту долю.' in quiet
    assert 'тематические вставки' not in quiet
    assert 'тематические вставки' in full
    assert 'стрелка вверх' in full and 'крупная цифра' in full


def test_spoken_subjects_become_two_short_windows():
    manual = {'captions': [
        {'start': 1, 'end': 8, 'zh': '但中泰有限责任公司第一步就完全不同', 'en': 'Sino-Thai LLCs differ from step one'},
        {'start': 19, 'end': 26, 'zh': '而是股东结构', 'en': 'shareholder structure'},
        {'start': 47, 'end': 56, 'zh': '中国强调法人代表，泰国更看重的是董事权限'},
    ]}
    chosen = windows(manual)
    assert [item['query'] for item in chosen] == ['Bangkok city street', 'business meeting']
    assert chosen[0]['end'] - chosen[0]['start'] <= 2.01
    assert chosen[0]['start'] >= 1


def test_an_unrelated_clip_is_not_inserted():
    speech = '中国 泰国 company shareholders'
    assert relevant({'title': 'Business meeting in an office', 'description': '', 'artist': ''}, 'business meeting', speech)
    assert not relevant(
        {'title': 'Business meeting', 'description': '', 'artist': 'Philippine Government - Radio Television Malacañang'},
        'business meeting', speech,
    )
    assert not relevant({'title': 'Office of the president', 'description': 'radio office', 'artist': ''}, 'company office', speech)


def test_a_window_is_a_layer_and_does_not_replace_the_picture():
    layers = _broll_layers([{'src': 'broll-0.mp4', 'start': 2, 'end': 4, 'credit': 'Ada'}])
    assert len(layers) == 2
    assert 'class="hf-broll"' in layers[0] and 'src="broll-0.mp4"' in layers[0]
    assert 'data-hypit-start-frame="60"' in layers[0]
    assert 'Ada' in layers[1]
    assert _broll_layers([{'src': '', 'start': 0, 'end': 1}]) == []
