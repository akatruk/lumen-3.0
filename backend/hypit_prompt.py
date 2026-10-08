"""The hand-written Hypit prompt.

A person writes one sentence. That sentence is text:Value. A stored older
line cannot replace it. Open-source Hypit films the project source from it.
"""
import html
import json
import re
from pathlib import Path

RUN = '''<?svml using="@hypit/run-markup@1"?>

<svrun version="1">
  <author source="./main.svml"/>
  <target output="final.video"/>
</svrun>
'''

_MARKUP = '<?svml using="@hypit/markup@1"?>'

_ASSEMBLY = Path(__file__).resolve().parent / 'assembly_prompt.txt'

_RECIPES = '''<?svml using="@hypit/svs@1"?>

<sheet version="1">
  film.vertical {
    background: #09090B;
  }
  media.performance { stack-order: 0; fit: cover; }
  media.host-circle {
    stack-order: 48; fit: cover; clip: rounded; radius: 100;
    content-y: 0.36;
    border-width: 4; border-color: #7DFFC3;
    shadows: "0 10 28 0 #00000099";
  }
  caption.line {
    stack-order: 80;
    x: 0.5; y: 0.9; width: 0.92; height: 0.22;
    anchor-x: center; anchor-y: bottom;
    align: center; block-align: end; wrap: word;
    size: 28; line-height: 1.2; fill: #FFFFFF;
    stroke-color: #09090B; stroke-width: 3;
    background: #09090BE6; padding: "12 22"; radius: 14;
    karaoke: off; cue-enter: none; cue-exit: none;
    lead-frames: 0; tail-frames: 0; handoff: cut;
  }
  caption.host-bottom {
    stack-order: 80;
    x: 0.5; y: 0.88; width: 0.92; height: 0.24;
    anchor-x: center; anchor-y: bottom;
    align: center; block-align: end; wrap: word;
    size: 28; line-height: 1.2; fill: #FFFFFF;
    stroke-color: #09090B; stroke-width: 4;
    background: #09090BE6; padding: "16 20"; radius: 16;
    karaoke: off; cue-enter: none; cue-exit: none;
    lead-frames: 0; tail-frames: 0; handoff: cut;
  }
  caption.host-center {
    stack-order: 80;
    x: 0.5; y: 0.46; width: 0.9; height: 0.28;
    anchor-x: center; anchor-y: center;
    align: center; block-align: center; wrap: word;
    size: 32; line-height: 1.15; fill: #FFFFFF;
    stroke-color: #09090B; stroke-width: 5;
    background: #09090BCC; padding: "18 22"; radius: 18;
    karaoke: off; cue-enter: none; cue-exit: none;
    lead-frames: 0; tail-frames: 0; handoff: cut;
  }
  caption.host-top {
    stack-order: 80;
    x: 0.5; y: 0.18; width: 0.9; height: 0.22;
    anchor-x: center; anchor-y: center;
    align: center; block-align: center; wrap: word;
    size: 30; line-height: 1.15; fill: #FFFFFF;
    stroke-color: #09090B; stroke-width: 4;
    background: #09090BE6; padding: "14 18"; radius: 16;
    karaoke: off; cue-enter: none; cue-exit: none;
    lead-frames: 0; tail-frames: 0; handoff: cut;
  }
  comment.card {
    stack-order: 64;
    background: #F4F1E8; border-color: #7DFFC3; border-width: 3;
    radius: 18; padding-x: 22; padding-y: 16; rotation: 0;
    tail: false; avatar-fallback: none;
    header-size: 1; header-line-height: 1; header-color: #F4F1E8;
    body-size: 32; body-weight: 700; body-color: #16362C; body-max-lines: 4;
    enter: none; exit: none; hold: none;
  }
  comment.column-b {
    stack-order: 64;
    background: #F4F1E8; border-color: #7A5CFF; border-width: 3;
    radius: 18; padding-x: 22; padding-y: 16; rotation: 0;
    tail: false; avatar-fallback: none;
    header-size: 1; header-line-height: 1; header-color: #F4F1E8;
    body-size: 32; body-weight: 700; body-color: #16362C; body-max-lines: 4;
    enter: none; exit: none; hold: none;
  }
  comment.figure {
    stack-order: 70;
    background: #12352C; border-color: #7DFFC3; border-width: 3;
    radius: 22; padding-x: 18; padding-y: 12; rotation: 0;
    tail: false; avatar-fallback: none;
    header-size: 1; header-line-height: 1; header-color: #12352C;
    body-size: 96; body-weight: 700; body-color: #F4FFF8; body-max-lines: 1;
    enter: none; exit: none; hold: none;
  }
  media.motion {
    stack-order: 36; fit: contain; playback: once-start;
  }
  comment.scene {
    stack-order: 72;
    background: #12182A; border-color: #E2C27A; border-width: 2;
    radius: 28; padding-x: 28; padding-y: 22; rotation: 0;
    tail: false; avatar-fallback: none;
    header-size: 1; header-line-height: 1; header-color: #12182A;
    body-size: 40; body-weight: 700; body-color: #F6F1E4; body-max-lines: 4;
    enter: none; exit: none; hold: none;
  }
</sheet>
'''

