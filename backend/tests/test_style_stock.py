from backend import stock
from backend.style_match import build
from backend.style_stock import attach, subject
from backend.tests.test_style_match import shot

def page():
    return {'pageid': 12, 'title': 'File:Ocean.webm', 'videoinfo': [{'duration': 2, 'extmetadata': {'LicenseShortName': {'value': 'CC BY 4.0'}, 'LicenseUrl': {'value': 'https://creativecommons.org/licenses/by/4.0/'}, 'Artist': {'value': '<b>Author</b>'}, 'ImageDescription': {'value': '<p>Ocean waves</p>'}}, 'derivatives': [{'src': 'https://upload.wikimedia.org/wikipedia/commons/test.webm', 'height': 480, 'width': 854, 'type': 'video/webm'}]}]}

def test_reference_words_are_not_the_stock_query():
    assert 'SECRET' not in subject('Visa', 'ocean waves')
    assert subject('Visa', 'ocean waves').startswith('Visa')

def test_licensed_commons_clip_is_inserted(monkeypatch):
    seen = {}
    def query(**kwargs):
        seen['q'] = kwargs['gsrsearch']
        return [page()]
    monkeypatch.setattr(stock, 'query', query)
    monkeypatch.setattr(stock, 'import_licensed', lambda pid, item: ('a' * 32, 2.0))
    row = shot(reusable_method={'en': 'b-roll of the coast', 'zh': '空镜'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    edit, report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False, script='ocean waves')
    edit, report = attach('p' * 32, edit, [row], 'ocean waves', report, 40)
    assert 'ocean' in seen['q'] and 'SECRET' not in seen['q']
    assert edit['clips'][0]['external_broll']['asset_id'] == 'a' * 32
    assert edit['clips'][0]['cutaway'] is None
    assert 'stock' in report['applied']
    assert 'broll' not in {gap['id'] for gap in report['gaps']}

def test_unlicensed_page_is_not_inserted(monkeypatch):
    blocked = page()
    blocked['videoinfo'][0]['extmetadata']['LicenseShortName']['value'] = 'All rights reserved'
    monkeypatch.setattr(stock, 'query', lambda **kwargs: [blocked])
    def refuse(*args, **kwargs):
        raise AssertionError('unlicensed stock was downloaded')
    monkeypatch.setattr(stock, 'import_licensed', refuse)
    row = shot(reusable_method={'en': 'stock footage', 'zh': '素材'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    edit, report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False, script='ocean waves')
    edit, report = attach('p' * 32, edit, [row], 'ocean waves', report, 40)
    assert edit['clips'][0]['external_broll'] is None
    assert 'stock' not in report['applied']
