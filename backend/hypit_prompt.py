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
    lines = [
        'Собери один непрерывный ролик одним файлом, без склейки из кусков. '
        'Каждую фразу договаривай до конца: не обрывай её и не перескакивай на следующую секцию, пока она не закончена. '
        'Один и тот же фрагмент не повторяй. '
        'Убери паузы между фразами, моменты, где ведущий поправляет волосы или молчит, и реплики не по теме.'
    ]
    if manual.get('voice_cleanup'):
        lines.append('Очисти голос ведущего от посторонних шумов, гула и шипения. Речь не ускоряй.')
    if manual.get('normalize'):
        lines.append('Выровняй громкость речи.')
    if manual.get('picture_quality'):
        lines.append('Убери шум изображения и верни резкость. Кадр не смягчай и не увеличивай.')
    if manual.get('subtitles'):
        size = {'small': 'мелкие', 'large': 'крупные'}.get(manual.get('font_size'), 'средние')
        place = 'вверху' if manual.get('position') == 'top' else 'внизу'
        ink = 'жёлтые' if manual.get('color') == 'yellow' else 'белые'
        lines.append(f'Добавь субтитры по речи: {size}, {place}, {ink}.')
    names = {'zh': 'китайском', 'ru': 'русском', 'en': 'английском'}
    host = manual.get('host_language')
    captions = manual.get('subtitle_language')
    if host in names:
        lines.append(f'Речь ведущего на {names[host]}.')
    if captions in names and captions == host:
        lines.append(f'Субтитры на {names[captions]}, на том же языке, что и речь.')
    elif captions in names:
        lines.append(f'Субтитры на {names[captions]}.')
    graphics = manual.get('effects_language') if manual.get('effects_language') in names else host
    if graphics in names and graphics == host:
        lines.append(f'Графика и вставки на {names[graphics]}, на том же языке, что и речь.')
    elif graphics in names:
        lines.append(f'Графика и вставки на {names[graphics]}.')
    spoken = _host_speech(manual)
    if host in names and spoken:
        script = ' '.join(spoken)
        if len(script) > 3500:
            script = script[:3500].rsplit(' ', 1)[0]
        lines.append(f'Озвучка на {names[host]}: {script}')
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


def _label(value):
    if isinstance(value, dict):
        text = value.get('en') or value.get('zh') or ''
    else:
        text = value or ''
    return ' '.join(str(text).split())


def _shot_notes(shots):
    """Distinct reference frames. The same measured name is not repeated."""
    kinds, motions = [], []
    seen_kinds, seen_motions = set(), set()
    for shot in shots or []:
        if not isinstance(shot, dict):
            continue
        kind = _label(shot.get('visual_type'))[:80]
        motion = _label(shot.get('motion'))[:80]
        if kind and kind.lower() not in seen_kinds:
            seen_kinds.add(kind.lower())
            kinds.append(kind)
        if motion and motion.lower() not in seen_motions:
            seen_motions.add(motion.lower())
            motions.append(motion)
    return kinds[:8], motions[:4]


def host_diameter(shots=None, style=None):
    """Share of the frame width for the host circle.

    A talking-head reference keeps the face large. A measured pip smaller than
    the face is not the host.
    """
    kinds, motions = _shot_notes(shots)
    blob = ' '.join(kinds + motions).lower()
    talking = any(word in blob for word in (
        'talking head', 'presenter', 'ведущ', '主讲', 'avatar', 'cutout', 'overlay', 'inset', 'photo',
    ))
    chosen = 0.50 if talking or not blob else 0.46
    avatar = ((style or {}).get('stage') or {}).get('avatar') if isinstance(style, dict) else None
    try:
        measured = float((avatar or {}).get('d'))
    except (TypeError, ValueError):
        measured = 0.0
    if measured >= 0.36:
        chosen = max(chosen, min(0.62, measured))
    return round(chosen, 3)


def reference_brief(shots):
    """The reference method, as words. Footage, faces and unstated facts stay out."""
    kinds, motions = _shot_notes(shots)
    if not kinds and not motions:
        return ''
    blob = ' '.join(kinds + motions).lower()
    moves = []
    if any(word in blob for word in ('talking head', 'presenter', 'ведущ', '主讲')):
        moves.append('ведущий остаётся главным')
    if any(word in blob for word in ('overlay', 'inset', 'picture-in-picture', 'photo', 'врез')):
        moves.append('внизу на каждую фразу сменяется врезка предмета речи')
    if any(word in blob for word in ('caption', 'subtitle', 'kinetic', 'keyword', 'подпис')):
        moves.append('подпись сменяется вместе с фразой')
    if any(word in blob for word in ('static', 'hold')):
        moves.append('камера почти стоит, двигается графика')
    if any(word in blob for word in ('screen', 'ui', 'document', 'callout', 'headline', 'scan')):
        moves.append('врезка показывает схему или документ сказанного')
    line = f" По измерению референса, разных кадров: {len(kinds)}."
    if moves:
        line += ' Приём: ' + ', '.join(moves) + '.'
    if kinds:
        line += ' Кадры референса: ' + '; '.join(kinds[:5]) + '.'
    line += (
        " Чужие лица, чужие кадры и несказанные факты не бери. "
        "Раскладка меняется на каждой фразе этого ролика."
    )
    return line


