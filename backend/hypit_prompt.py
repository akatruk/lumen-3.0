"""The hand-written Hypit prompt.

A person writes one sentence. That sentence is text:Value. A stored older
line cannot replace it. Open-source Hypit films the project source from it.
"""
import html
from pathlib import Path

RUN = '''<?svml using="@hypit/run-markup@1"?>

<svrun version="1">
  <author source="./main.svml"/>
  <target output="final.video"/>
</svrun>
'''

_MARKUP = '<?svml using="@hypit/markup@1"?>'

HAND_PROMPT = (
    "Один ролик, без склейки. Анимация 40%  ведущий в кружке, передний план — графика сказанного. Интенсивность 60%, движение 80%, плотность 70%. Рост — стрелка вверх, падение — стрелка вниз, число — крупная цифра, сравнение — две колонки, срок — отметка на шкале. Только сказанные слова.\n"
    "Эффекты: color, glow, shadow, blur по краю, kinetic, progress, speed на коротких акцентах, stabilize, split на сравнении, screen, zoom на цифре. Переходы: растворение, шторка, круг. Субтитры средние, белые, внизу. Голос очистить, громкость выровнять, лицо и исходный кадр резкие. Музыка −24 дБ, тише под речь. Звуковые акценты: щелчок, свист, колокольчик."
)

_RECIPES = '''<?svml using="@hypit/svs@1"?>

<sheet version="1">
  film.vertical {
    background: #09090B;
  }
  media.performance { stack-order: 0; fit: cover; }
</sheet>
'''


def illustration_request(percent=40):
    """The sentence Hypit films. The stored edit is not this sentence."""
    del percent
    return HAND_PROMPT


def picture_prompt(edit, board=None, voiceover=False, reference=None, style=None):
    """The sentence Hypit receives. A saved presentation_prompt cannot replace it."""
    del edit, board, voiceover, reference, style
    return illustration_request()


def plan(edit, board=None):
    """Store the hand prompt. A rebuilt sentence is not the film."""
    del board
    return edit.model_copy(update={
        'presentation': [],
        'presentation_prompt': illustration_request(),
        'animation_prompt': '',
    })


def _xml(text):
    return html.escape(text or '', quote=False)


def _spoken_script(manual):
    """Spoken lines for alignment. They are not the prompt."""
    lines = []
    for caption in (manual or {}).get('captions') or []:
        if not isinstance(caption, dict):
            caption = caption.model_dump() if hasattr(caption, 'model_dump') else {}
        text = caption.get('zh') or caption.get('original') or caption.get('en') or caption.get('ru') or ''
        text = ' '.join(str(text).split()).replace('{', '').replace('}', '')
        text = text.replace('<', '').replace('>', '')
        if text and text != '口播':
            lines.append(text)
    for clip in (manual or {}).get('clips') or []:
        if not isinstance(clip, dict):
            clip = clip.model_dump() if hasattr(clip, 'model_dump') else {}
        if clip.get('approved', True) is False:
            continue
        text = ' '.join(str(clip.get('text') or '').split()).replace('{', '').replace('}', '')
        text = text.replace('<', '').replace('>', '')
        if text and text != '口播' and text not in lines:
            lines.append(text)
    return ' || '.join(lines)


def _language_attr(script, language):
    if not script:
        return ''
    if any('\u4e00' <= char <= '\u9fff' for char in script):
        code = 'zh'
    elif language in ('zh', 'en', 'ru'):
        code = language
    else:
        code = 'en'
    return f' language="{code}"'


def author_source(edit, width, height, board=None, language=None, voiceover=False, reference=None, style=None, duration=None, cyrillic_font=None):
    """Film the full source. text:Value is the hand prompt and nothing else."""
    manual = dict(edit) if isinstance(edit, dict) else edit.model_dump()
    manual.pop('presentation_prompt', None)
    manual.pop('animation_prompt', None)
    del board, voiceover, reference, style, duration, cyrillic_font
    width = max(2, int(width))
    height = max(2, int(height))
    request = _xml(illustration_request())
    script = _xml(_spoken_script(manual))
    language_attr = _language_attr(script, language)
    return _RECIPES + f'''{_MARKUP}

<svml>
  <import from="@hypit/script@1"/>
  <import as="media" from="@hypit/media@1"/>
  <import as="pipeline" from="@hypit/media-pipeline@1"/>
  <import as="time" from="@hypit/timeline-author@1"/>
  <import as="whisperx" from="@hypit/whisperx@1"/>
  <import as="space" from="@hypit/spatial@1"/>
  <import as="program" from="@hypit/program-space@1"/>
  <import as="performance" from="@hypit/performance@1"/>
  <import as="text" from="@hypit/text@1"/>
  <import as="film" from="@hypit/film@1"/>
  <import as="render" from="@hypit/render-hyperframes@1"/>
  <import as="recipes" source="./recipes.svs"/>

  <script id="story">
    <picture>{script}</picture>
  </script>
  <text:Value id="request">{request}</text:Value>

  <media:Video id="footage" src="./source.mp4" media-type="video/mp4"/>
  <space:Canvas id="vertical" width="{width}" height="{height}"/>
  <program:Clock id="clock" frame-rate="30"/>
  <space:Frame id="speech-frame" within={{vertical}} left="0%" top="0%" right="100%" bottom="100%"/>

  <pipeline:Normalize id="footage-media" source={{footage}}
    video="primary-moving" audio="default" span-authority="video" clock={{clock}}/>
  <whisperx:SemanticTake id="picture-semantic" narrative={{story}}
    segment={{story.segment.picture}} media={{footage-media.media}}{language_attr}/>
  <time:Timeline id="speech" clock={{clock}}>
    <time:Take source={{picture-semantic.take}}/>
  </time:Timeline>

  <performance:Style id="full-style" frame={{speech-frame}} appearance={{recipes.media.performance}}/>
  <performance:Track id="performance" timeline={{speech.timeline}} canvas={{vertical}}>
    <performance:Use style={{full-style}} during="program"/>
  </performance:Track>
  <film:Film id="main" canvas={{vertical}} timeline={{speech.timeline}} appearance={{recipes.film.vertical}}>
    <film:Track source={{performance.visual}}/>
  </film:Film>
  <render:Video id="final" composition={{main.composition}} timeline={{speech.timeline}}/>
</svml>
'''


def write_author(folder, prompt):
    """Split the stored prompt into the recipe sheet and the author source."""
    folder = Path(folder)
    if _MARKUP in prompt:
        sheet, svml = prompt.split(_MARKUP, 1)
        (folder / 'recipes.svs').write_text(sheet.strip() + '\n')
        (folder / 'main.svml').write_text(_MARKUP + svml)
    else:
        (folder / 'main.svml').write_text(prompt)
    (folder / 'build.svrun').write_text(RUN)
