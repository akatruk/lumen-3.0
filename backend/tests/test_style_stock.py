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

def test_two_cover_shots_keep_a_single_commons_clip(monkeypatch):
    calls = {'n': 0}
    def query(**kwargs):
        calls['n'] += 1
        return [page()]
    monkeypatch.setattr(stock, 'query', query)
    monkeypatch.setattr(stock, 'import_licensed', lambda pid, item: ('a' * 32, 2.0))
    quiet = dict(information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': 'SECRET REFERENCE LINE', 'zh': '参考'})
    first = shot(reusable_method={'en': 'b-roll of the coast', 'zh': '空镜'}, **quiet)
    second = shot(start=2, end=4, reusable_method={'en': 'stock footage of the coast', 'zh': '素材'}, **quiet)
    spoken = [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}]
    edit, report = build([first, second], 40, spoken, False, script='ocean waves')
    edit, report = attach('p' * 32, edit, [first, second], 'ocean waves', report, 40)
    assert calls['n'] == 1
    assert sum(1 for clip in edit['clips'] if clip.get('external_broll')) == 1
    assert all(clip.get('art') == '' for clip in edit['clips'])
    assert 'SECRET' not in json.dumps(edit)
    again, _report = attach('p' * 32, edit, [first, second], 'ocean waves', report, 40)
    assert calls['n'] == 1
    assert sum(1 for clip in again['clips'] if clip.get('external_broll')) == 1

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

def image_page(page_id=44):
    return {'pageid': page_id, 'title': 'File:Ocean.jpg', 'imageinfo': [{'url': 'https://upload.wikimedia.org/wikipedia/commons/test.jpg', 'mime': 'image/jpeg', 'width': 800, 'height': 600, 'extmetadata': {'LicenseShortName': {'value': 'CC BY 4.0'}, 'LicenseUrl': {'value': 'https://creativecommons.org/licenses/by/4.0/'}, 'Artist': {'value': '<b>Author</b>'}, 'ImageDescription': {'value': '<p>Ocean</p>'}}}]}

def measured_picture(kind):
    picture = {'zoom': 1, 'graphic': False, 'split': False, 'screen': False}
    picture[kind] = True
    return shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': 'SECRET REFERENCE LINE', 'zh': '参考'}, picture=picture)

def test_measured_illustration_or_photo_attaches_a_licensed_still(monkeypatch):
    seen = []
    def query(**kwargs):
        assert kwargs['gsrlimit'] <= 4
        seen.append(kwargs['gsrsearch'])
        return [image_page()]
    monkeypatch.setattr(stock, 'query', query)
    monkeypatch.setattr('backend.style_pictures.import_still', lambda pid, item: 'b' * 32)
    spoken = [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}]
    for kind in ('illustration', 'photo'):
        seen.clear()
        row = measured_picture(kind)
        row['reference_path'] = '/tmp/SECRET-reference.mp4'
        edit, report = build([row], 40, spoken, False, script='ocean waves')
        edit, report = attach('p' * 32, edit, [row], 'ocean waves', report, 40)
        assert seen and 'ocean' in seen[0] and 'filetype:bitmap' in seen[0]
        assert 'SECRET' not in seen[0] and 'reference' not in seen[0].lower()
        assert edit['clips'][0]['stock_still'] == 'b' * 32
        assert edit['clips'][0]['art'] == ''
        assert edit['clips'][0]['external_broll'] is None
        assert 'SECRET' not in json.dumps(edit)

def test_still_search_stays_at_two_images(monkeypatch):
    calls = {'n': 0}
    def query(**kwargs):
        calls['n'] += 1
        assert kwargs['gsrlimit'] <= 4
        assert 'SECRET' not in kwargs['gsrsearch']
        return [image_page(40 + calls['n'])]
    monkeypatch.setattr(stock, 'query', query)
    ids = iter(['b' * 32, 'c' * 32, 'd' * 32])
    monkeypatch.setattr('backend.style_pictures.import_still', lambda pid, item: next(ids))
    quiet = dict(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''}, observation={'en': 'SECRET REFERENCE LINE', 'zh': '参考'}, picture={'zoom': 1, 'photo': True, 'graphic': False, 'split': False, 'screen': False})
    shots = [shot(**quiet), shot(start=4, end=8, **quiet), shot(start=8, end=12, **quiet)]
    edit = {'clips': [{'id': f'style_{i}', 'start': i * 4, 'end': i * 4 + 4, 'text': 'Visa ocean', 'art': 'style-art-0.png', 'external_broll': None, 'screen': None, 'stock_still': ''} for i in range(3)], 'gaps': []}
    edit, _report = attach('p' * 32, edit, shots, 'ocean waves', {'applied': [], 'gaps': [{'id': 'broll', 'essential': True}]}, 12)
    filled = [clip for clip in edit['clips'] if clip.get('stock_still')]
    assert calls['n'] == 2 and len(filled) == 2
    assert {clip['stock_still'] for clip in filled} == {'b' * 32, 'c' * 32}
    assert all(clip.get('art') == '' for clip in filled)
    assert edit['clips'][2]['stock_still'] == ''
    assert any(gap['id'] == 'broll' and gap['essential'] is True for gap in _report['gaps'])

