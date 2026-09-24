import re
from types import SimpleNamespace
from backend import media
from backend.manual import Edit
from backend.style_match import build
from backend.style_vision import _join, annotate_pictures, black_spans, chroma_plate, color_sample, flat_background, frame_similarity, freeze_spans, grade_between, highlight_window, light_between, measure, pace_of, picture_of, reference_layout, title_motion, visual_track
from backend.timeline import motion_filter
from backend.media import write_kinetic


def _video(path, *graphs):
    media.ffmpeg(*graphs, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', path)


def test_measure_finds_a_cut_and_a_flat_plate(tmp_path):
    cuts = tmp_path / 'cuts.mp4'
    _video(cuts, '-f', 'lavfi', '-i', 'color=red:s=320x568:r=30:d=1', '-f', 'lavfi', '-i', 'color=blue:s=320x568:r=30:d=1', '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0')
    vision = measure(cuts)
    boundaries = [shot['start'] for shot in vision['shots']]
    assert any(abs(stamp - 1) < 0.2 for stamp in boundaries)
    assert vision['color'] and vision['color']['y'] > 0
    plate = tmp_path / 'plate.mp4'
    _video(plate, '-f', 'lavfi', '-i', 'color=0x00FF00:s=160x240:r=30:d=1', '-f', 'lavfi', '-i', 'color=white:s=40x80:r=30:d=1', '-filter_complex', 'overlay=60:80')
    assert flat_background(plate) is True
    assert chroma_plate(plate) == 'green'
    moving = tmp_path / 'moving.mp4'
    _video(moving, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=1', '-f', 'lavfi', '-i', 'color=white:s=50x80:r=30:d=1', '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=1', '-f', 'lavfi', '-i', 'color=white:s=50x80:r=30:d=1', '-filter_complex', '[0:v][1:v]overlay=10:40[a];[2:v][3:v]overlay=120:40[b];[a][b]concat=n=2:v=1:a=0')
    track = visual_track(moving)
    assert track and track['x0'] < track['x1']
    dark = tmp_path / 'dark.mp4'
    _video(dark, '-f', 'lavfi', '-i', 'color=black:s=160x240:r=30:d=1', '-f', 'lavfi', '-i', 'color=0x335577:s=160x240:r=30:d=1', '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0')
    spans = black_spans(dark)
    assert spans and spans[0]['start'] < 0.2 and spans[0]['end'] > 0.8
    assert highlight_window(dark, 2)['start'] >= 0.8
    held = tmp_path / 'held-plate.mp4'
    _video(held, '-f', 'lavfi', '-i', 'color=0x202020:s=160x160:r=30:d=0.4', '-f', 'lavfi', '-i', 'color=white:s=160x160:r=30:d=1.2', '-f', 'lavfi', '-i', 'color=0x224466:s=160x160:r=30:d=0.4', '-filter_complex', '[0:v][1:v][2:v]concat=n=3:v=1:a=0')
    frozen = freeze_spans(held)
    assert frozen and frozen[0]['start'] < 0.6 and frozen[0]['end'] > 1.4
    moving_plate = tmp_path / 'moving-plate.mp4'
    _video(moving_plate, '-f', 'lavfi', '-i', 'testsrc=s=160x160:r=30:d=1.6')
    assert freeze_spans(moving_plate) == []
    bright = tmp_path / 'bright-then-detail.mp4'
    _video(bright, '-f', 'lavfi', '-i', 'color=white:s=160x160:r=30:d=1.2', '-f', 'lavfi', '-i', 'testsrc=s=160x160:r=30:d=1.2', '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0')
    assert highlight_window(bright, 2.4)['start'] >= 0.9
    title = tmp_path / 'title.ass'
    write_kinetic(title, 'Visa', 1.2, 160, 240)
    assert '\\fscx100' in title.read_text()
    assert title.read_text().count('Dialogue:') == 1
    follow = tmp_path / 'follow.ass'
    write_kinetic(follow, 'Visa days', 1.6, 160, 240)
    lines = [line for line in follow.read_text().splitlines() if line.startswith('Dialogue:')]
    assert len(lines) == 2 and 'Visa' in lines[0] and lines[1].endswith('days')
    assert lines[1].split(',')[1] != lines[0].split(',')[1]
    split = tmp_path / 'split.mp4'
    _video(split, '-f', 'lavfi', '-i', 'color=red:s=90x240:r=30:d=1', '-f', 'lavfi', '-i', 'color=blue:s=90x240:r=30:d=1', '-filter_complex', '[0:v][1:v]hstack=inputs=2')
    assert reference_layout(split)['split'] is True
    bar = tmp_path / 'bar.mp4'
    _video(bar, '-f', 'lavfi', '-i', 'color=0x222222:s=160x240:r=30:d=1', '-f', 'lavfi', '-i', 'color=white:s=160x16:r=30:d=1', '-filter_complex', 'overlay=0:224')
    found = reference_layout(bar)
    assert found['bar'] is True and found['split'] is False
    jumped = tmp_path / 'jumped.mp4'
    _video(jumped, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.35', '-f', 'lavfi', '-i', 'color=white:s=50x70:r=30:d=0.35', '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.35', '-f', 'lavfi', '-i', 'color=white:s=50x70:r=30:d=0.35', '-filter_complex', '[0:v][1:v]overlay=8:40[a];[2:v][3:v]overlay=120:40[b];[a][b]concat=n=2:v=1:a=0')
    assert reference_layout(jumped)['shake'] is True and reference_layout(jumped)['shake_rx'] == 32
    card = tmp_path / 'card.mp4'
    _video(card, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=1', '-f', 'lavfi', '-i', 'color=white:s=36x90:r=30:d=1', '-filter_complex', 'overlay=72:30')
    tight = picture_of(card, 0, 1)
    assert tight['graphic'] is True and tight['zoom'] >= 1.3
    plain = tmp_path / 'plain.mp4'
    _video(plain, '-f', 'lavfi', '-i', 'color=0x446688:s=180x240:r=30:d=1')
    wide = picture_of(plain, 0, 1)
    assert wide['zoom'] == 1 and wide['graphic'] is False and wide['split'] is False
    assert picture_of(split, 0, 1)['split'] is True
    faded = tmp_path / 'faded.mp4'
    _video(faded, '-f', 'lavfi', '-i', 'color=black:s=160x240:r=30:d=0.25', '-f', 'lavfi', '-i', 'color=0x6688aa:s=160x240:r=30:d=0.9', '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0')
    assert picture_of(faded, 0, 1.15)['fade'] is True
    assert picture_of(plain, 0, 1)['fade'] is False
    vig = tmp_path / 'vig.mp4'
    _video(vig, '-f', 'lavfi', '-i', 'testsrc=s=180x240:r=30:d=0.4', '-vf', 'vignette=angle=PI/3')
    assert picture_of(vig, 0, 0.4)['vignette'] is True
    assert picture_of(plain, 0, 1)['vignette'] is False
    bezel = tmp_path / 'bezel.mp4'
    _video(bezel, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.4', '-vf', 'drawbox=x=16:y=16:w=148:h=208:color=0xD8D2C4:t=fill')
    assert picture_of(bezel, 0, 0.4)['screen'] is True
    assert picture_of(plain, 0, 1)['screen'] is False
    assert picture_of(card, 0, 1)['screen'] is False
    low = tmp_path / 'low.mp4'
    _video(low, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.8', '-f', 'lavfi', '-i', 'color=white:s=40x50:r=30:d=0.8', '-filter_complex', 'overlay=70:180')
    placed = picture_of(low, 0, 0.8)
    assert placed['y'] == 0.78 and placed['zoom'] >= 1.3 and placed['y_end'] is None
    large = tmp_path / 'large.mp4'
    _video(large, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.8', '-f', 'lavfi', '-i', 'color=white:s=160x200:r=30:d=0.8', '-filter_complex', 'overlay=10:20')
    filled = picture_of(large, 0, 0.8)
    assert placed['zoom'] > filled['zoom'] >= 1
    assert picture_of(plain, 0, 1)['y'] == 0.5
    ellipse = tmp_path / 'ellipse.mp4'
    _video(ellipse, '-f', 'lavfi', '-i', 'color=0x101614:s=180x240:r=30:d=0.4', '-vf', "geq=lum='if(lt(pow((X-W/2)/(W*0.38),2)+pow((Y-H/2)/(H*0.42),2),1),210,16)':cb=128:cr=128")
    assert picture_of(ellipse, 0, 0.4)['mask'] is True
    assert picture_of(ellipse, 0, 0.4)['split'] is False and picture_of(ellipse, 0, 0.4)['lower'] is False
    assert picture_of(split, 0, 1)['mask'] is False
    assert picture_of(plain, 0, 1)['mask'] is False and picture_of(vig, 0, 0.4)['mask'] is False
    band = tmp_path / 'band.mp4'
    _video(band, '-f', 'lavfi', '-i', 'color=0x222222:s=180x240:r=30:d=0.4', '-vf', 'drawbox=x=0:y=192:w=180:h=48:color=0xF4F1EA:t=fill')
    assert picture_of(band, 0, 0.4)['lower'] is True and picture_of(band, 0, 0.4)['mask'] is False
    assert picture_of(bar, 0, 1)['lower'] is False
    rise = tmp_path / 'rise.mp4'
    _video(rise, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.6', '-f', 'lavfi', '-i', 'color=white:s=40x50:r=30:d=0.6', '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.6', '-f', 'lavfi', '-i', 'color=white:s=40x50:r=30:d=0.6', '-filter_complex', '[0:v][1:v]overlay=70:8[a];[2:v][3:v]overlay=70:180[b];[a][b]concat=n=2:v=1:a=0')
    moved = picture_of(rise, 0, 1.2)
    assert moved['y'] == 0.22 and moved['y_end'] == 0.78


def test_style_filters_keep_the_slot_duration(tmp_path):
    source = tmp_path / 'source.mp4'
    _video(source, '-f', 'lavfi', '-i', 'color=0x224466:s=160x240:r=30:d=3')
    folder = tmp_path / 'out'
    folder.mkdir()
    edit = Edit(clips=[
        {'start': 0, 'end': 1.5, 'speed': 1.35, 'blur': 2, 'stabilize': True, 'glow': True, 'shadow': True, 'grade': {'brightness': 0.02, 'contrast': 1.05, 'saturation': 1.08}},
        {'start': 1.5, 'end': 3, 'split': True},
    ])
    result = media.render(source, folder, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=edit.model_dump())
    assert abs(result['metadata']['duration'] - 3) < 0.6
    assert result['metadata']['width'] > 0
    keyed = tmp_path / 'keyed'
    keyed.mkdir()
    plate = tmp_path / 'plate.mp4'
    _video(plate, '-f', 'lavfi', '-i', 'color=0x00FF00:s=160x240:r=30:d=2', '-f', 'lavfi', '-i', 'color=white:s=40x80:r=30:d=2', '-filter_complex', 'overlay=60:80')
    cut = media.render(plate, keyed, media.probe(plate), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 2, 'cutout': True, 'plate': '1A1F1C'}]).model_dump())
    assert abs(cut['metadata']['duration'] - 2) < 0.6
    masked = tmp_path / 'masked'
    masked.mkdir()
    window = media.render(source, masked, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.5, 'mask': True, 'exposure': 0.2, 'progress': 0.66}]).model_dump())
    assert abs(window['metadata']['duration'] - 1.5) < 0.6
    chart = tmp_path / 'chart'
    chart.mkdir()
    drawn = media.render(source, chart, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.5, 'graphic': True, 'bars': [1, 0.4]}]).model_dump())
    assert abs(drawn['metadata']['duration'] - 1.5) < 0.6
    band = tmp_path / 'band'
    band.mkdir()
    lowered = media.render(source, band, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.5, 'lower': True}]).model_dump())
    assert abs(lowered['metadata']['duration'] - 1.5) < 0.6
    held = tmp_path / 'held'
    held.mkdir()
    frozen = media.render(source, held, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.5, 'still': 2}]).model_dump())
    assert abs(frozen['metadata']['duration'] - 1.5) < 0.6
    halves = tmp_path / 'halves.mp4'
    _video(halves, '-f', 'lavfi', '-i', 'color=red:s=160x240:r=30:d=1', '-f', 'lavfi', '-i', 'color=blue:s=160x240:r=30:d=1', '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0')
    sided = tmp_path / 'sided'
    sided.mkdir()
    panel = media.render(halves, sided, media.probe(halves), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1, 'split': True, 'panel': 1}]).model_dump())
    assert abs(panel['metadata']['duration'] - 1) < 0.6
    framed = tmp_path / 'framed'
    framed.mkdir()
    screen = media.render(source, framed, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.5, 'screen': 2}]).model_dump())
    assert abs(screen['metadata']['duration'] - 1.5) < 0.6
    drawn_art = tmp_path / 'drawn'
    drawn_art.mkdir()
    shapes = media.render(source, drawn_art, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.5, 'diagram': 3}]).model_dump())
    assert abs(shapes['metadata']['duration'] - 1.5) < 0.6
    png = source.parent / 'style-art-0.png'
    media.ffmpeg('-f', 'lavfi', '-i', 'color=c=0xE7C27A:s=80x80:d=0.2', '-frames:v', '1', png)
    painted = tmp_path / 'painted'
    painted.mkdir()
    picture = media.render(source, painted, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.5, 'diagram': 3, 'art': 'style-art-0.png'}]).model_dump())
    assert abs(picture['metadata']['duration'] - 1.5) < 0.6