def _look_line(shots=None, style=None):
    """Art direction for the one prompt. The reference analysis changes it."""
    percent = int(round(host_diameter(shots, style) * 100))
    return (
        " Анимация дорогая и собранная, как моушн-графика, а не одна строка на тёмном поле. "
        "Тёмный фон. На одну сказанную мысль одна карточка: заголовок и, если слова другие, мелкая подпись. "
        "Вторую карточку с тем же текстом не ставь. Лента, стрелка или схема только между разными словами. "
        "Если в речи есть место, дом или предмет, одна карточка показывает кадр этого предмета и подпись. "
        f"Ведущий крупный: кружок на {percent}% ширины кадра, лицо читается. Фраза — подпись внизу. "
        "Кружок ведущего стоит выше подписи и не закрывает текст. "
        "Внизу одна строка подписи. Вторую копию тех же слов не рисуй, буквы не накладывай друг на друга. "
        "На карточке и в подписи фраза закончена, не обрывок из нескольких знаков. "
        "На экране только сказанные слова, с пробелами. Логин, водяной знак и склеенную латиницу вроде обрезанного имени не пиши. "
        "Цвета карточек разные: тёмное стекло, зелёная, фиолетовая, золотая пометка. "
        "Раскладку меняй от фразы к фразе и от ролика к ролику: схема из карточек, две колонки, стопка "
        "или полный кадр места с кружком ведущего. Одну и ту же плашку не повторяй. "
        "Карточки выезжают по очереди на долю ползунка движения, лента между ними дорисовывается, "
        "ведущий подъезжает к графике и слегка смещается. "
        "Сколько коротких роликов внутри графики решает ползунок вставок. "
        "Каждый такой ролик показывает тему этой речи: названную страну или названное дело. "
        "Чужую страну и чужую организацию не вставляй. "
        "Исходный ролик остаётся одним файлом. "
        "Бери только слова, которые были сказаны. Лицо не смягчай и исходный кадр не увеличивай."
        + reference_brief(shots)
    )


def _host_speech(manual):
    """Lines the host speaks in the selected language. Missing text adds no line."""
    host = (manual or {}).get('host_language')
    if host not in ('zh', 'ru', 'en'):
        return []
    lines = []
    for caption in (manual or {}).get('captions') or []:
        if not isinstance(caption, dict):
            caption = caption.model_dump() if hasattr(caption, 'model_dump') else {}
        if host == 'zh':
            text = caption.get('zh') or caption.get('original') or ''
        elif host == 'en':
            text = caption.get('en') or ''
        else:
            text = caption.get('ru') or ''
            if not text:
                original = ' '.join(str(caption.get('original') or '').split())
                if any('а' <= char.lower() <= 'я' or char in 'ёЁ' for char in original):
                    text = original
        text = ' '.join(str(text).split())
        if text and text != '口播':
            lines.append(text)
    return lines


def _spoken(manual):
    from .presentation_graphics import _caption_text

    lines = []
    for caption in (manual or {}).get('captions') or []:
        text = _caption_text(caption)
        if text:
            lines.append(text.replace('{', '').replace('}', ''))
    return lines


def _caption_recipe(manual):
    """Subtitle controls are recipe words Hypit draws. They are not page styles."""
    manual = manual or {}
    if not manual.get('subtitles'):
        return ''
    size = {'small': 36, 'large': 72}.get(manual.get('font_size'), 52)
    top = manual.get('position') == 'top'
    y = '0.1' if top else '0.9'
    anchor = 'top' if top else 'bottom'
    fill = '#FFE14A' if manual.get('color') == 'yellow' else '#FFFFFF'
    return f'''
  caption.speech {{
    stack-order: 80;
    x: 0.5; y: {y}; width: 0.88; height: 0.2;
    anchor-x: center; anchor-y: {anchor};
    align: center; block-align: end; inline-size: fixed;
    wrap: word;
    size: {size}; line-height: 1.08; fill: {fill};
    background: #00000000; padding: "0"; radius: 0;
    karaoke: current; active-fill: {fill};
    cue-enter: none; cue-exit: none;
    lead-frames: 0; tail-frames: 0; handoff: cut;
  }}'''


