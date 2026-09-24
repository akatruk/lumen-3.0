from backend import ai
from backend.style_pictures import attach_art

def test_automatic_cut_drops_a_generated_picture_and_does_not_fetch(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError('openrouter')
    monkeypatch.setattr(ai, 'json_call', forbid)
    monkeypatch.setattr(ai, 'generate_broll', forbid)
    manual = {'clips': [{'id': 'style_0', 'diagram': 3, 'text': 'Visa', 'art': 'style-art-0.png'}, {'id': 'style_1', 'text': 'days'}]}
    result = attach_art('p' * 32, manual, True)
    assert result['clips'][0]['art'] == ''
    assert result['clips'][1]['art'] == ''
    assert result['clips'][0]['text'] == 'Visa'
    assert attach_art('p' * 32, None) is None
