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


def recipes_sheet():
    """The footage stays sharp. The percent is a timed window, not a grade."""
    return '''<?svml using="@hypit/svs@1"?>

<sheet version="1">
  film.vertical {
    background: #09090B;
  }
  media.performance { stack-order: 0; fit: cover; }
  caption.line {
    stack-order: 80;
    x: 0.5; y: 0.93; width: 0.88; height: 0.14;
    anchor-x: center; anchor-y: bottom;
    align: center; block-align: end; inline-size: fixed; wrap: word;
    size: 36; line-height: 1.05; fill: #FFFFFF;
    stroke-color: #09090B; stroke-width: 3;
    background: #09090BE6; padding: "12 22"; radius: 14;
    karaoke: off; cue-enter: none; cue-exit: none;
    lead-frames: 0; tail-frames: 0; handoff: cut;
  }
  comment.card {
    stack-order: 64;
    background: #111827F2; border-color: #FFFFFF33; border-width: 1;
    radius: 22; padding-x: 28; padding-y: 22; rotation: 0;
    tail: false; avatar-fallback: none;
    body-size: 34; body-weight: 700; body-color: #FFFFFF; body-max-lines: 4;
    enter: none; exit: none; hold: none;
  }
</sheet>
'''


def _prompt_language(manual, language=None):
    """WhisperX aligns the spoken words, so their script wins over the project tag."""
    blob = ' '.join(_spoken(manual))
    if any('\u4e00' <= char <= '\u9fff' for char in blob):
        return 'zh'
    if any('а' <= char.lower() <= 'я' or char in 'ёЁ' for char in blob):
        return 'ru'
    if isinstance(language, str) and language.startswith('zh'):
        return 'zh'
    if language in ('en', 'ru', 'zh'):
        return language
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