def test_join_names_only_reproducible_transitions(tmp_path):
    hard = tmp_path / 'hard.mp4'
    _video(hard, '-f', 'lavfi', '-i', 'color=red:s=180x240:r=30:d=0.6', '-f', 'lavfi', '-i', 'color=blue:s=180x240:r=30:d=0.6', '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0')
    assert _join(hard, 0.6) == 'cut'
    dip = tmp_path / 'dip.mp4'
    _video(dip, '-f', 'lavfi', '-i', 'color=black:s=180x240:r=30:d=0.5', '-f', 'lavfi', '-i', 'color=0xE8E4DC:s=180x240:r=30:d=0.6', '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0')
    assert _join(dip, 0.5) == 'fade'
    wipe = tmp_path / 'wipe.mp4'
    _video(wipe, '-f', 'lavfi', '-i', 'color=red:s=180x240:r=30:d=0.56', '-f', 'lavfi', '-i', 'color=blue:s=90x240:r=30:d=0.08', '-f', 'lavfi', '-i', 'color=red:s=90x240:r=30:d=0.08', '-f', 'lavfi', '-i', 'color=blue:s=180x240:r=30:d=0.56', '-filter_complex', '[1:v][2:v]hstack=inputs=2[m];[0:v][m][3:v]concat=n=3:v=1:a=0')
    assert _join(wipe, 0.6) == 'wipe'
    other = tmp_path / 'other.mp4'
    _video(other, '-f', 'lavfi', '-i', 'color=red:s=180x240:r=30:d=0.56', '-f', 'lavfi', '-i', 'color=red:s=90x240:r=30:d=0.08', '-f', 'lavfi', '-i', 'color=blue:s=90x240:r=30:d=0.08', '-f', 'lavfi', '-i', 'color=blue:s=180x240:r=30:d=0.56', '-filter_complex', '[1:v][2:v]hstack=inputs=2[m];[0:v][m][3:v]concat=n=3:v=1:a=0')
    assert _join(other, 0.6) == 'wipe-right'
    opened = tmp_path / 'opened.mp4'
    _video(opened, '-f', 'lavfi', '-i', 'color=red:s=180x240:r=30:d=0.56', '-f', 'lavfi', '-i', 'color=red:s=180x240:r=30:d=0.08', '-f', 'lavfi', '-i', 'color=blue:s=60x80:r=30:d=0.08', '-f', 'lavfi', '-i', 'color=blue:s=180x240:r=30:d=0.56', '-filter_complex', '[1:v][2:v]overlay=60:80[m];[0:v][m][3:v]concat=n=3:v=1:a=0')
    assert _join(opened, 0.6) == 'circle'
    blend = tmp_path / 'blend.mp4'
    _video(blend, '-f', 'lavfi', '-i', 'color=red:s=180x240:r=30:d=0.56', '-f', 'lavfi', '-i', 'color=red:s=180x240:r=30:d=0.08', '-f', 'lavfi', '-i', 'color=blue:s=180x240:r=30:d=0.08', '-f', 'lavfi', '-i', 'color=blue:s=180x240:r=30:d=0.56', '-filter_complex', '[1:v][2:v]blend=all_mode=average[m];[0:v][m][3:v]concat=n=3:v=1:a=0')
    assert _join(blend, 0.6) == 'crossfade'

