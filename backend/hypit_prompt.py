"""The effects percent is a Hypit author source.

Hypit consumes SVML. ``render:Video`` compiles ``film:Film`` into the picture.
0% is the footage alone. A higher percent lengthens the type window and
strengthens the grade, vignette, and type size. 75% and above keep the type
for the whole timeline (``during="program"``).
"""
import html

RUN = '''<?svml using="@hypit/run-markup@1"?>

<svrun version="1">
  <author source="./main.svml"/>
  <target output="final.video"/>
</svrun>
'''

_MARKUP = '<?svml using="@hypit/markup@1"?>'


def treatment_line(manual, language='en'):
    """Words already on the edit. A mark is used when the edit has no line."""
    order = ('zh', 'original', 'en') if str(language).startswith('zh') else ('en', 'original', 'zh')
    for caption in (manual or {}).get('captions') or []:
        if not isinstance(caption, dict):
            caption = caption.model_dump() if hasattr(caption, 'model_dump') else {}
        for key in order:
            text = ' '.join(str(caption.get(key) or '').split())
            if text and text != '口播' and not text.isdigit():
                return text[:42]
    return '•'


def _xml(text):
    return html.escape(text or '•', quote=False)


def _strength(board):
    if not isinstance(board, dict):
        return None, 1.0
    effects = board.get('effects') if isinstance(board.get('effects'), dict) else {}
    try:
        amount = max(0.4, min(1.6, float(board.get('amount') or 1)))
    except (TypeError, ValueError):
        amount = 1.0
    return effects, amount


def _flags(share, board):
    """Color, vignette, and kinetic. 0% adds none. A missing board follows the percent."""
    if share <= 0:
        return False, False, False, 1.0
    effects, amount = _strength(board)
    if effects is None:
        return True, share >= 45, False, 1.0
    return bool(effects.get('color')), bool(effects.get('shadow')), bool(effects.get('kinetic')), amount


def _levels(share, scale, color, vignette):
    if share >= 75:
        contrast, saturation, shade, size = 1.22, 1.28, 0.55, 72
    elif share >= 45:
        contrast, saturation, shade, size = 1.12, 1.14, 0.35, 56
    else:
        contrast, saturation, shade, size = 1.04, 1.06, 0.35, 48
    contrast = 1 + (contrast - 1) * scale
    saturation = 1 + (saturation - 1) * scale
    shade = shade * scale
    size = max(32, min(96, round(size * scale)))
    return (
        f'{contrast:.3f}' if color else '',
        f'{saturation:.3f}' if color else '',
        f'{shade:.3f}' if vignette else '',
        size,
    )


def recipes_sheet(share, board=None):
    """Recipe numbers for this percent. Board strength scales them."""
    share = max(0, min(100, int(share or 0)))
    color, vignette, kinetic, scale = _flags(share, board)
    contrast, saturation, shade, size = _levels(share, scale, color, vignette)
    lines = [
        'film.vertical {',
        '    background: #09090B;',
        '  }',
        '  media.performance { stack-order: 0; fit: cover; }',
    ]
    if contrast:
        lines.append(f'  film.grade {{ contrast: {contrast}; saturation: {saturation}; }}')
    if shade:
        lines.append(f'  film.vignette {{ amount: {shade}; }}')
    if share > 0:
        lines.append(
            '  text.title {'
            f' stack-order: 90; weight: 900; size: {size}; align: center;'
            ' fill: #FFFFFF; tracking: -1;'
            ' }'
        )
    if kinetic:
        lines.append(
            '  text.kinetic {'
            f' stack-order: 91; weight: 900; size: {min(96, size + 8)}; align: center;'
            ' fill: #FFFFFF; tracking: -3;'
            ' }'
        )
    body = '\n'.join(lines)
    return f'''<?svml using="@hypit/svs@1"?>

<sheet version="1">
  {body}
</sheet>
'''