def test_illustration_words_without_a_measured_picture_do_not_fetch(monkeypatch):
    def query(**kwargs):
        raise AssertionError('words alone fetched a still')
    monkeypatch.setattr(stock, 'query', query)
    monkeypatch.setattr('backend.style_pictures.import_still', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('import')))
    row = shot(motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, reusable_method={'en': 'illustration photo', 'zh': '插画'}, information_density={'en': 'low', 'zh': '低'}, subtitle_emphasis={'en': '', 'zh': ''}, music={'en': '', 'zh': ''})
    edit, report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False, script='ocean waves')
    edit, report = attach('p' * 32, edit, [row], 'ocean waves', report, 40)
    assert all(not clip.get('stock_still') for clip in edit['clips'])
    assert all(clip.get('art') == '' for clip in edit['clips'])

def test_empty_commons_still_keeps_the_gap_and_does_not_write_art(monkeypatch):
    reference = '/tmp/SECRET-reference.mp4'
    monkeypatch.setattr(stock, 'query', lambda **kwargs: [])
    def refuse(*args, **kwargs):
        raise AssertionError('empty commons wrote a file')
    monkeypatch.setattr(stock, 'import_licensed', refuse)
    monkeypatch.setattr('backend.style_pictures.import_still', refuse)
    row = measured_picture('photo')
    row['reusable_method'] = {'en': 'b-roll of the coast', 'zh': '空镜'}
    row['reference_path'] = reference
    edit, report = build([row], 10, [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False, script='ocean waves')
    edit, report = attach('p' * 32, edit, [row], 'ocean waves', report, 10)
    assert all(not clip.get('stock_still') and clip.get('art') == '' and clip.get('external_broll') is None for clip in edit['clips'])
    assert any(gap['id'] == 'broll' and gap['essential'] is True for gap in report['gaps'])
    blob = json.dumps(edit)
    assert reference not in blob and 'SECRET REFERENCE LINE' not in blob

def test_still_search_failure_does_not_fail_the_cut(monkeypatch):
    def boom(**kwargs):
        raise ValueError('stock_unavailable')
    monkeypatch.setattr(stock, 'query', boom)
    row = measured_picture('illustration')
    edit, report = build([row], 40, [{'start': 0, 'end': 4, 'original': 'Visa', 'en': 'Visa', 'zh': '签证'}], False, script='ocean waves')
    edit, report = attach('p' * 32, edit, [row], 'ocean waves', report, 40)
    assert all(not clip.get('stock_still') and clip.get('art') == '' for clip in edit['clips'])
    assert 'style_match_failed' not in {gap['id'] for gap in report['gaps']}

@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg required')
def test_render_inputs_are_the_owned_source_and_the_licensed_still(monkeypatch, tmp_path):
    from backend.schemas import Analysis
    reference = tmp_path / 'SECRET-reference.mp4'
    owned = tmp_path / 'owned.mp4'
    commons = tmp_path / 'commons.png'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=blue:s=160x160:d=1:r=30', '-c:v', 'libx264', reference)
    media.ffmpeg('-f', 'lavfi', '-i', 'color=red:s=160x160:d=10:r=30', '-c:v', 'libx264', owned)
    media.ffmpeg('-f', 'lavfi', '-i', 'color=c=0xE7C27A:s=80x80:d=0.2', '-frames:v', '1', commons)
    monkeypatch.setattr(stock, 'query', lambda **kwargs: [image_page()])
    monkeypatch.setattr('backend.style_pictures.import_still', lambda pid, item: 'b' * 32)
    row = measured_picture('illustration')
    row['reference_path'] = str(reference)
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
    media.render(owned, tmp_path, media.probe(owned), analysis, [], 'en', 'original', manual=edit, asset_paths={'b' * 32: commons})
    inputs = [arg for call in calls for flag, arg in zip(call, call[1:]) if flag == '-i']
    assert str(owned) in inputs and str(commons) in inputs
    assert str(reference) not in inputs
    assert 'SECRET REFERENCE LINE' not in '\n'.join(' '.join(call) for call in calls)