_PLACEMENTS = {
    'figure': ('8%', '22%', '58%', '46%'),
    'left': ('4%', '50%', '48%', '78%'),
    'right': ('50%', '50%', '96%', '78%'),
    'wide': ('4%', '36%', '68%', '62%'),
    'scene': ('8%', '28%', '92%', '72%'),
}
_STYLE_IDS = {
    'figure': 'figure-style',
    'left': 'column-a',
    'right': 'column-b',
    'wide': 'column-a',
    'scene': 'scene-style',
}


def _as_dict(manual):
    if manual is None:
        return {}
    if isinstance(manual, dict):
        return manual
    if hasattr(manual, 'model_dump'):
        return manual.model_dump()
    return {}


def _levels(manual):
    """Animation, intensity, motion and density. A missing key keeps the written default."""
    data = _as_dict(manual)

    def read(name, default, low=0):
        if name not in data or data.get(name) is None:
            return default
        try:
            value = int(data.get(name))
        except (TypeError, ValueError):
            return default
        value = max(low, min(100, value))
        value -= value % 5
        return max(low, value)

    return {
        'animation': read('card_motion', 60),
        'intensity': read('animation_intensity', 60, 5),
        'motion': read('animation_motion', 80),
        'density': read('animation_density', 70),
    }


def _sentence(levels):
    """The assembly brief, plus the studio sliders. The brief file has no format fields."""
    brief = _ASSEMBLY.read_text(encoding='utf-8').strip()
    levels_line = (
        f"Доля анимации — {levels['animation']}% каждой минуты. "
        f"Интенсивность — {levels['intensity']}. "
        f"Движение — {levels['motion']}%. "
        f"Визуальная плотность — {levels['density']}%."
    )
    return f"{brief}\n\n--- STUDIO LEVELS ---\n{levels_line}\n--- END STUDIO LEVELS ---"


def _output_language(manual):
    """The one language switch, as the existing ru/en/zh code. Absent keeps the base sentence alone."""
    from .language import LanguageError, resolve_locale, short_code
    language = _as_dict(manual).get('language')
    if not language:
        return None
    try:
        return short_code(resolve_locale(language))
    except LanguageError:
        return None


def _has_script(text, script):
    if script == 'ru':
        return any('\u0400' <= char <= '\u04FF' for char in text)
    if script == 'zh':
        return any('\u4e00' <= char <= '\u9fff' for char in text)
    return any(char.isascii() and char.isalpha() for char in text)


def illustration_request(manual=None):
    """The sentence Hypit films. One base prompt, plus the project language and its cards."""
    from .language import LanguageError, audio_instruction, build_language_directive, director_context_blocks, resolve_locale
    levels = _levels(manual)
    sentence = _sentence(levels)
    language = _as_dict(manual).get('language')
    if not language:
        return sentence
    try:
        locale = resolve_locale(language)
    except LanguageError:
        return sentence
    cards, motion, media, context = director_context_blocks(locale)
    from .library_clips import media_block
    listed = media_block()
    if listed:
        media = listed
    return "\n\n".join((
        sentence,
        build_language_directive(locale),
        audio_instruction(manual, locale),
        cards,
        motion,
        media,
        context,
    ))