def test_measured_zoom_and_right_wipe_render_on_owned_clips(tmp_path, monkeypatch):
    import subprocess
    from backend.style_match import _gaps, _transition
    from backend.transitions import apply
    zoom = tmp_path / 'zoom-ref.mp4'
    _video(zoom, '-f', 'lavfi', '-i', 'color=red:s=160x240:r=30:d=0.9', '-f', 'lavfi', '-i', 'color=red:s=160x240:r=30:d=0.2', '-f', 'lavfi', '-i', 'color=white:s=52x80:r=30:d=0.2', '-f', 'lavfi', '-i', 'color=0xE8E4DC:s=160x240:r=30:d=0.9', '-filter_complex', '[1:v][2:v]overlay=54:80[m];[0:v][m][3:v]concat=n=3:v=1:a=0')
    assert _join(zoom, 1.0) == 'zoom'
    wipe = tmp_path / 'wipe-ref.mp4'
    _video(wipe, '-f', 'lavfi', '-i', 'color=red:s=160x240:r=30:d=0.9', '-f', 'lavfi', '-i', 'color=red:s=80x240:r=30:d=0.2', '-f', 'lavfi', '-i', 'color=0xE8E4DC:s=80x240:r=30:d=0.2', '-f', 'lavfi', '-i', 'color=0xE8E4DC:s=160x240:r=30:d=0.9', '-filter_complex', '[1:v][2:v]hstack=inputs=2[m];[0:v][m][3:v]concat=n=3:v=1:a=0')
    assert _join(wipe, 1.0) == 'wipe-right'
    assert _transition({'transition': {'en': 'zoom', 'zh': '缩放'}}) == 'zoom'
    assert _transition({'transition': {'en': 'cut', 'zh': '切'}, 'motion': {'en': 'a zoom through the room', 'zh': ''}, 'reusable_method': {'en': 'zoom on the speaker', 'zh': ''}}) == 'cut'
    assert _transition({'transition': {'en': 'cut', 'zh': '切'}, 'picture': {'join': 'zoom'}}) == 'zoom'
    assert _transition({'transition': {'en': 'cut', 'zh': '切'}, 'picture': {'join': 'wipe-right'}}) == 'wipe'
    missed = {'clips': [{'transition': 'cut'}], 'subtitles': False, 'captions': []}
    quiet = {'transition': {'en': 'cut', 'zh': ''}, 'subtitle_emphasis': {'en': '', 'zh': ''}}
    assert {gap['id']: gap['essential'] for gap in _gaps([{**quiet, 'picture': {'join': 'zoom'}}], missed)}['zoom_transition'] is False
    assert {gap['id']: gap['essential'] for gap in _gaps([{**quiet, 'picture': {'join': 'wipe-right'}}], missed)}['wipe_right'] is False
    kept = {'clips': [{'transition': 'wipe'}], 'subtitles': False, 'captions': []}
    assert 'wipe_right' not in {gap['id'] for gap in _gaps([{**quiet, 'picture': {'join': 'wipe-right'}, 'transition': {'en': 'wipe-right', 'zh': ''}}], kept)}

    def rgb(path, stamp, crop):
        return subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', str(stamp), '-i', str(path), '-vf', crop, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])

    calls = []
    real = media.ffmpeg

    def spy(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)

    before = tmp_path / 'owned-before.mp4'
    after = tmp_path / 'owned-after.mp4'
    for path, color in ((before, 'black'), (after, '0xE8E4DC')):
        real('-f', 'lavfi', '-i', f'color={color}:s=160x240:d=1:r=30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', path)
    hard_cut = tmp_path / 'hard-cut.mp4'
    hard_cut.write_bytes(after.read_bytes())
    monkeypatch.setattr(media, 'ffmpeg', spy)
    apply(before, after, 'zoom', 1)
    assert abs(media.probe(before)['duration'] - 1) < 0.08
    assert abs(media.probe(after)['duration'] - 1) < 0.08
    # zoomin holds the outgoing picture, so the blend is visible on the incoming clip.
    hard = rgb(hard_cut, 0.08, 'scale=16:16')
    mixed = rgb(after, 0.08, 'scale=16:16')
    assert sum(abs(a - b) for a, b in zip(hard, mixed)) / len(hard) > 8
    calls.clear()
    left = tmp_path / 'owned-left.mp4'
    right = tmp_path / 'owned-right.mp4'
    for path, color in ((left, 'black'), (right, '0xE8E4DC')):
        real('-f', 'lavfi', '-i', f'color={color}:s=160x240:d=1:r=30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', path)
    apply(left, right, _transition({'transition': {'en': 'cut', 'zh': ''}, 'picture': {'join': 'wipe-right'}}), 1)
    assert abs(media.probe(left)['duration'] - 1) < 0.08
    assert abs(media.probe(right)['duration'] - 1) < 0.08
    side_l = rgb(right, 0.08, 'crop=80:240:0:0,scale=8:8')
    side_r = rgb(right, 0.08, 'crop=80:240:80:0,scale=8:8')
    assert sum(side_r) / len(side_r) > sum(side_l) / len(side_l) + 20
    rendered = ' '.join(str(part) for args in calls for part in args)
    sentinel = tmp_path / 'do-not-render.mp4'
    assert str(zoom) not in rendered and str(wipe) not in rendered and str(sentinel) not in rendered

