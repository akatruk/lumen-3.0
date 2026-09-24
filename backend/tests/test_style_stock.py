import json
import shutil

import pytest
from backend import media, stock
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

def covered(reference):
    row = shot(start=0, end=10, motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, visual_type={'en': 'presenter', 'zh': '主讲'}, reusable_method={'en': 'b-roll cover', 'zh': '空镜'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, picture={'insert': 0.70, 'zoom': 1, 'x': 0.5, 'y': 0.5, 'graphic': False, 'split': False})
    row['reference_path'] = reference
    return row

def test_measured_insert_places_one_stock_clip_at_the_same_fraction(monkeypatch):
    reference = '/tmp/SECRET-reference.mp4'
    monkeypatch.setattr(stock, 'query', lambda **kwargs: [page()])
    monkeypatch.setattr(stock, 'import_licensed', lambda pid, item: ('a' * 32, 2.0))
    row = covered(reference)
    edit, report = build([row], 10, [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False, script='ocean waves')
    edit, report = attach('p' * 32, edit, [row], 'ocean waves', report, 10)
    clip = edit['clips'][0]
    insert = clip['external_broll']
    owned_start = clip['start'] + insert['start']
    assert abs(owned_start - 7.0) <= 0.5
    assert insert['end'] - insert['start'] <= 1.2 + 1e-6
    assert insert['end'] - insert['start'] < clip['end'] - clip['start']
    assert insert['asset_id'] == 'a' * 32
    assert clip['cutaway'] is None
    blob = json.dumps(edit)
    assert reference not in blob and 'SECRET REFERENCE LINE' not in blob
    assert 'broll' not in {gap['id'] for gap in report['gaps']}

def test_missing_stock_leaves_the_essential_broll_gap(monkeypatch):
    reference = '/tmp/SECRET-reference.mp4'
    monkeypatch.setattr(stock, 'query', lambda **kwargs: [])
    def refuse(*args, **kwargs):
        raise AssertionError('missing stock was invented')
    monkeypatch.setattr(stock, 'import_licensed', refuse)
    row = covered(reference)
    edit, report = build([row], 10, [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False, script='ocean waves')
    edit, report = attach('p' * 32, edit, [row], 'ocean waves', report, 10)
    assert all(clip.get('cutaway') is None and clip.get('external_broll') is None for clip in edit['clips'])
    assert any(gap['id'] == 'broll' and gap['essential'] is True for gap in report['gaps'])
    blob = json.dumps(edit)
    assert reference not in blob and 'SECRET REFERENCE LINE' not in blob

@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg required')
def test_render_inputs_are_the_owned_source_and_the_stock_file(monkeypatch, tmp_path):
    from backend.schemas import Analysis
    reference = tmp_path / 'SECRET-reference.mp4'
    owned = tmp_path / 'owned.mp4'
    commons = tmp_path / 'commons.mp4'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=blue:s=160x160:d=1:r=30', '-c:v', 'libx264', reference)
    media.ffmpeg('-f', 'lavfi', '-i', 'color=red:s=160x160:d=10:r=30', '-c:v', 'libx264', owned)
    media.ffmpeg('-f', 'lavfi', '-i', 'color=lime:s=160x160:d=2:r=30', '-c:v', 'libx264', commons)
    monkeypatch.setattr(stock, 'query', lambda **kwargs: [page()])
    monkeypatch.setattr(stock, 'import_licensed', lambda pid, item: ('a' * 32, 2.0))
    row = covered(str(reference))
    edit, report = build([row], 10, [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False, script='ocean waves')
    edit, report = attach('p' * 32, edit, [row], 'ocean waves', report, 10)
    calls = []
    real = media.run
    def spy(args, timeout=600):
        calls.append([str(arg) for arg in args])
        return real(args, timeout=timeout)
    monkeypatch.setattr(media, 'run', spy)
    text = {'en': 'Owned', 'zh': '自有'}
    analysis = Analysis(summary=text, strongest_moment=text, audience=text, scores=[{'category': 'hook', 'value': 50, 'reason': text}], scenes=[{'start': 0, 'end': 10, 'title': text, 'observation': text, 'role': 'context'}], transcript=[], recommendations=[], uncertainties=[text])
    media.render(owned, tmp_path, media.probe(owned), analysis, [], 'en', 'original', manual=edit, asset_paths={'a' * 32: commons})
    inputs = [arg for call in calls for flag, arg in zip(call, call[1:]) if flag == '-i']
    assert str(owned) in inputs and str(commons) in inputs
    assert str(reference) not in inputs
    assert 'SECRET REFERENCE LINE' not in '\n'.join(' '.join(call) for call in calls)
