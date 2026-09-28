from backend import ai
from backend.config import settings
from backend.style_pictures import attach_art, image_bytes

PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 24

def _ready(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'openrouter_api_key', 'test-not-a-key')
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    monkeypatch.setattr('backend.style_pictures.reserve', lambda *args, **kwargs: 'token')
    monkeypatch.setattr('backend.style_pictures.settle', lambda *args, **kwargs: None)
    monkeypatch.setattr(ai, 'json_call', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('json')))
    monkeypatch.setattr(ai, 'generate_broll', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('broll')))

def test_measured_graphic_requests_one_image_and_stores_it(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path)
    prompts = []
    def fake(prompt):
        prompts.append(prompt)
        return PNG
    monkeypatch.setattr('backend.style_pictures.fetch', fake)
    manual = {'clips': [
        {'id': 'style_0', 'diagram': 3, 'text': 'Visa', 'observation': 'SECRET REFERENCE LINE', 'art': ''},
        {'id': 'style_1', 'text': 'days'},
    ]}
    result = attach_art('p' * 32, manual, True)
    assert len(prompts) == 1
    assert 'Visa' in prompts[0] and 'days' not in prompts[0] and 'SECRET' not in prompts[0]
    assert result['clips'][0]['art'] == 'style-art-0.png'
    assert result['clips'][0]['diagram'] == 3 and result['clips'][0]['text'] == 'Visa'
    assert result['clips'][1]['art'] == ''
    assert (tmp_path / ('p' * 32) / 'style-art-0.png').read_bytes() == PNG
    assert attach_art('p' * 32, None) is None

def test_each_graphic_uses_one_prompt_from_its_own_words(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path)
    prompts = []
    monkeypatch.setattr('backend.style_pictures.fetch', lambda prompt: prompts.append(prompt) or PNG)
    manual = {'clips': [
        {'id': 'card', 'card': {'title': {'en': 'Price deposit', 'zh': '价格'}}, 'text': 'SECRET REFERENCE LINE'},
        {'id': 'chart', 'graphic': True, 'bars': [1, 0.4], 'text': 'Visa ocean'},
        {'id': 'icon', 'icon': True, 'text': '● Ocean'},
        {'id': 'plain', 'text': 'only words here'},
    ]}
    result = attach_art('c' * 32, manual)
    assert len(prompts) == 3
    assert 'Price deposit' in prompts[0] and 'SECRET' not in prompts[0]
    assert prompts[1].count('Visa') == 1 and 'ocean' in prompts[1]
    assert 'Ocean' in prompts[2]
    assert [clip['art'] for clip in result['clips']] == ['style-art-0.png', 'style-art-1.png', 'style-art-2.png', '']
    assert result['clips'][1]['bars'] == [1, 0.4] and result['clips'][2]['icon'] is True

def test_words_without_a_graphic_do_not_call(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path)
    monkeypatch.setattr('backend.style_pictures.fetch', lambda prompt: (_ for _ in ()).throw(AssertionError(prompt)))
    manual = {'clips': [{'id': 'style_1', 'text': 'days Visa ocean'}]}
    result = attach_art('p' * 32, manual, True)
    assert result['clips'][0]['art'] == ''
    assert result['clips'][0]['text'] == 'days Visa ocean'

def test_a_measured_still_does_not_request_an_image(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path)
    monkeypatch.setattr('backend.style_pictures.fetch', lambda prompt: (_ for _ in ()).throw(AssertionError(prompt)))
    monkeypatch.setattr('backend.style_pictures._reference_shots', lambda pid: [{'picture': {'illustration': True}}])
    manual = {'clips': [{'id': 'style_0', 'diagram': 2, 'text': 'Visa'}]}
    result = attach_art('q' * 32, manual)
    assert result['clips'][0]['art'] == ''
    assert result['clips'][0]['diagram'] == 2 and result['clips'][0]['text'] == 'Visa'
    filled = {'clips': [{'id': 'style_0', 'diagram': 3, 'text': 'Visa', 'stock_still': 'b' * 32}]}
    monkeypatch.setattr('backend.style_pictures._reference_shots', lambda pid: [])
    again = attach_art('q' * 32, filled)
    assert again['clips'][0]['art'] == '' and again['clips'][0]['stock_still'] == 'b' * 32

def test_missing_key_or_a_failed_call_keeps_the_layout(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    monkeypatch.setattr(settings, 'openrouter_api_key', '')
    monkeypatch.setattr('backend.style_pictures.fetch', lambda prompt: (_ for _ in ()).throw(AssertionError('openrouter')))
    manual = {'clips': [{'id': 'style_0', 'diagram': 3, 'text': 'Visa', 'bars': [1], 'art': 'style-art-0.png'}]}
    quiet = attach_art('p' * 32, manual, True)
    assert quiet['clips'][0]['art'] == ''
    assert quiet['clips'][0]['diagram'] == 3 and quiet['clips'][0]['bars'] == [1] and quiet['clips'][0]['text'] == 'Visa'
    _ready(monkeypatch, tmp_path)
    monkeypatch.setattr('backend.style_pictures.fetch', lambda prompt: (_ for _ in ()).throw(ValueError('style_image_failed')))
    failed = attach_art('p' * 32, {'clips': [{'diagram': 3, 'text': 'Visa', 'graphic': True, 'bars': [0.5]}]})
    assert failed['clips'][0]['art'] == ''
    assert failed['clips'][0]['diagram'] == 3 and failed['clips'][0]['bars'] == [0.5]

def test_commons_photo_and_illustration_stay_licensed_stills(monkeypatch):
    from backend import stock
    from backend.style_match import build
    from backend.style_stock import attach
    from backend.tests.test_style_stock import image_page, measured_picture
    monkeypatch.setattr('backend.style_pictures.fetch', lambda prompt: (_ for _ in ()).throw(AssertionError('generated image')))
    monkeypatch.setattr(stock, 'query', lambda **kwargs: [image_page()])
    monkeypatch.setattr('backend.style_pictures.import_still', lambda pid, item: 'b' * 32)
    spoken = [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}]
    for kind in ('illustration', 'photo'):
        row = measured_picture(kind)
        edit, report = build([row], 40, spoken, False, script='ocean waves')
        edit, report = attach('p' * 32, edit, [row], 'ocean waves', report, 40)
        assert edit['clips'][0]['stock_still'] == 'b' * 32
        assert edit['clips'][0]['art'] == ''
        assert edit['clips'][0]['external_broll'] is None

def test_image_bytes_accepts_a_png_data_url():
    import base64
    payload = {'choices': [{'message': {'images': [{'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(PNG).decode()}}]}}]}
    assert image_bytes(payload).startswith(b'\x89PNG')
    assert image_bytes({'choices': [{'message': {'content': 'no image'}}]}) is None