def test_grade_follows_measured_yuv_without_copying_the_frame(tmp_path):
    dark = tmp_path / 'dark.mp4'
    bright = tmp_path / 'bright.mp4'
    warm = tmp_path / 'warm.mp4'
    _video(dark, '-f', 'lavfi', '-i', 'color=0x202020:s=160x160:r=30:d=1.2')
    _video(bright, '-f', 'lavfi', '-i', 'color=0xE8E8E8:s=160x160:r=30:d=1.2')
    _video(warm, '-f', 'lavfi', '-i', 'color=0xC04020:s=160x160:r=30:d=1.2')
    owned, lit, tinted = color_sample(dark), color_sample(bright), color_sample(warm)
    lifted = grade_between(lit, owned)
    matched = grade_between(owned, owned)
    assert lifted['brightness'] == 0.2
    assert light_between(lit, owned) > 0.5
    assert grade_between(tinted, owned)['rs'] > lifted['rs']
    assert grade_between(tinted, owned)['saturation'] > 1
    assert matched['brightness'] == 0 and matched['contrast'] == 1 and matched['saturation'] == 1 and matched['rs'] == 0
    assert light_between(owned, owned) == 0
    assert set(lifted) == {'brightness', 'contrast', 'saturation', 'gamma', 'rs', 'gs', 'bs'}

