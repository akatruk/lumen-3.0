from backend.style_pictures import image_bytes, subject

def test_owned_words_become_the_picture_subject_and_a_png_is_accepted():
    assert subject('Visa days!') == 'Visa days'
    assert 'SECRET' not in subject('Visa')
    png = b'\x89PNG\r\n\x1a\n' + b'0' * 16
    payload = {'choices': [{'message': {'images': [{'image_url': {'url': 'data:image/png;base64,' + __import__('base64').b64encode(png).decode()}}]}}]}
    assert image_bytes(payload).startswith(b'\x89PNG')
    assert image_bytes({'choices': [{'message': {'content': 'no image'}}]}) is None