def picture_prompt(edit, board=None, voiceover=False, reference=None, style=None):
    """The sentence Hypit receives. A saved presentation_prompt cannot replace it."""
    del board, voiceover, reference, style
    return illustration_request(edit)


def plan(edit, board=None):
    """Store the hand prompt. A rebuilt sentence is not the film."""
    del board
    return edit.model_copy(update={
        'presentation': [],
        'presentation_prompt': illustration_request(edit),
        'animation_prompt': '',
    })


def _xml(text):
    return html.escape(text or '', quote=False)


def _caption_dict(caption):
    if isinstance(caption, dict):
        return caption
    if hasattr(caption, 'model_dump'):
        return caption.model_dump()
    return {}


def _graphic_text(caption):
    """The host's stored words. Chinese speech is kept in zh."""
    text = caption.get('zh') or caption.get('original') or caption.get('en') or caption.get('ru') or ''
    text = ' '.join(str(text).split()).replace('{', '').replace('}', '')
    return text.replace('<', '').replace('>', '')


def _plain_label(text):
    text = ' '.join(str(text or '').split()).replace('{', '').replace('}', '')
    return text.replace('<', '').replace('>', '').replace('|', ' ')


def _display_line(caption, language):
    """Card and caption words in the chosen language. Nothing is invented."""
    if language == 'zh':
        for key in ('zh', 'original'):
            text = _plain_label(caption.get(key))
            if _has_script(text, 'zh'):
                return text
        return _graphic_text(caption)
    if language in ('ru', 'en'):
        for key in (language, 'original'):
            text = _plain_label(caption.get(key))
            if text and _has_script(text, language) and not (language == 'en' and _has_script(text, 'ru')):
                return text
        stored = _plain_label(caption.get(language))
        if stored:
            return stored
    return _graphic_text(caption)


def _phrase_rows(manual):
    """Timed lines. display is the switch language. source is what the host said."""
    language = _output_language(manual)
    rows = []
    seen = set()
    for caption in _as_dict(manual).get('captions') or []:
        caption = _caption_dict(caption)
        source = _graphic_text(caption)
        display = _display_line(caption, language)
        if not display or display == '口播' or display in seen:
            continue
        try:
            start = float(caption.get('start') or 0)
            end = float(caption.get('end') or 0)
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        seen.add(display)
        rows.append((start, end, display, source or display))
    return rows


def _spoken_cues(manual):
    """Timed lines shown on the cards. A card may only repeat one of these."""
    return [(start, end, display) for start, end, display, _source in _phrase_rows(manual)]


def _spoken_lines(manual):
    return [text for _start, _end, text in _spoken_cues(manual)]


def _script_side(text):
    return _plain_label(text).replace('@', '').replace(']', '')


def _spoken_script(manual):
    """Shown words are the chosen language. The host's line stays on the speech side for alignment."""
    language = _output_language(manual)
    parts = []
    for _start, _end, display, source in _phrase_rows(manual):
        if language and source and display != source:
            parts.append('<' + _script_side(display) + '|' + _script_side(source) + '>')
        else:
            parts.append(display)
    return ' || '.join(parts)


def generation_prompt(manual):
    """The hand sentence Hypit films. The spoken lines stay off this sentence."""
    return illustration_request(manual)


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


def _clock(seconds):
    text = f'{max(0.0, float(seconds)):.3f}'.rstrip('0').rstrip('.')
    return f'{text or "0"}s'


def _graphic_windows(duration, share=0.6):
    """That share of each minute. The rest of that minute is the host full frame."""
    duration = float(duration or 0)
    share = max(0.0, min(1.0, float(share)))
    if share <= 0:
        return []
    if duration <= 0:
        return [(0.0, 60.0 * share)]
    windows = []
    start = 0.0
    while start < duration - 0.05:
        span = min(60.0, duration - start)
        length = span * share
        if length >= 0.2:
            windows.append((start, length))
        start += 60.0
    return windows


