"""The Effects percent is a Hypit author source.

Hypit consumes SVML. ``render:Video`` compiles ``film:Film`` into the picture.
0% is the performance of the footage alone. 100% keeps the text treatment for
the whole timeline (``during="program"``). A middle percent is the same
composition with ``start``/``end`` covering that fraction of the footage.
"""
import html

RECIPES = '''<?svml using="@hypit/svs@1"?>

<sheet version="1">
  film.vertical {
    background: #09090B;
  }
  media.performance { stack-order: 0; fit: cover; }
  text.title {
    stack-order: 90;
    weight: 900; size: 64; align: center;
    fill: #FFFFFF; tracking: -1;
  }
</sheet>
'''

RUN = '''<?svml using="@hypit/run-markup@1"?>

<svrun version="1">
  <author source="./main.svml"/>
  <target output="final.video"/>
</svrun>
'''


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


def author_source(share, duration, width, height, line):
    """SVML Hypit checks and builds. The percent is the text-track window."""
    share = max(0, min(100, int(share or 0)))
    duration = max(1 / 30, float(duration or 0))
    width = max(2, int(width))
    height = max(2, int(height))
    words = _xml(line)
    text_imports = ''
    text = ''
    titles = ''
    if share > 0:
        window = 'during="program"' if share >= 100 else f'start="0s" end="{duration * share / 100:.3f}s"'
        text_imports = '''
  <import as="fonts" from="@hypit/fonts-open@1"/>
  <import as="text" from="@hypit/typography-track@1"/>'''
        text = f'''
  <fonts:Stack id="title-font" family="inter" weight="900" style="normal"/>
  <text:Style id="title-style" recipe={{recipes.text.title}} font={{title-font}}/>
  <text:Track id="titles" timeline={{speech.timeline}}>
    <text:Area id="title" placement={{title-frame}} style={{title-style}} {window}>
      {words}
    </text:Area>
  </text:Track>
'''
        titles = '\n    <film:Track source={titles.track}/>'
    return f'''<?svml using="@hypit/markup@1"?>

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
  <space:Frame id="title-frame" within={{vertical}} left="6%" top="6%" right="94%" bottom="22%"/>

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
{text}
  <film:Film id="main" canvas={{vertical}} timeline={{speech.timeline}} appearance={{recipes.film.vertical}}>
    <film:Track source={{performance.visual}}/>{titles}
  </film:Film>
  <render:Video id="final" composition={{main.composition}} timeline={{speech.timeline}}/>
</svml>
'''