def author_source(share, duration, width, height, line, board=None):
    """SVML Hypit checks, plus the recipe sheet for this percent."""
    share = max(0, min(100, int(share or 0)))
    duration = max(1 / 30, float(duration or 0))
    width = max(2, int(width))
    height = max(2, int(height))
    color, vignette, kinetic, _scale = _flags(share, board)
    words = _xml(line)
    text_imports = ''
    text = ''
    titles = ''
    grade = ''
    shade = ''
    if color:
        grade = '\n  <film:Grade id="look" recipe={recipes.film.grade}/>'
    if vignette:
        shade = '\n  <film:Vignette id="shade" recipe={recipes.film.vignette}/>'
    if share > 0:
        window = 'during="program"' if share >= 75 else f'start="0s" end="{duration * share / 100:.3f}s"'
        text_imports = '''
  <import as="fonts" from="@hypit/fonts-open@1"/>
  <import as="text" from="@hypit/typography-track@1"/>'''
        kinetic_area = ''
        if kinetic:
            kinetic_area = f'''
    <text:Area id="kinetic" placement={{title-frame}} style={{kinetic-style}} {window}>
      {words}
    </text:Area>'''
        kinetic_style = '\n  <text:Style id="kinetic-style" recipe={recipes.text.kinetic} font={title-font}/>' if kinetic else ''
        text = f'''
  <fonts:Stack id="title-font" family="inter" weight="900" style="normal"/>
  <text:Style id="title-style" recipe={{recipes.text.title}} font={{title-font}}/>{kinetic_style}
  <text:Track id="titles" timeline={{speech.timeline}}>
    <text:Area id="title" placement={{title-frame}} style={{title-style}} {window}>
      {words}
    </text:Area>{kinetic_area}
  </text:Track>
'''
        titles = '\n    <film:Track source={titles.track}/>'
    svml = f'''{_MARKUP}

<svml>
  <import from="@hypit/script@1"/>
  <import as="media" from="@hypit/media@1"/>
  <import as="pipeline" from="@hypit/media-pipeline@1"/>
  <import as="time" from="@hypit/timeline-author@1"/>
  <import as="whisperx" from="@hypit/whisperx@1"/>
  <import as="space" from="@hypit/spatial@1"/>
  <import as="program" from="@hypit/program-space@1"/>
  <import as="performance" from="@hypit/performance@1"/>{text_imports}
  <import as="film" from="@hypit/film@1"/>
  <import as="render" from="@hypit/render-hyperframes@1"/>
  <import as="recipes" source="./recipes.svs"/>

  <script id="story">
    <picture></picture>
  </script>

  <media:Video id="footage" src="./cut.mp4"/>
  <space:Canvas id="vertical" width="{width}" height="{height}"/>
  <program:Clock id="clock" frame-rate="30"/>
  <space:Frame id="speech-frame" within={{vertical}} left="0%" top="0%" right="100%" bottom="100%"/>
  <space:Frame id="title-frame" within={{vertical}} left="6%" top="72%" right="94%" bottom="94%"/>

  <pipeline:Normalize id="footage-media" source={{footage}}
    video="primary-moving" audio="none" span-authority="video" clock={{clock}}/>
  <whisperx:SemanticTake id="picture-semantic" narrative={{story}}
    segment={{story.segment.picture}} media={{footage-media.media}}/>
  <time:Timeline id="speech" clock={{clock}}>
    <time:Take source={{picture-semantic.take}}/>
  </time:Timeline>

  <performance:Style id="performance-style" frame={{speech-frame}} appearance={{recipes.media.performance}}/>
  <performance:Track id="performance" timeline={{speech.timeline}} canvas={{vertical}}>
    <performance:Use style={{performance-style}} during="program"/>
  </performance:Track>
{text}{grade}{shade}
  <film:Film id="main" canvas={{vertical}} timeline={{speech.timeline}} appearance={{recipes.film.vertical}}>
    <film:Track source={{performance.visual}}/>{titles}
  </film:Film>
  <render:Video id="final" composition={{main.composition}} timeline={{speech.timeline}}/>
</svml>
'''
    return recipes_sheet(share, board) + svml


def write_author(folder, prompt):
    """Split the stored prompt into the recipe sheet and the author source."""
    from pathlib import Path
    folder = Path(folder)
    if _MARKUP in prompt:
        sheet, svml = prompt.split(_MARKUP, 1)
        (folder / 'recipes.svs').write_text(sheet.strip() + '\n')
        (folder / 'main.svml').write_text(_MARKUP + svml)
    else:
        (folder / 'main.svml').write_text(prompt)
    (folder / 'build.svrun').write_text(RUN)