def recipes_sheet(manual=None):
    """The footage stays sharp. The percent is not a grade or a vignette."""
    return f'''<?svml using="@hypit/svs@1"?>

<sheet version="1">
  film.vertical {{
    background: #09090B;
  }}
  media.performance {{ stack-order: 0; fit: cover; }}{_caption_recipe(manual)}
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


def reference_shots(source):
    """Reference frames stored for the project that owns this source file."""
    from pathlib import Path
    from .style_match import shots_of
    try:
        from .studio import state
        current = state(Path(source).resolve().parent.name)
    except Exception:
        return []
    if not current:
        return []
    return shots_of(current.get('dna'))


_TRANSITION = {
    'fade': 'затухание через чёрный',
    'crossfade': 'растворение',
    'zoom': 'наезд',
    'wipe': 'шторка',
    'wipe-up': 'шторка вверх',
    'wipe-down': 'шторка вниз',
    'circle': 'круг',
    'diagtl': 'диагональ',
    'diagtr': 'диагональ',
    'diagbl': 'диагональ',
    'diagbr': 'диагональ',
}


def _montage_line(manual):
    """Montage choices that used to change only the page. They are sentences now."""
    manual = manual or {}
    skipped, transitions, texts = [], [], []
    zoom = 1.0
    own_insert = False
    for clip in manual.get('clips') or []:
        if not isinstance(clip, dict):
            continue
        if clip.get('approved', True) is False:
            try:
                skipped.append(f"{float(clip.get('start')):.1f}–{float(clip.get('end')):.1f} с")
            except (TypeError, ValueError):
                skipped.append('фрагмент')
            continue
        label = _TRANSITION.get(clip.get('transition') or 'cut')
        if label and label not in transitions:
            transitions.append(label)
        text = ' '.join(str(clip.get('text') or '').split())
        if text and text != '口播' and text not in texts:
            texts.append(text[:80])
        try:
            zoom = max(zoom, float(clip.get('zoom') or 1))
        except (TypeError, ValueError):
            pass
        if clip.get('external_broll') or clip.get('cutaway') or clip.get('picture_insert'):
            own_insert = True
    lines = []
    if skipped:
        lines.append('Не включай фрагменты: ' + ', '.join(skipped[:8]) + '.')
    if transitions:
        lines.append('Переходы между фразами: ' + ', '.join(transitions) + '.')
    if texts:
        lines.append('Текст на сцене: ' + '; '.join(texts[:8]) + '.')
    if zoom > 1.01:
        lines.append(f'Приближение кадра до {zoom:.2f}. Лицо остаётся резким.')
    if own_insert:
        lines.append('В ролике есть врезка из своего материала. Логин и водяной знак на врезке не пиши.')
    return (' ' + ' '.join(lines)) if lines else ''


def picture_prompt(edit, board=None, voiceover=False, reference=None, style=None):
    """The prompt that is filmed. Speech, sliders and the reference analysis are in it."""
    from .presentation_graphics import animation_brief

    manual = edit if isinstance(edit, dict) else edit.model_dump()
    return (
        animation_brief(manual)
        + _board_line(board)
        + _delivery_line(manual, voiceover)
        + _montage_line(manual)
        + _look_line(reference, style)
    )


def author_source(edit, width, height, board=None, language=None, voiceover=False, reference=None, style=None):
    """One prompt for the whole video. Sliders and the other controls are that request."""
    manual = edit if isinstance(edit, dict) else edit.model_dump()
    width = max(2, int(width))
    height = max(2, int(height))
    spoken_language = _prompt_language(manual, language)
    request = _xml(picture_prompt(manual, board, voiceover, reference, style).replace('{', '').replace('}', ''))
    script = _xml(' '.join(_spoken(manual)))
    language_attr = f' language="{spoken_language}"' if script else ''
    caption_imports = ''
    caption_nodes = ''
    caption_track = ''
    if manual.get('subtitles') and script:
        caption_language = manual.get('subtitle_language') or spoken_language
        caption_font = {'zh': 'noto-sans-sc', 'ru': 'noto-sans'}.get(caption_language, 'noto-sans')
        caption_imports = '''
  <import as="fonts" from="@hypit/fonts-open@1"/>
  <import as="caption-fine" from="@hypit/caption-fine@1"/>'''
        caption_nodes = f'''
  <fonts:Stack id="caption-font" family="{caption_font}" weight="700" style="normal"/>
  <caption-fine:Style id="speech-captions" recipe={{recipes.caption.speech}} font={{caption-font}}/>
  <caption-fine:Track id="captions" document={{story.caption}} timeline={{speech.timeline}}>
    <caption-fine:Use style={{speech-captions}}/>
  </caption-fine:Track>'''
        caption_track = '\n    <film:Track source={captions.track}/>'
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
  <import as="recipes" source="./recipes.svs"/>{caption_imports}

  <script id="story">
    <picture>{script}</picture>
  </script>
  <text:Value id="request">{request}</text:Value>

  <media:Video id="footage" src="./source.mp4"/>
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
{caption_nodes}
  <performance:Style id="performance-style" frame={{speech-frame}} appearance={{recipes.media.performance}}/>
  <performance:Track id="performance" timeline={{speech.timeline}} canvas={{vertical}}>
    <performance:Use style={{performance-style}} during="program"/>
  </performance:Track>
  <film:Film id="main" canvas={{vertical}} timeline={{speech.timeline}} appearance={{recipes.film.vertical}}>
    <film:Track source={{performance.visual}}/>{caption_track}
  </film:Film>
  <render:Video id="final" composition={{main.composition}} timeline={{speech.timeline}}/>
</svml>
'''
    return recipes_sheet(manual) + svml


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