def _overlap(start, end, windows):
    chosen = None
    best = 0.0
    for win_start, win_len in windows:
        lo = max(start, win_start)
        hi = min(end, win_start + win_len)
        if hi - lo > best:
            best = hi - lo
            chosen = (lo, hi - lo)
    if chosen and best >= 0.3:
        return chosen
    return None


_CLAUSE_PUNCT = '，。；：、,;'


def _clauses(text):
    parts = re.split(r'[，。；：、,;]', text or '')
    cleaned = []
    for part in parts:
        piece = part.strip(_CLAUSE_PUNCT + ' \t')
        if len(piece) >= 2:
            cleaned.append(piece)
    return cleaned


def _card_budget(density):
    """How many spoken cards one phrase may film. Seventy is past the old cap of three."""
    value = max(0, min(100, int(density)))
    if value <= 20:
        return 1
    if value <= 45:
        return 2
    if value <= 65:
        return 3
    if value <= 85:
        return 4
    return 6


def _spoken_number(text):
    """A digit or count the host said. A missing amount is not filled in."""
    found = re.search(r'\d+(?:\.\d+)?%?', text)
    if found:
        return found.group(0)
    if '三名' in text or '三个' in text:
        return '三'
    return ''


def _beats(text, density=70):
    """Spoken-clause cards for one phrase. A repeated clause updates that card once."""
    clauses = _clauses(text)
    if not clauses:
        return []
    budget = _card_budget(density)
    if budget <= 1:
        return [(clauses[0], 'wide')]
    number = _spoken_number(text)
    china = next((clause for clause in clauses if '中国' in clause and '泰国' not in clause), '')
    thai = next((clause for clause in clauses if '泰国' in clause or '中泰' in clause), '')
    beats = []
    used = set()

    def add(body, kind):
        body = ' '.join(str(body).split())
        if not body or body in used or len(beats) >= budget:
            return
        used.add(body)
        beats.append((body, kind))

    comparison = bool(china and thai)
    if comparison and number and budget >= 3:
        add(number, 'figure')
    if comparison:
        add(china, 'left')
        add(thai, 'right')
    elif number:
        add(number, 'figure')
    for clause in clauses:
        add(clause, 'wide')
    return beats


def _schedule(beats, start, length):
    """One phrase steps across its graphic overlap. A comparison keeps both columns together."""
    if not beats or length <= 0:
        return []
    groups = []
    index = 0
    while index < len(beats):
        if beats[index][1] == 'left' and index + 1 < len(beats) and beats[index + 1][1] == 'right':
            groups.append(beats[index:index + 2])
            index += 2
        else:
            groups.append(beats[index:index + 1])
            index += 1
    step = length / len(groups)
    timed = []
    for group_index, group in enumerate(groups):
        at = start + group_index * step
        for body, kind in group:
            timed.append((body, kind, at, step))
    return timed


def _cinematic_pair(cues, windows):
    """Two cards on a host-only stretch. The closing line of that stretch stays the host.

    The animation share still owns the graphic windows. A stretch of spoken lines
    outside those windows has no card yet. Its last line stays the host, because
    that is where a source card already sits. The two lines before it get the
    same dark card. A stretch of exactly two lines takes both.
    """
    host = []
    for start, end, text in cues:
        if end - start < 2 or _overlap(start, end, windows):
            continue
        host.append((start, end, text))
    if len(host) < 2:
        return []
    stretches = []
    current = [host[0]]
    for cue in host[1:]:
        if cue[0] - current[-1][1] <= 0.4:
            current.append(cue)
        else:
            stretches.append(current)
            current = [cue]
    stretches.append(current)
    best = None
    for stretch in stretches:
        if len(stretch) >= 3:
            pair = stretch[-3:-1]
        elif len(stretch) == 2:
            pair = stretch
        else:
            continue
        span = sum(end - start for start, end, _text in pair)
        key = (span, pair[0][0])
        if best is None or key > best[0]:
            best = (key, pair)
    if not best:
        return []
    return list(best[1])


_UP = ('增长', '上升', '提高', '利润', 'рост', 'вырос', 'profit', 'growth')
_DOWN = ('下降', '下跌', '风险', '减少', 'паден', 'риск', 'risk', 'fall')