def test_pace_ramps_only_when_the_shot_changes_speed(tmp_path):
    accelerate = tmp_path / 'accel.mp4'
    _video(accelerate, '-f', 'lavfi', '-i', 'color=0x202020:s=160x160:r=30:d=0.9', '-f', 'lavfi', '-i', 'color=0x111111:s=160x160:r=30:d=0.9', '-f', 'lavfi', '-i', 'color=white:s=40x40:r=30:d=0.9', '-filter_complex', "[1:v][2:v]overlay=x='20+80*mod(n,2)':y=40[move];[0:v][move]concat=n=2:v=1:a=0")
    assert pace_of(accelerate, 0, 1.8) == (1.0, 1.45)
    decelerate = tmp_path / 'decel.mp4'
    _video(decelerate, '-f', 'lavfi', '-i', 'color=0x111111:s=160x160:r=30:d=0.9', '-f', 'lavfi', '-i', 'color=white:s=40x40:r=30:d=0.9', '-f', 'lavfi', '-i', 'color=0x202020:s=160x160:r=30:d=0.9', '-filter_complex', "[0:v][1:v]overlay=x='20+80*mod(n,2)':y=40[move];[move][2:v]concat=n=2:v=1:a=0")
    assert pace_of(decelerate, 0, 1.8) == (1.45, 0.8)
    still = tmp_path / 'still.mp4'
    _video(still, '-f', 'lavfi', '-i', 'color=0x446688:s=160x160:r=30:d=1.8')
    assert pace_of(still, 0, 1.8) is None
    chain = motion_filter({'zoom': 1, 'x': 0.5, 'y': 0.5, 'speed': 1, 'speed_end': 1.45}, 160, 240, 1.5)
    assert 'sqrt' in chain and 'PTS/1.0000' not in chain
    source = tmp_path / 'source.mp4'
    _video(source, '-f', 'lavfi', '-i', 'color=0x224466:s=160x240:r=30:d=4')
    folder = tmp_path / 'ramp'
    folder.mkdir()
    result = media.render(source, folder, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.5, 'speed': 1, 'speed_end': 1.45}]).model_dump())
    assert abs(result['metadata']['duration'] - 1.5) < 0.6

