from backend.hypit_picture import _broll_layers
from backend.presentation_graphics import animation_brief
from backend.manual import Edit
from backend.thematic_broll import hold, image_hit, quota, relevant, windows


def test_the_inserts_slider_names_how_many_clips():
    quiet = animation_brief(Edit.model_validate({
        'clips': [{'start': 0, 'end': 60}],
        'animation_motion': 40,
        'animation_inserts': 0,
    }))
    full = animation_brief(Edit.model_validate({
        'clips': [{'start': 0, 'end': 60}],
        'animation_inserts': 100,
    }))
    mid = animation_brief(Edit.model_validate({
        'clips': [{'start': 0, 'end': 60}],
        'animation_inserts': 40,
    }))
    assert 'Движение 40%: карточки выезжают на эту долю.' in quiet
    assert 'Вставки 0%: дополнительных роликов нет.' in quiet
    assert 'Вставки 100%: 6 коротких роликов по 3 с внутри графики' in full
    assert 'Вставки 40%: 2 коротких роликов' in mid
    assert 'стрелка вверх' in full and 'крупная цифра' in full
    assert quota(0) == 0 and quota(20) == 1 and quota(100) == 6
    assert hold(0) == 1.5 and hold(100) == 3.0


def test_spoken_subjects_become_two_short_windows():
    manual = {'captions': [
        {'start': 1, 'end': 8, 'zh': '但中泰有限责任公司第一步就完全不同', 'en': 'Sino-Thai LLCs differ from step one'},
        {'start': 19, 'end': 26, 'zh': '而是股东结构', 'en': 'shareholder structure'},
        {'start': 47, 'end': 56, 'zh': '中国强调法人代表，泰国更看重的是董事权限'},
    ]}
    chosen = windows(manual)
    assert [item['query'] for item in chosen] == ['Bangkok city hall', 'Shanghai skyline']
    wider = windows(manual, limit=6)
    assert [item['query'] for item in wider] == [
        'Bangkok city hall', 'Shanghai skyline', 'Beijing financial street',
    ]
    assert chosen[0]['end'] - chosen[0]['start'] <= 2.01
    assert chosen[0]['start'] >= 1
    later = windows({'captions': [
        {'start': 1, 'end': 8, 'en': 'Thai company registration'},
        {'start': 20, 'end': 28, 'zh': '注册资本另说'},
    ]}, limit=6, length=3)
    office = next(item for item in later if item['query'] == 'Bangkok city hall')
    capital = next(item for item in later if item['query'] == 'Bangkok city')
    assert capital['start'] >= office['end'] - 0.05


def test_an_unrelated_clip_is_not_inserted():
    speech = '中国 泰国 company shareholders'
    assert relevant({'title': 'Business meeting in an office', 'description': '', 'artist': ''}, 'business meeting', speech)
    assert not relevant(
        {'title': 'Business meeting', 'description': '', 'artist': 'Philippine Government - Radio Television Malacañang'},
        'business meeting', speech,
    )
    assert not relevant({'title': 'Office of the president', 'description': 'radio office', 'artist': ''}, 'company office', speech)
    speech = '中国 泰国 公司 股东 董事 资本'
    assert not relevant({'title': 'RDECOM Board of Directors meeting', 'description': 'U.S. Army', 'artist': 'U.S. Army DEVCOM'}, 'China company directors', speech)
    assert not relevant({'title': "Novatek's Annual General Meeting of Shareholders", 'description': '', 'artist': 'Krassotkin'}, 'China business meeting', speech)
    assert not relevant({'title': 'Cumberland Telephone & Telegraph Company Stock Certificate', 'description': '', 'artist': ''}, 'China company capital', speech)
    assert relevant({'title': 'Bangkok City Hall', 'description': '', 'artist': 'Ada'}, 'Bangkok city hall', speech)
    assert not relevant({'title': 'Shanghai Street in Hong Kong', 'description': '', 'artist': ''}, 'Shanghai skyline', speech)
    from backend.presentation_graphics import animation_brief
    from backend.manual import Edit
    themed = animation_brief(Edit.model_validate({
        'clips': [{'start': 0, 'end': 60}],
        'animation_inserts': 100,
        'captions': [
            {'start': 1, 'end': 8, 'original': '中泰公司', 'en': 'Sino-Thai company', 'zh': '中泰公司注册'},
            {'start': 20, 'end': 28, 'original': '中国股东', 'en': 'China shareholders', 'zh': '中国的股东和泰国的董事'},
        ],
    }))
    assert 'по теме ролика: Таиланд и Китай, регистрация компании, акционеры, директора' in themed
    assert 'Чужую страну и чужую организацию не показывай' in themed


def test_a_licensed_photo_of_the_subject_can_become_the_clip():
    page = {
        'title': 'File:Bangkok city street market.jpg',
        'imageinfo': [{
            'thumburl': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/b.jpg',
            'extmetadata': {
                'LicenseShortName': {'value': 'CC BY 4.0'},
                'Artist': {'value': 'Ada'},
                'ImageDescription': {'value': 'A street in Bangkok'},
            },
        }],
    }
    hit = image_hit(page, 'Bangkok city street', '泰国')
    assert hit and hit['artist'] == 'Ada'
    shared = {
        'title': 'File:Bangkok skytrain.jpg',
        'imageinfo': [{
            'thumburl': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/c.jpg',
            'extmetadata': {
                'LicenseShortName': {'value': 'CC BY-SA 4.0'},
                'Artist': {'value': 'Ada'},
                'ImageDescription': {'value': 'Bangkok'},
            },
        }],
    }
    assert image_hit(shared, 'Bangkok city street', '泰国') is None


def test_a_window_is_a_layer_and_does_not_replace_the_picture():
    layers = _broll_layers([{'src': 'broll-0.mp4', 'start': 2, 'end': 4, 'credit': 'Ada'}])
    assert len(layers) == 2
    assert 'class="hf-broll"' in layers[0] and 'src="broll-0.mp4"' in layers[0]
    assert 'data-hypit-start-frame="60"' in layers[0]
    assert 'Ada' in layers[1]
    assert _broll_layers([{'src': '', 'start': 0, 'end': 1}]) == []
    many = _broll_layers([
        {'src': f'broll-{index}.mp4', 'start': 2 + index * 8, 'end': 5 + index * 8, 'credit': 'Ada'}
        for index in range(4)
    ])
    assert sum('class="hf-broll"' in layer for layer in many) == 4