_STAMP = ('签证', '签字', '盖章', '印章', '工作证', 'виза', 'visa', 'stamp', 'печать', 'штамп')
_DOCS = ('文件', '合同', '资料', '银行', '开户', '资本', '股东', '居留', '身份', '护照', '申请', 'документ', 'document', 'банк', 'bank', 'паспорт')
_PATH = ('路', '通道', '距离', '直通', '走廊', '移居', '移民', '海外', 'path', 'путь', 'дорога', '泳池')
_DOOR = ('门', '入口', '门口', '地下', '停车', 'door', 'дверь', 'гараж')
_PLACE = ('中国', '泰国', '城市', '国家', 'Китай', 'Таиланд', '亚马逊', '杜斯特')


def _arrow_way(text):
    """A moving arrow on every phrase. Up or down only when the host said so."""
    down = any(word in text for word in _DOWN)
    up = any(word in text for word in _UP)
    if down and not up:
        return 'down'
    if up and not down:
        return 'up'
    return 'across'


def _fragment_scene(text, parts):
    """A 3–5s scene of a place, object, or action named in this phrase."""
    found = None
    for motif, words in (
        ('stamp', _STAMP),
        ('documents', _DOCS),
        ('path', _PATH),
        ('doorway', _DOOR),
        ('doorway', _PLACE),
    ):
        for word in words:
            at = text.find(word)
            if at >= 0 and (found is None or at < found[0]):
                found = (at, motif, word)
    if found:
        _at, motif, word = found
        label = next((part for part in parts if word in part), word)
        return motif, ' '.join(str(label).split())
    return 'path', (' '.join(str(parts[0]).split()) if parts else '')


_SCENE_FORMATS = (
    'type', 'number', 'flow', 'object', 'split',
    'timeline', 'minimal', 'question', 'montage', 'speaker',
)


def _scene_format(index, previous, number):
    """The next phrase does not repeat the previous scene. A spoken number becomes the big figure."""
    if number and previous != 'number':
        return 'number'
    count = len(_SCENE_FORMATS)
    choice = _SCENE_FORMATS[index % count]
    if choice == previous:
        choice = _SCENE_FORMATS[(index + 1) % count]
    return choice


def _figure_kind(text, density):
    """Every phrase carries every figure. Commas do not pick a single kind."""
    beats = _beats(text, density)
    parts = [body for body, _kind in beats]
    return 'all', parts


def animation_shots(manual, duration):
    """A fresh clip for each spoken line inside the animation share. Nothing is reused."""
    if _as_dict(manual).get('host_frame'):
        return []
    levels = _levels(manual)
    windows = _graphic_windows(duration, levels['animation'] / 100)
    from .library_clips import pick
    shots = []
    used = []
    for start, end, display, source in _phrase_rows(manual):
        slot = _overlap(start, end, windows)
        if not slot:
            continue
        _kind, parts = _figure_kind(display, levels['density'])
        if not parts or slot[1] < 1:
            continue
        motif, _spoken_label = _fragment_scene(source, parts)
        label = ' '.join(str(parts[0]).split())
        span = float(slot[1])
        number = _spoken_number(source) or _spoken_number(display)
        arrow = _arrow_way(source)
        if arrow == 'across':
            arrow = _arrow_way(display)
        previous = shots[-1]['format'] if shots else ''
        fmt = _scene_format(len(shots), previous, number)
        filmed = sum(1 for item in shots if item.get('file'))
        chosen = None if fmt == 'speaker' else pick(source or display, used)
        if chosen:
            used.append(chosen['id'])
        shots.append({
            'id': f'motion-{len(shots) + 1}',
            'file': '' if fmt == 'speaker' else f'{filmed + 1}.mp4',
            'library_id': chosen['id'] if chosen else '',
            'library_path': str(chosen['path']) if chosen else '',
            'library': bool(chosen),
            'kind': fmt,
            'format': fmt,
            'at': slot[0],
            'span': span,
            'parts': parts,
            'number': number,
            'arrow': arrow,
            'motif': motif,
            'fragment_label': label,
            'fragment_s': min(5.0, span),
            'intensity': levels['intensity'],
        })
    return shots


