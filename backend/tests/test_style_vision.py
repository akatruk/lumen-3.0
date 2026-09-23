from types import SimpleNamespace
from backend import media
from backend.manual import Edit
from backend.style_vision import _join, black_spans, chroma_plate, color_sample, flat_background, grade_between, highlight_window, light_between, measure, pace_of, picture_of, reference_layout, visual_track
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
    title = tmp_path / 'title.ass'
    write_kinetic(title, 'Visa', 1.2, 160, 240)
    assert '\\fscx100' in title.read_text()
    split = tmp_path / 'split.mp4'
    _video(split, '-f', 'lavfi', '-i', 'color=red:s=90x240:r=30:d=1', '-f', 'lavfi', '-i', 'color=blue:s=90x240:r=30:d=1', '-filter_complex', '[0:v][1:v]hstack=inputs=2')
    assert reference_layout(split)['split'] is True
    bar = tmp_path / 'bar.mp4'
    _video(bar, '-f', 'lavfi', '-i', 'color=0x222222:s=160x240:r=30:d=1', '-f', 'lavfi', '-i', 'color=white:s=160x16:r=30:d=1', '-filter_complex', 'overlay=0:224')
    found = reference_layout(bar)
    assert found['bar'] is True and found['split'] is False
    jumped = tmp_path / 'jumped.mp4'
    _video(jumped, '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.35', '-f', 'lavfi', '-i', 'color=white:s=50x70:r=30:d=0.35', '-f', 'lavfi', '-i', 'color=0x111111:s=180x240:r=30:d=0.35', '-f', 'lavfi', '-i', 'color=white:s=50x70:r=30:d=0.35', '-filter_complex', '[0:v][1:v]overlay=8:40[a];[2:v][3:v]overlay=120:40[b];[a][b]concat=n=2:v=1:a=0')
    assert reference_layout(jumped)['shake'] is True
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
    assert _join(other, 0.6) == 'cut'
    opened = tmp_path / 'opened.mp4'
    _video(opened, '-f', 'lavfi', '-i', 'color=red:s=180x240:r=30:d=0.56', '-f', 'lavfi', '-i', 'color=red:s=180x240:r=30:d=0.08', '-f', 'lavfi', '-i', 'color=blue:s=60x80:r=30:d=0.08', '-f', 'lavfi', '-i', 'color=blue:s=180x240:r=30:d=0.56', '-filter_complex', '[1:v][2:v]overlay=60:80[m];[0:v][m][3:v]concat=n=3:v=1:a=0')
    assert _join(opened, 0.6) == 'circle'
    blend = tmp_path / 'blend.mp4'
    _video(blend, '-f', 'lavfi', '-i', 'color=red:s=180x240:r=30:d=0.56', '-f', 'lavfi', '-i', 'color=red:s=180x240:r=30:d=0.08', '-f', 'lavfi', '-i', 'color=blue:s=180x240:r=30:d=0.08', '-f', 'lavfi', '-i', 'color=blue:s=180x240:r=30:d=0.56', '-filter_complex', '[1:v][2:v]blend=all_mode=average[m];[0:v][m][3:v]concat=n=3:v=1:a=0')
    assert _join(blend, 0.6) == 'crossfade'

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
