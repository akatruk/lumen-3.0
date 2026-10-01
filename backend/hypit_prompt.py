"""One Hypit prompt for the whole picture.

The percent, the intensity and the spoken words are that prompt. Hypit builds
one video from it. Lumen does not cut the footage into scenes or set a
parameter on each frame.
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
    return html.escape(text or '', quote=False)


def _board_line(board):
    """Enabled effect names, as words in the one prompt."""
    if not isinstance(board, dict):
        return ''
    effects = board.get('effects') if isinstance(board.get('effects'), dict) else {}
    names = [str(key) for key, enabled in effects.items() if enabled]
    if not names:
        return ''
    return ' Эффекты: ' + ', '.join(names) + '.'


def _delivery_line(manual, voiceover=False):
    """Every other saved control, as words in the same prompt. The file stays one piece."""
    manual = manual or {}
    lines = ['Собери один непрерывный ролик из исходника целиком. На отрезки не режь и не склеивай.']
    if manual.get('voice_cleanup'):
        lines.append('Очисти голос ведущего от посторонних шумов, гула и шипения. Длину ролика не меняй.')
    if manual.get('normalize'):
        lines.append('Выровняй громкость речи.')
    if manual.get('picture_quality'):
        lines.append('Убери шум изображения и верни резкость. Кадр не смягчай и не увеличивай.')
    if manual.get('subtitles'):
        size = {'small': 'мелкие', 'large': 'крупные'}.get(manual.get('font_size'), 'средние')
        place = 'вверху' if manual.get('position') == 'top' else 'внизу'
        ink = 'жёлтые' if manual.get('color') == 'yellow' else 'белые'
        lines.append(f'Добавь субтитры по речи: {size}, {place}, {ink}.')
    music = manual.get('music') if isinstance(manual.get('music'), dict) else None
    if music and music.get('asset_id'):
        gain = music.get('gain_db', -24)
        fade_in = music.get('fade_in', 1)
        fade_out = music.get('fade_out', 2)
        duck = 'Приглушай её под речь.' if music.get('duck', True) else 'Под речь не приглушай.'
        lines.append(
            f'Добавь фоновую музыку: {gain:g} дБ, появление {fade_in:g} с, затухание {fade_out:g} с. {duck}'
        )
    accents = []
    names = {'chime': 'колокольчик', 'click': 'щелчок', 'whoosh': 'свист'}
    for clip in manual.get('clips') or []:
        if not isinstance(clip, dict) or not clip.get('approved', True):
            continue
        for effect in clip.get('sound_effects') or []:
            kind = effect.get('kind') if isinstance(effect, dict) else ''
            label = names.get(kind)
            if label and label not in accents:
                accents.append(label)
    if accents:
        lines.append('Звуковые акценты: ' + ', '.join(accents) + '.')
    if voiceover:
        lines.append('В ролике звучит закадровый голос вместо исходной речи.')
    return ' ' + ' '.join(lines)


def _look_line():
    """Art direction for the one prompt. The layout may change; the footage is not cut."""
    return (
        " Анимация дорогая и собранная, как моушн-графика, а не одна строка на тёмном поле. "
        "Тёмный фон. Несколько карточек одной мысли: крупный заголовок, мелкая подпись под ним, "
        "между карточками лента, стрелка или схема. "
        "Если в речи есть место, дом или предмет, одна карточка показывает кадр этого предмета и подпись. "
        "Ведущий маленький и рядом с графикой: кружок или скруглённый портрет. Фраза — подпись внизу. "
        "Цвета карточек разные: тёмное стекло, зелёная, фиолетовая, золотая пометка. "
        "Раскладку меняй от фразы к фразе и от ролика к ролику: схема из карточек, две колонки, стопка "
        "или полный кадр места с кружком ведущего. Одну и ту же плашку не повторяй. "
        "Бери только слова, которые были сказаны. Лицо не смягчай и исходный кадр не увеличивай."
    )


def _spoken(manual):
    from .presentation_graphics import _caption_text

    lines = []
    for caption in (manual or {}).get('captions') or []:
        text = _caption_text(caption)
        if text:
            lines.append(text.replace('{', '').replace('}', ''))
    return lines


def recipes_sheet():
    """The footage stays sharp. The percent is not a grade or a vignette."""
    return '''<?svml using="@hypit/svs@1"?>

<sheet version="1">
  film.vertical {
    background: #09090B;
  }
  media.performance { stack-order: 0; fit: cover; }
</sheet>
'''


def _prompt_language(manual, language=None):
    """WhisperX needs the language of the words in the prompt."""
    if isinstance(language, str) and language.startswith('zh'):
        return 'zh'
    if language in ('en', 'ru', 'zh'):
        return language
    blob = ' '.join(_spoken(manual))
    if any('\u4e00' <= char <= '\u9fff' for char in blob):
        return 'zh'
    if any('а' <= char.lower() <= 'я' or char in 'ёЁ' for char in blob):
        return 'ru'
    return 'en'


def author_source(edit, width, height, board=None, language=None, voiceover=False):
    """One prompt for the whole video. Sliders and the other controls are that request."""
    from .presentation_graphics import animation_brief

    manual = edit if isinstance(edit, dict) else edit.model_dump()
    width = max(2, int(width))
    height = max(2, int(height))
    spoken_language = _prompt_language(manual, language)
    request = _xml((
        animation_brief(manual) + _board_line(board) + _delivery_line(manual, voiceover) + _look_line()
    ).replace('{', '').replace('}', ''))
    script = _xml(' '.join(_spoken(manual)))
    language_attr = f' language="{spoken_language}"' if script else ''
    svml = f'''{_MARKUP}

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

  <media:Video id="footage" src="./source.mp4"/>
  <space:Canvas id="vertical" width="{width}" height="{height}"/>
  <program:Clock id="clock" frame-rate="30"/>
  <space:Frame id="speech-frame" within={{vertical}} left="0%" top="0%" right="100%" bottom="100%"/>

  <pipeline:Normalize id="footage-media" source={{footage}}
    video="primary-moving" audio="none" span-authority="video" clock={{clock}}/>
  <whisperx:SemanticTake id="picture-semantic" narrative={{story}}
    segment={{story.segment.picture}} media={{footage-media.media}}{language_attr}/>
  <time:Timeline id="speech" clock={{clock}}>
    <time:Take source={{picture-semantic.take}}/>
  </time:Timeline>

  <performance:Style id="performance-style" frame={{speech-frame}} appearance={{recipes.media.performance}}/>
  <performance:Track id="performance" timeline={{speech.timeline}} canvas={{vertical}}>
    <performance:Use style={{performance-style}} during="program"/>
  </performance:Track>
  <film:Film id="main" canvas={{vertical}} timeline={{speech.timeline}} appearance={{recipes.film.vertical}}>
    <film:Track source={{performance.visual}}/>
  </film:Film>
  <render:Video id="final" composition={{main.composition}} timeline={{speech.timeline}}/>
</svml>
'''
    return recipes_sheet() + svml


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