def _motion_block(shots):
    """Pre-made figure clips. Hypit places them; it does not draw the shapes itself."""
    if not shots:
        return '', '', '', ''
    lines = []
    items = []
    for shot in shots:
        if shot.get('format') == 'speaker' or not shot.get('file'):
            continue
        ident = shot['id']
        label = _xml(json.dumps(shot['parts'], ensure_ascii=False))
        lines.append(f'  <text:Value id="{ident}">{label}</text:Value>')
        lines.append(
            f'  <media:Video id="{ident}-file" src="./motion/{shot["file"]}" media-type="video/mp4"/>'
        )
        lines.append(
            f'  <pipeline:Normalize id="{ident}-media" source={{{ident}-file}} clock={{clock}} '
            f'video="primary-moving" audio="none" span-authority="video"/>'
        )
        lines.append(
            f'  <space:Frame id="{ident}-frame" within={{vertical}} left="0%" top="0%" right="100%" bottom="100%"/>'
        )
        items.append(
            f'    <media-track:Item id="{ident}-show" media={{{ident}-media.media}} '
            f'frame={{{ident}-frame}} at="{_clock(shot["at"])}" for="{_clock(shot["span"])}" '
            f'appearance={{recipes.media.motion}}/>'
        )
    if not items:
        return '', '', '', ''
    track = (
        '  <media-track:Track id="motions" timeline={speech.timeline} canvas={vertical}>\n'
        + '\n'.join(items) + '\n'
        '  </media-track:Track>\n'
    )
    opening = '  <import as="media-track" from="@hypit/media-track@1"/>\n'
    return opening, '\n'.join(lines) + '\n', track, '    <film:Track source={motions.visual}/>\n'