def illustration_percent(edit):
    """The one control on the project page. A missing value is 50."""
    manual = edit if isinstance(edit, dict) else edit.model_dump() if hasattr(edit, 'model_dump') else {}
    raw = None if not isinstance(manual, dict) else manual.get('illustration_percent', manual.get('card_motion'))
    if raw is None:
        return 50
    try:
        number = int(round(float(raw)))
    except (TypeError, ValueError):
        return 50
    return max(0, min(100, number // 5 * 5))


def illustration_request(percent):
    """The request Hypit built. The typo and the line breaks are part of that text."""
    return (
        "analyze the style of both reference video and reference video 2, make edit to\n"
        "src video 2. focus on adding the appropriate visuals to make it more\n"
        "illustrative. make ilustration "
        f"{int(percent)}% from all time video"
    )


def picture_prompt(edit, board=None, voiceover=False, reference=None, style=None):
    """The prompt that is filmed. Only the illustration percent changes it."""
    del board, voiceover, reference, style
    return illustration_request(illustration_percent(edit))


def _script_words(text):
    """Spoken words safe inside a Script body. Markers and tags are not words."""
    cleaned = str(text or '').replace('{', '').replace('}', '')
    cleaned = cleaned.replace('@', '').replace('<', '').replace('>', '').replace('||', ' ')
    return ' '.join(cleaned.split())


def _cue_script(manual):
    """One caption cue per spoken phrase. ``||`` is the cue break, not a cut."""
    lines = []
    for text in _spoken(manual):
        cleaned = _script_words(text)
        if cleaned:
            lines.append(cleaned)
    return ' || '.join(lines)


def _clock_ms(millis):
    """Format an integer millisecond count. No second round trip through float."""
    millis = int(millis)
    if millis <= 0:
        return '0s'
    if millis % 1000 == 0:
        return f'{millis // 1000}s'
    whole, frac = divmod(millis, 1000)
    return f'{whole}.{frac:03d}'.rstrip('0') + 's'


# Hypit captures round(duration * clock). The clock is the source rate.
_SOURCE_FPS = 30


def _program_frames(duration):
    """Frames at 30fps. A duration already on a frame boundary stays there."""
    frames = float(duration) * 30
    rounded = round(frames)
    if abs(frames - rounded) <= 1e-4:
        return max(1, int(rounded))
    return max(1, int(frames))


def _capture_rate(duration):
    """Author clock Hypit honors as the screenshot count.

    A finished minute is the source rate. A lower clock stretches a handful of
    screenshots across the whole program.
    """
    return str(_SOURCE_FPS)


def _max_end_ms(duration):
    """Latest millisecond whose projection is still inside the program.

    Hypit rejects an instant past the last frame. Rounding a remainder up
    (3.466667s → 3.467s) lands one millisecond outside that frame.
    """
    return _program_frames(duration) * 1000 // 30


def _bounded_ms(start, length, duration):
    """Start and length in milliseconds. The end stays inside the program."""
    if duration <= 0 or length <= 0:
        return None
    limit = _max_end_ms(duration)
    start_ms = int(round(float(start) * 1000))
    end_ms = int(round((float(start) + float(length)) * 1000))
    if start_ms < 0:
        start_ms = 0
    if start_ms > limit:
        start_ms = limit
    if end_ms > limit:
        end_ms = limit
    if end_ms - start_ms < 33:
        return None
    return start_ms, end_ms - start_ms


def _program_seconds(manual, duration):
    if duration is not None:
        try:
            value = float(duration)
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass
    from .presentation_graphics import _footage_seconds
    return _footage_seconds(manual)


def _presence_seconds(manual):
    """The same seconds the slider sentence names. 80% is 48 seconds a minute."""
    from .presentation_graphics import animation_levels
    coverage = animation_levels(manual)['coverage']
    return coverage, coverage * 60 // 100


def _graphic_windows(span, duration):
    """Graphic time inside each minute, clipped so it stays in the program.

    100% is the whole program. 0% is no graphic. Anything between repeats
    ``span`` seconds from the start of every minute the file actually reaches.
    Each window is milliseconds whose end frame is still inside the video.
    """
    if span >= 60:
        return 'program'
    if span <= 0 or duration <= 0:
        return []
    windows = []
    minute = 0
    while minute * 60 < duration - 1e-6 and minute < 240:
        start = float(minute * 60)
        room = duration - start
        if room < 1 / 30:
            break
        length = float(span) if span <= room else room
        bounded = _bounded_ms(start, length, duration)
        if bounded:
            windows.append(bounded)
        minute += 1
    return windows


def _has_cyrillic(text):
    return any('а' <= char.lower() <= 'я' or char in 'ёЁ' for char in text)


def _timed_lines(manual):
    from .presentation_graphics import _caption_text
    lines = []
    for caption in (manual or {}).get('captions') or []:
        if not isinstance(caption, dict):
            caption = caption.model_dump() if hasattr(caption, 'model_dump') else {}
        text = _script_words(_caption_text(caption))
        if not text:
            continue
        try:
            start = float(caption.get('start'))
            end = float(caption.get('end'))
        except (TypeError, ValueError):
            continue
        if end > start:
            lines.append((start, end, text))
    return lines


def _card_pieces(manual, windows, duration):
    """One card per spoken thought that falls inside a graphic window.

    A comment card draws its own letters from the open font catalog. That
    catalog's Latin face does not carry Cyrillic, so those thoughts stay on
    the bottom line, which can take the installed Cyrillic file.
    """
    if not windows:
        return []
    pieces = []
    for start, end, text in _timed_lines(manual):
        if _has_cyrillic(text):
            continue
        start = max(0.0, start)
        end = min(float(duration), end)
        if end - start < 1 / 30:
            continue
        if windows == 'program':
            chosen = _bounded_ms(start, end - start, duration)
        else:
            chosen = None
            best = 0
            for win_start, win_len in windows:
                lo = max(int(round(start * 1000)), win_start)
                hi = min(int(round(end * 1000)), win_start + win_len)
                if hi - lo > best:
                    best = hi - lo
                    chosen = (lo, hi - lo)
            if best < 33:
                chosen = None
        if chosen:
            pieces.append((*chosen, text))
        if len(pieces) >= 40:
            break
    return pieces


_CARD_BOXES = (
    ('8%', '14%', '86%', '42%'),
    ('12%', '20%', '90%', '48%'),
    ('6%', '26%', '80%', '54%'),
    ('16%', '12%', '92%', '40%'),
)


def _caption_uses(windows, span):
    if windows == 'program':
        return '    <caption-fine:Use id="graphic-program" style={spoken-style} during="program"/>'
    if not windows:
        return '    <caption-fine:Use id="graphic-off" style={graphic-hidden} during="program"/>'
    lines = ['    <caption-fine:Use id="graphic-off" style={graphic-hidden} during="program"/>']
    for index, (start_ms, length_ms) in enumerate(windows):
        lines.append(
            f'    <caption-fine:Use id="minute{index}-{span}" at="{_clock_ms(start_ms)}" '
            f'for="{_clock_ms(length_ms)}" style={{spoken-style}}/>'
        )
    return '\n'.join(lines)


def _graphic_markup(manual, duration, cyrillic_font):
    """Bottom line for the graphic window, plus one local card per thought."""
    if not _cue_script(manual):
        return '', '', '', ''
    _coverage, span = _presence_seconds(manual)
    windows = _graphic_windows(span, duration)
    pieces = _card_pieces(manual, windows, duration)
    imports = (
        '  <import as="caption" from="@hypit/caption@1"/>\n'
        '  <import as="caption-fine" from="@hypit/caption-fine@1"/>\n'
        '  <import as="fonts" from="@hypit/fonts-open@1"/>\n'
    )
    font = ''
    if cyrillic_font:
        font = (
            f'  <media:Font id="cyrillic-face" src="{_xml(cyrillic_font)}" '
            'weight="700" style="normal"/>\n'
        )
        style = (
            '  <caption-fine:Style id="spoken-style" recipe={recipes.caption.line} font={caption-font}>\n'
            '    <caption-fine:Fallback font={cyrillic-face}/>\n'
            '  </caption-fine:Style>'
        )
    else:
        style = '  <caption-fine:Style id="spoken-style" recipe={recipes.caption.line} font={caption-font}/>'
    spoken = (
        '  <fonts:Stack id="caption-font" family="noto-sans" weight="700" style="normal">\n'
        '    <fonts:Fallback family="noto-sans-sc" weight="700" style="normal"/>\n'
        '  </fonts:Stack>\n'
        f'{font}{style}\n'
        '  <caption:Hidden id="graphic-hidden"/>\n'
        '  <caption-fine:Track id="spoken-line" document={story.caption} timeline={speech.timeline}>\n'
        f'{_caption_uses(windows, span)}\n'
        '  </caption-fine:Track>'
    )
    frames = ''
    cards = ''
    film = '    <film:Track source={spoken-line.track}/>\n'
    if pieces:
        imports += '  <import as="comment" from="@hypit/comment-sticker@1"/>\n'
        frame_lines = []
        sticker_lines = []
        for index, (start_ms, length_ms, text) in enumerate(pieces, start=1):
            left, top, right, bottom = _CARD_BOXES[(index - 1) % len(_CARD_BOXES)]
            frame_lines.append(
                f'  <space:Frame id="thought-frame-{index}" within={{vertical}} '
                f'left="{left}" top="{top}" right="{right}" bottom="{bottom}"/>'
            )
            sticker_lines.append(
                f'    <comment:Sticker id="thought-{index}" frame={{thought-frame-{index}}} '
                f'style={{thought-style}} at="{_clock_ms(start_ms)}" for="{_clock_ms(length_ms)}">'
                f'{_xml(text)}</comment:Sticker>'
            )
        frames = '\n'.join(frame_lines) + '\n'
        cards = (
            '  <comment:Style id="thought-style" recipe={recipes.comment.card} font={caption-font}/>\n'
            '  <comment:Track id="thought-cards" canvas={vertical} timeline={speech.timeline}>\n'
            + '\n'.join(sticker_lines) + '\n'
            '  </comment:Track>\n'
        )
        film = '    <film:Track source={thought-cards.track}/>\n' + film
    return imports, frames, spoken + '\n' + cards, film


def _bound_request(manual, duration):
    """Put the short request on the film when the picture has no spoken script.

    An unreferenced ``text:Value`` is dropped by the build, and the video is
    then only the source footage. Create video sends no captions, so this
    binding is what carries the request into the picture.
    """
    if _cue_script(manual) or illustration_percent(manual) <= 0:
        return '', '', '', ''
    _coverage, span = _presence_seconds(manual)
    windows = _graphic_windows(span, duration)
    if not windows:
        return '', '', '', ''
    imports = (
        '  <import as="fonts" from="@hypit/fonts-open@1"/>\n'
        '  <import as="comment" from="@hypit/comment-sticker@1"/>\n'
    )
    frames = (
        '  <space:Frame id="request-frame" within={vertical} '
        'left="8%" top="14%" right="86%" bottom="42%"/>\n'
    )
    if windows == 'program':
        stickers = (
            '    <comment:Sticker id="request-card" comment={request} '
            'frame={request-frame} style={request-style} during="program"/>'
        )
    else:
        stickers = '\n'.join(
            f'    <comment:Sticker id="request-card-{index}" comment={{request}} '
            f'frame={{request-frame}} style={{request-style}} '
            f'at="{_clock_ms(start_ms)}" for="{_clock_ms(length_ms)}"/>'
            for index, (start_ms, length_ms) in enumerate(windows, start=1)
        )
    graphic = (
        '  <fonts:Stack id="caption-font" family="noto-sans" weight="700" style="normal">\n'
        '    <fonts:Fallback family="noto-sans-sc" weight="700" style="normal"/>\n'
        '  </fonts:Stack>\n'
        '  <comment:Style id="request-style" recipe={recipes.comment.card} font={caption-font}/>\n'
        '  <comment:Track id="request-cards" canvas={vertical} timeline={speech.timeline}>\n'
        f'{stickers}\n'
        '  </comment:Track>\n'
    )
    film = '    <film:Track source={request-cards.track}/>\n'
    return imports, frames, graphic, film


def author_source(edit, width, height, board=None, language=None, voiceover=False, reference=None, style=None, duration=None, cyrillic_font=None):
    """One prompt for the whole video. The slider percent is a window in that prompt."""
    manual = edit if isinstance(edit, dict) else edit.model_dump()
    width = max(2, int(width))
    height = max(2, int(height))
    spoken_language = _prompt_language(manual, language)
    request = _xml(picture_prompt(manual, board, voiceover, reference, style).replace('{', '').replace('}', ''))
    script = _xml(_cue_script(manual))
    language_attr = f' language="{spoken_language}"' if script else ''
    program = _program_seconds(manual, duration)
    clock = _capture_rate(program)
    imports, frames, graphic, film_graphic = _graphic_markup(manual, program, cyrillic_font)
    if not script:
        bound_imports, bound_frames, bound_graphic, bound_film = _bound_request(manual, program)
        imports += bound_imports
        frames += bound_frames
        graphic += bound_graphic
        film_graphic += bound_film
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
{imports}

  <script id="story">
    <picture>{script}</picture>
  </script>
  <text:Value id="request">{request}</text:Value>

  <media:Video id="footage" src="./source.mp4"/>
  <space:Canvas id="vertical" width="{width}" height="{height}"/>
  <program:Clock id="clock" frame-rate="{clock}"/>
  <space:Frame id="speech-frame" within={{vertical}} left="0%" top="0%" right="100%" bottom="100%"/>
{frames}

  <pipeline:Normalize id="footage-media" source={{footage}}
    video="primary-moving" audio="default" span-authority="video" clock={{clock}}/>
  <whisperx:SemanticTake id="picture-semantic" narrative={{story}}
    segment={{story.segment.picture}} media={{footage-media.media}}{language_attr}/>
  <time:Timeline id="speech" clock={{clock}}>
    <time:Take source={{picture-semantic.take}}/>
  </time:Timeline>

{graphic}  <performance:Style id="performance-style" frame={{speech-frame}} appearance={{recipes.media.performance}}/>
  <performance:Track id="performance" timeline={{speech.timeline}} canvas={{vertical}}>
    <performance:Use style={{performance-style}} during="program"/>
  </performance:Track>
  <film:Film id="main" canvas={{vertical}} timeline={{speech.timeline}} appearance={{recipes.film.vertical}}>
    <film:Track source={{performance.visual}}/>
{film_graphic}  </film:Film>
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