def test_blur_glow_and_shadow_strength_follow_the_frame(tmp_path):
    def clip(name, *graphs):
        path = tmp_path / name
        _video(path, *graphs)
        return picture_of(path, 0, 0.4)
    light = clip('light.mp4', '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.4', '-f', 'lavfi', '-i', 'color=white:s=70x90:r=30:d=0.4', '-filter_complex', 'overlay=55:70,gblur=sigma=2')
    heavy = clip('heavy.mp4', '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.4', '-f', 'lavfi', '-i', 'color=white:s=70x90:r=30:d=0.4', '-filter_complex', 'overlay=55:70,gblur=sigma=8')
    sharp = clip('sharp.mp4', '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.4', '-f', 'lavfi', '-i', 'color=white:s=70x90:r=30:d=0.4', '-filter_complex', 'overlay=55:70')
    flat = clip('flat.mp4', '-f', 'lavfi', '-i', 'color=0x446688:s=180x240:r=30:d=0.4')
    assert heavy['blur'] > light['blur'] > 0
    assert sharp['blur'] == 0 and flat['blur'] == 0
    mild = clip('mild.mp4', '-f', 'lavfi', '-i', 'testsrc=s=180x240:r=30:d=0.4', '-vf', 'vignette=angle=PI/3')
    deep = clip('deep.mp4', '-f', 'lavfi', '-i', 'testsrc=s=180x240:r=30:d=0.4', '-vf', 'vignette=angle=PI/2')
    assert deep['shade'] > mild['shade'] > 0 and flat['shade'] == 0
    halo = clip('halo.mp4', '-f', 'lavfi', '-i', 'color=0x101010:s=180x240:r=30:d=0.4', '-f', 'lavfi', '-i', 'color=white:s=90x90:r=30:d=0.4', '-f', 'lavfi', '-i', 'color=white:s=28x28:r=30:d=0.4', '-filter_complex', '[1:v]gblur=sigma=14[halo];[0:v][halo]overlay=(W-w)/2:(H-h)/2[base];[base][2:v]overlay=(W-w)/2:(H-h)/2')
    assert halo['glow'] > 0 and halo['blur'] == 0 and sharp['glow'] == 0
    chain = motion_filter({'zoom': 1, 'x': 0.5, 'y': 0.5, 'speed': 1, 'blur': heavy['blur'], 'glow': True, 'glow_amount': halo['glow'], 'shadow': True, 'shade': deep['shade']}, 160, 240, 1)
    assert f"gblur=sigma={heavy['blur']:.2f}" in chain
    assert f"unsharp=7:7:{halo['glow']:.2f}" in chain
    assert f"vignette=angle={deep['shade']:.3f}" in chain
    assert 'enable=' not in chain

def test_similarity_compares_the_rendered_frame(tmp_path):
    sharp = tmp_path / 'sharp.mp4'
    soft = tmp_path / 'soft.mp4'
    _video(sharp, '-f', 'lavfi', '-i', 'testsrc=s=180x240:r=30:d=1.2')
    _video(soft, '-f', 'lavfi', '-i', 'testsrc=s=180x240:r=30:d=1.2', '-vf', 'gblur=sigma=8')
    same = frame_similarity(sharp, sharp)
    apart = frame_similarity(sharp, soft)
    assert same is not None and same >= 90
    assert apart is not None and apart < same - 15

def test_illustration_tiles_follow_the_bright_blocks(tmp_path):
    one = tmp_path / 'one-tile.mp4'
    four = tmp_path / 'four-tiles.mp4'
    box = 'drawbox=x=iw*{x}:y=ih*{y}:w=iw*0.24:h=ih*0.16:color=0xE7C27A:t=fill'
    spots = ((0.18, 0.32), (0.56, 0.32), (0.18, 0.58), (0.56, 0.58))
    _video(one, '-f', 'lavfi', '-i', 'color=0x1A2430:s=180x240:r=30:d=0.4', '-vf', box.format(x=0.18, y=0.32))
    _video(four, '-f', 'lavfi', '-i', 'color=0x1A2430:s=180x240:r=30:d=0.4', '-vf', ','.join(box.format(x=x, y=y) for x, y in spots))
    assert picture_of(one, 0, 0.4)['tiles'] == 1
    assert picture_of(four, 0, 0.4)['tiles'] == 4
    source = tmp_path / 'owned.mp4'
    _video(source, '-f', 'lavfi', '-i', 'color=0x203028:s=180x240:r=30:d=1.2')
    single, several = tmp_path / 'single', tmp_path / 'several'
    single.mkdir(); several.mkdir()
    media.render(source, single, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.2, 'diagram': 1, 'text': ''}]).model_dump())
    rendered = media.render(source, several, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.2, 'diagram': 4, 'text': ''}]).model_dump())
    assert abs(rendered['metadata']['duration'] - 1.2) < 0.2

    def luma(folder):
        out, err = media.ffmpeg('-ss', '0.5', '-i', folder / 'result.mp4', '-vf', 'crop=8:8:118:154,signalstats,metadata=print:file=-', '-frames:v', '1', '-f', 'null', '-')
        return float(re.search(r'YAVG=([\d.]+)', out + '\n' + err).group(1))

    assert luma(several) > luma(single) + 40