def _local_graphics(manual, duration):
    """Cards of the spoken lines, drawn by local Hypit. The instruction stays off the frame."""
    levels = _levels(manual)
    windows = _graphic_windows(duration, levels['animation'] / 100)
    cues = []
    for start, end, text in _spoken_cues(manual):
        slot = _overlap(start, end, windows)
        if slot:
            cues.append((*slot, text))
    frames = []
    stickers = []
    plates = []
    circles = []
    captions = []
    host = bool(_as_dict(manual).get('host_frame'))
    shots = [] if host else animation_shots(manual, duration)
    if host:
        covers = []
        styles = ('host-bottom', 'host-center', 'host-top')
        for index, (start, end, _text) in enumerate(_spoken_cues(manual)):
            captions.append(
                f'    <caption-fine:Use id="minute{index}" at="{_clock(start)}" '
                f'for="{_clock(end - start)}" style={{{styles[index % 3]}}}/>'
            )
    elif shots:
        covers = [
            (shot, index) for index, shot in enumerate(shots) if shot.get('format') != 'speaker'
        ]
    else:
        covers = [
            ({'at': win_start, 'span': win_len}, index)
            for index, (win_start, win_len) in enumerate(windows)
        ]
    for shot, index in covers:
        at = _clock(shot['at'])
        span = _clock(shot['span'])
        plates.append(
            f'    <screen:ColorWash id="plate-{index}" at="{at}" for="{span}" z="1" color="#09090B" opacity="1"/>\n'
            f'    <screen:LightLeak id="glow-{index}" at="{at}" for="{span}" z="2" colors="#7DFFC3,#12182A" angle="28" softness="0.8" travel="40" intensity="0.22" seed="7"/>\n'
            f'    <screen:Vignette id="edge-{index}" at="{at}" for="{span}" z="3" center-x="0.5" center-y="0.42" radius-x="0.72" radius-y="0.62" softness="0.8" color="#09090B" opacity="0.35"/>'
        )
        if shot.get('format') not in ('split', 'timeline'):
            slot = index % 4
            circles.append(f'    <performance:Use style={{circle-{slot}}} at="{at}" for="{span}"/>')
    if not host:
        for index, shot in enumerate(shots or [{'at': start, 'span': length} for start, length in windows]):
            captions.append(
                f'    <caption-fine:Use id="minute{index}" at="{_clock(shot["at"])}" '
                f'for="{_clock(shot["span"])}" style={{spoken-style}}/>'
            )
    serial = 0
    seen = set()
    # A motion clip already carries the spoken words. A second card would cover the figure.
    if host or shots:
        cues = []
    for start, length, text in cues:
        fresh = []
        for body, kind in _beats(text, levels['density']):
            if body in seen:
                continue
            seen.add(body)
            fresh.append((body, kind))
        for body, kind, at, span in _schedule(fresh, start, length):
            serial += 1
            left, top, right, bottom = _PLACEMENTS[kind]
            frames.append(
                f'  <space:Frame id="thought-frame-{serial}" within={{vertical}} '
                f'left="{left}" top="{top}" right="{right}" bottom="{bottom}"/>'
            )
            stickers.append(
                f'    <comment:Sticker id="thought-{serial}" frame={{thought-frame-{serial}}} '
                f'style={{{_STYLE_IDS[kind]}}} at="{_clock(at)}" for="{_clock(span)}">{_xml(body)}</comment:Sticker>'
            )
    if not host:
        for index, (start, end, text) in enumerate(_cinematic_pair(_spoken_cues(manual), windows)):
            body = ' '.join(str(text).split())
            if not body or body in seen:
                continue
            seen.add(body)
            serial += 1
            at = _clock(start)
            span = _clock(end - start)
            left, top, right, bottom = _PLACEMENTS['scene']
            frames.append(
                f'  <space:Frame id="thought-frame-{serial}" within={{vertical}} '
                f'left="{left}" top="{top}" right="{right}" bottom="{bottom}"/>'
            )
            stickers.append(
                f'    <comment:Sticker id="thought-{serial}" frame={{thought-frame-{serial}}} '
                f'style={{scene-style}} at="{at}" for="{span}">{_xml(body)}</comment:Sticker>'
            )
    frame_block = ('\n'.join(frames) + '\n') if frames else ''
    scene_style = ''
    if any('scene-style' in line for line in stickers):
        scene_style = '  <comment:Style id="scene-style" recipe={recipes.comment.scene} font={caption-font}/>\n'
    if stickers:
        cards = (
            '  <comment:Style id="column-a" recipe={recipes.comment.card} font={caption-font}/>\n'
            '  <comment:Style id="column-b" recipe={recipes.comment.column-b} font={caption-font}/>\n'
            '  <comment:Style id="figure-style" recipe={recipes.comment.figure} font={caption-font}/>\n'
            + scene_style
            + '  <comment:Track id="thought-cards" canvas={vertical} timeline={speech.timeline}>\n'
            + '\n'.join(stickers) + '\n'
            '  </comment:Track>\n'
        )
        card_track = '    <film:Track source={thought-cards.track}/>\n'
    else:
        cards = ''
        card_track = ''
    plate = ''
    if plates:
        plate = (
            '  <screen:Track id="plate" timeline={speech.timeline} canvas={vertical}>\n'
            + '\n'.join(plates) + '\n'
            '  </screen:Track>\n'
        )
    elif host:
        plate = '  <screen:Track id="plate" timeline={speech.timeline} canvas={vertical}/>\n'
    circle = '\n'.join(circles)
    caption = ''
    if captions:
        caption = (
            '  <fonts:Stack id="caption-font" family="noto-sans" weight="700" style="normal">\n'
            '    <fonts:Fallback family="noto-sans-sc" weight="700" style="normal"/>\n'
            '  </fonts:Stack>\n'
            '  <caption-fine:Style id="spoken-style" recipe={recipes.caption.line} font={caption-font}/>\n'
            '  <caption-fine:Style id="host-bottom" recipe={recipes.caption.host-bottom} font={caption-font}/>\n'
            '  <caption-fine:Style id="host-center" recipe={recipes.caption.host-center} font={caption-font}/>\n'
            '  <caption-fine:Style id="host-top" recipe={recipes.caption.host-top} font={caption-font}/>\n'
            '  <caption:Hidden id="graphic-hidden"/>\n'
            '  <caption-fine:Track id="spoken-line" document={story.caption} timeline={speech.timeline}>\n'
            '    <caption-fine:Use id="graphic-off" style={graphic-hidden} during="program"/>\n'
            + '\n'.join(captions) + '\n'
            '  </caption-fine:Track>\n'
        )
    return frame_block, plate, cards, caption, circle, card_track