def test_screen_bezel_follows_the_measured_border(tmp_path):
    thick = tmp_path / 'thick-bezel.mp4'
    _video(thick, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.4', '-vf', 'drawbox=x=28:y=32:w=124:h=176:color=0xE8E4DC:t=fill')
    thin = tmp_path / 'thin-bezel.mp4'
    _video(thin, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.4', '-vf', 'drawbox=x=16:y=16:w=148:h=208:color=0xE8E4DC:t=fill')
    wide = picture_of(thick, 0, 0.4)
    narrow = picture_of(thin, 0, 0.4)
    assert wide['screen'] is True and narrow['screen'] is True
    assert wide['bezel'] > narrow['bezel'] >= 0.06
    source = tmp_path / 'owned.mp4'
    _video(source, '-f', 'lavfi', '-i', 'color=0xE8E4DC:s=180x240:r=30:d=1.2')
    folder = tmp_path / 'framed'
    folder.mkdir()
    rendered = media.render(source, folder, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.2, 'screen': 0, 'bezel': wide['bezel'], 'text': ''}]).model_dump())
    assert abs(rendered['metadata']['duration'] - 1.2) < 0.2

    def luma(x):
        out, err = media.ffmpeg('-ss', '0.4', '-i', folder / 'result.mp4', '-vf', f'crop=8:8:{x}:116,signalstats,metadata=print:file=-', '-frames:v', '1', '-f', 'null', '-')
        return float(re.search(r'YAVG=([\d.]+)', out + '\n' + err).group(1))

    assert luma(80) > luma(8) + 40

def test_deshake_window_follows_the_measured_shift(tmp_path):
    mild = tmp_path / 'mild.mp4'
    _video(mild, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.35', '-f', 'lavfi', '-i', 'color=white:s=50x70:r=30:d=0.35', '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.35', '-f', 'lavfi', '-i', 'color=white:s=50x70:r=30:d=0.35', '-filter_complex', '[0:v][1:v]overlay=8:40[a];[2:v][3:v]overlay=70:40[b];[a][b]concat=n=2:v=1:a=0')
    still = tmp_path / 'still-block.mp4'
    _video(still, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.7', '-f', 'lavfi', '-i', 'color=white:s=50x70:r=30:d=0.7', '-filter_complex', 'overlay=8:40')
    assert reference_layout(mild)['shake'] is True and reference_layout(mild)['shake_rx'] == 8
    assert reference_layout(still)['shake'] is False and reference_layout(still)['shake_rx'] == 0
    chain = motion_filter({'zoom': 1, 'x': 0.5, 'y': 0.5, 'speed': 1, 'stabilize': True, 'shake_rx': 32}, 160, 240, 1.2)
    assert 'deshake=rx=32:ry=32' in chain and 'vidstab' not in chain
    source = tmp_path / 'source.mp4'
    _video(source, '-f', 'lavfi', '-i', 'testsrc=s=180x240:r=30:d=1.2')
    folder = tmp_path / 'steady'
    folder.mkdir()
    rendered = media.render(source, folder, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.2, 'stabilize': True, 'shake_rx': 32, 'text': ''}]).model_dump())
    assert abs(rendered['metadata']['duration'] - 1.2) < 0.2

def test_a_plate_that_appears_later_starts_the_effect_then(tmp_path):
    late = tmp_path / 'late.mp4'
    _video(late, '-f', 'lavfi', '-i', 'color=0x222222:s=180x240:r=30:d=1.8', '-f', 'lavfi', '-i', 'color=0xF4F1EA:s=180x48:r=30:d=1.8', '-filter_complex', "[0:v][1:v]overlay=0:192:enable='gte(t\\,1.0)'")
    picture = picture_of(late, 0, 1.8)
    assert picture['lower'] is True and 0.35 <= picture['hold'] <= 0.7
    flat = tmp_path / 'flat-long.mp4'
    _video(flat, '-f', 'lavfi', '-i', 'color=0x446688:s=180x240:r=30:d=1.2')
    assert picture_of(flat, 0, 1.2)['hold'] == 0 and picture_of(flat, 0, 1.2)['lower'] is False
    source = tmp_path / 'detail.mp4'
    _video(source, '-f', 'lavfi', '-i', 'testsrc=s=180x240:r=30:d=1.6')
    folder = tmp_path / 'gated'
    folder.mkdir()
    rendered = media.render(source, folder, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=Edit(clips=[{'start': 0, 'end': 1.6, 'blur': 8, 'effect_at': 0.5, 'text': ''}]).model_dump())
    assert abs(rendered['metadata']['duration'] - 1.6) < 0.2

    def edge(at):
        import re
        proc = media.ffmpeg('-ss', at, '-i', folder / 'result.mp4', '-vf', 'convolution="0 -1 0 -1 4 -1 0 -1 0",signalstats,metadata=print:file=-', '-frames:v', '1', '-f', 'null', '-')
        text = proc[0] + '\n' + proc[1]
        match = re.search(r'YAVG=([\d.]+)', text)
        return float(match.group(1))

    assert edge(0.2) > edge(1.2)
    caption = tmp_path / 'late.ass'
    write_kinetic(caption, 'Visa days', 1.6, 180, 240, begin=0.5)
    lines = [line for line in caption.read_text().splitlines() if line.startswith('Dialogue:')]
    assert lines[0].split(',')[1] == '0:00:00.50'

def test_owned_words_follow_a_measured_title(tmp_path):
    reference = tmp_path / 'reference.mp4'
    _video(reference, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=2.4', '-f', 'lavfi', '-i', 'color=white:s=48x40:r=30:d=2.4', '-filter_complex', "[0:v][1:v]overlay=x='8+100*min(max((t-0.45)/1.2,0),1)':y=24:enable='between(t,0.45,1.75)'")
    plain = tmp_path / 'plain.mp4'
    _video(plain, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=2.4')
    assert title_motion(plain, 0, 2.4) is None
    motion = title_motion(reference, 0, 2.4)
    assert motion['in'] < 0.5 < motion['out'] < 0.95
    assert motion['x0'] < motion['x1']
    shots = [{'start': 0, 'end': 2.4, 'picture': None}]
    annotate_pictures(reference, shots)
    assert shots[0]['picture']['title']['x0'] < shots[0]['picture']['title']['x1']
    row = dict(start=0, end=2.4, observation={'en': 'SECRET REFERENCE LINE', 'zh': '参考原文'}, visual_type={'en': 'presenter', 'zh': '主讲'}, narrative_role={'en': 'hook', 'zh': '开场'}, motion={'en': 'static hold', 'zh': '固定'}, transition={'en': 'cut', 'zh': '切'}, subtitle_emphasis={'en': 'none', 'zh': '无'}, music={'en': '', 'zh': ''}, emotion={'en': 'calm', 'zh': '平静'}, information_density={'en': 'low', 'zh': '低'}, reusable_method={'en': 'hold the frame', 'zh': '固定机位'}, picture={'title': motion})
    spoken = [{'start': 0, 'end': 2.4, 'original': 'Visa days', 'en': 'Visa days', 'zh': 'Visa days'}]
    edit, report = build([row], 2.4, spoken, False)
    blob = __import__('json').dumps(edit)
    assert 'SECRET REFERENCE LINE' not in blob
    clip = edit['clips'][0]
    assert clip['kinetic'] is True and 'Visa' in clip['text'] and 'SECRET' not in clip['text']
    assert clip['title_x'] < clip['title_x_end'] and clip['title_in'] < clip['title_out'] < 1
    assert all(gap['id'] != 'owned_title' for gap in report['gaps'])
    empty, missing = build([row], 2.4, [], False, script='')
    assert empty['clips'][0]['text'] == '' and empty['clips'][0]['kinetic'] is False
    assert any(gap['id'] == 'owned_title' and gap['essential'] is True for gap in missing['gaps'])
    ass = tmp_path / 'move.ass'
    length = clip['end'] - clip['start']
    write_kinetic(ass, clip['text'], length, 180, 240, begin=clip['title_in'] * length, end=clip['title_out'] * length, origin=(clip['title_x'], clip['title_y']), dest=(clip['title_x_end'], clip['title_y_end']))
    script = ass.read_text()
    assert 'Visa' in script and 'SECRET' not in script
    move = re.search(r'\\move\((\d+),(\d+),(\d+),(\d+),', script)
    assert int(move.group(1)) < int(move.group(3))
    first = next(line for line in script.splitlines() if line.startswith('Dialogue:'))
    assert first.split(',')[2] != '0:00:02.40'
    source = tmp_path / 'owned.mp4'
    _video(source, '-f', 'lavfi', '-i', 'color=0x224466:s=180x240:r=30:d=2.4')
    assert source.resolve() != reference.resolve()
    if media.ass_available():
        folder = tmp_path / 'render'
        folder.mkdir()
        rendered = media.render(source, folder, media.probe(source), SimpleNamespace(transcript=[]), [], 'en', 'original', manual=edit)
        assert abs(rendered['metadata']['duration'] - 2.4) < 0.4
        burned = (folder / 'title-0.ass').read_text()
        assert 'Visa' in burned and '\\move' in burned and 'SECRET' not in burned