def author_source(edit, width, height, board=None, language=None, voiceover=False, reference=None, style=None, duration=None, cyrillic_font=None):
    """Film the source on the local Hypit runtime. Hosted generation is not in this prompt."""
    manual = dict(edit) if isinstance(edit, dict) else edit.model_dump()
    manual.pop('presentation_prompt', None)
    manual.pop('animation_prompt', None)
    del board, voiceover, reference, style, cyrillic_font
    width = max(2, int(width))
    height = max(2, int(height))
    cues = _spoken_cues(manual)
    if duration is None:
        duration = max((end for _start, end, _text in cues), default=60.0)
    request = _xml(generation_prompt(manual))
    spoken = _spoken_script(manual)
    # `<shown|spoken>` is Hypit dual text. CDATA makes the next phrase look nested.
    script = spoken if '<' in spoken else _xml(spoken)
    chosen = _output_language(manual) or language
    language_attr = _language_attr(spoken, chosen)
    frames, plate, cards, caption, circle, card_track = _local_graphics(manual, duration)
    motion_import, motion_decls, motion_body, motion_track = _motion_block(animation_shots(manual, duration))
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
  <import as="caption" from="@hypit/caption@1"/>
  <import as="caption-fine" from="@hypit/caption-fine@1"/>
  <import as="fonts" from="@hypit/fonts-open@1"/>
  <import as="comment" from="@hypit/comment-sticker@1"/>
  <import as="screen" from="@hypit/screen-overlay@1"/>
{motion_import}

  <script id="story">
    <picture>{script}</picture>
  </script>
  <text:Value id="request">{request}</text:Value>

  <media:Video id="footage" src="./source.mp4" media-type="video/mp4"/>
  <space:Canvas id="vertical" width="{width}" height="{height}"/>
  <program:Clock id="clock" frame-rate="30"/>
{motion_decls}  <space:Frame id="speech-frame" within={{vertical}} left="0%" top="0%" right="100%" bottom="100%"/>
  <space:AspectFrame id="host-circle-0" within={{vertical}} x="84%" y="16%" width="180px" aspect="1/1" anchor="center"/>
  <space:AspectFrame id="host-circle-1" within={{vertical}} x="18%" y="70%" width="230px" aspect="1/1" anchor="center"/>
  <space:AspectFrame id="host-circle-2" within={{vertical}} x="82%" y="74%" width="160px" aspect="1/1" anchor="center"/>
  <space:AspectFrame id="host-circle-3" within={{vertical}} x="50%" y="15%" width="210px" aspect="1/1" anchor="center"/>
{frames}
  <pipeline:Normalize id="footage-media" source={{footage}}
    video="primary-moving" audio="default" span-authority="video" clock={{clock}}/>
  <whisperx:SemanticTake id="picture-semantic" narrative={{story}}
    segment={{story.segment.picture}} media={{footage-media.media}}{language_attr}/>
  <time:Timeline id="speech" clock={{clock}}>
    <time:Take source={{picture-semantic.take}}/>
  </time:Timeline>
{caption}{cards}{plate}  <performance:Style id="circle-0" frame={{host-circle-0}} appearance={{recipes.media.host-circle}}/>
  <performance:Style id="circle-1" frame={{host-circle-1}} appearance={{recipes.media.host-circle}}/>
  <performance:Style id="circle-2" frame={{host-circle-2}} appearance={{recipes.media.host-circle}}/>
  <performance:Style id="circle-3" frame={{host-circle-3}} appearance={{recipes.media.host-circle}}/>
  <performance:Style id="full-style" frame={{speech-frame}} appearance={{recipes.media.performance}}/>
  <performance:Track id="performance" timeline={{speech.timeline}} canvas={{vertical}}>
    <performance:Use style={{full-style}} during="program"/>
{circle}
  </performance:Track>
{motion_body}  <film:Film id="main" canvas={{vertical}} timeline={{speech.timeline}} appearance={{recipes.film.vertical}}>
    <film:Track source={{plate.track}}/>
{motion_track}    <film:Track source={{performance.visual}}/>
{card_track}    <film:Track source={{spoken-line.track}}/>
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
