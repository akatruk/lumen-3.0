"""Presentation graphics sized as a share of the finished video.

The scan reads speech and scene text already on the cut. It does not invent
facts. Each beat is stored in Russian, English and Chinese. The picture uses
the selected voiceover language when there is one, otherwise the project language.
"""
import re
from typing import Literal
from pydantic import Field, model_validator
from .schemas import Strict

class PresentationLine(Strict):
    en: str = Field(min_length=1, max_length=48)
    zh: str = Field(min_length=1, max_length=48)
    ru: str = Field(min_length=1, max_length=48)

class PresentationBeat(Strict):
    kind: Literal['window', 'mini']
    start: float = Field(ge=0, le=86400)
    end: float = Field(gt=0, le=86400)
    title: PresentationLine
    body: PresentationLine | None = None
    x: float = Field(ge=0.12, le=0.88)
    y: float = Field(ge=0.12, le=0.88)

    @model_validator(mode='after')
    def span(self):
        if self.end <= self.start:
            raise ValueError('presentation_range')
        if self.kind == 'mini' and self.body is None:
            raise ValueError('mini_needs_body')
        if self.kind == 'window':
            self.body = None
        return self

def shown_language(project_language, voice_language=None):
    if voice_language in ('ru', 'en', 'zh'):
        return voice_language
    if project_language in ('ru', 'en', 'zh'):
        return project_language
    return 'en'

def _clean(text, limit=42):
    text = re.sub(r'[{}\\\r\n]+', ' ', str(text or ''))
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0].strip()
    return cut or text[:limit].strip()

def _cyrillic(text):
    return bool(re.search(r'[А-Яа-яЁё]', text or ''))

def _copy(en, zh, original):
    en_s = _clean(en) or _clean(original) or _clean(zh)
    zh_s = _clean(zh) or _clean(original) or _clean(en)
    ru_s = _clean(original) if _cyrillic(original) else en_s
    if min(len(en_s), len(zh_s), len(ru_s)) < 2:
        return None
    return {'en': en_s, 'zh': zh_s, 'ru': ru_s}

def _field(row, key):
    if isinstance(row, dict):
        return row.get(key) or ''
    return getattr(row, key, '') or ''

def _contexts(edit):
    """Speech moments on the finished timeline, then scene text where speech is absent."""
    found = []
    cursor = 0.0
    clips = [clip for clip in edit.clips if clip.approved]
    for clip in clips:
        length = clip.end - clip.start
        spoke = False
        for cap in edit.captions:
            overlap_start = max(cap.start, clip.start)
            overlap_end = min(cap.end, clip.end)
            if overlap_end - overlap_start < 0.25:
                continue
            text = _copy(_field(cap, 'en'), _field(cap, 'zh'), _field(cap, 'original'))
            if not text:
                continue
            at = cursor + (overlap_start - clip.start)
            if found and abs(found[-1][0] - at) < 0.3 and found[-1][1] == text:
                spoke = True
                continue
            found.append((at, text))
            spoke = True
        if not spoke:
            text = _copy(clip.text, clip.text, clip.text)
            if text:
                found.append((cursor + min(0.4, length * 0.2), text))
        cursor += length
    return found, cursor

def _pick(lines, count):
    if count >= len(lines):
        return list(range(len(lines)))[:count]
    if count == 1:
        return [len(lines) // 2]
    return [round(i * (len(lines) - 1) / (count - 1)) for i in range(count)]

_SPOTS = ((0.74, 0.26), (0.28, 0.32), (0.70, 0.68), (0.30, 0.72))

def build(edit):
    share = int(edit.presentation_share or 0)
    lines, total = _contexts(edit)
    if share <= 0 or total <= 0:
        return []
    if not lines:
        raise ValueError('presentation_needs_context')
    target = total * share / 100
    count = min(len(lines), 12, max(1, round(target / 2.4)))
    length = target / count
    chosen = _pick(lines, count)
    beats = []
    for slot, index in enumerate(chosen):
        segment_start = total * slot / count
        segment_end = total * (slot + 1) / count
        at, text = lines[index]
        start = max(segment_start, min(at - length * 0.2, segment_end - length))
        start = max(0.0, start)
        nxt = lines[index + 1][1] if index + 1 < len(lines) else None
        body = nxt if nxt and nxt != text else None
        kind = 'mini' if slot % 2 and body else 'window'
        x, y = _SPOTS[slot % len(_SPOTS)]
        beats.append(PresentationBeat(
            kind=kind, start=start, end=start + length, title=text, body=body, x=x, y=y,
        ))
    return beats

def _footage_seconds(edit):
    clips = edit.get('clips') if isinstance(edit, dict) else edit.clips
    total = 0.0
    for clip in clips:
        approved = clip.get('approved', True) if isinstance(clip, dict) else getattr(clip, 'approved', True)
        if not approved:
            continue
        start = clip.get('start') if isinstance(clip, dict) else clip.start
        end = clip.get('end') if isinstance(clip, dict) else clip.end
        total += max(0.0, float(end) - float(start))
    return total or 0.1

def presentation_prompt(edit, board=None):
    """One prompt. The slider percent is the request Hypit builds, not a frame window."""
    from .hypit_prompt import author_source

    return author_source(edit, 720, 1280, board)

def _step(value, default=100):
    try:
        number = int(default if value is None else value)
    except (TypeError, ValueError):
        number = default
    return max(0, min(100, number // 5 * 5))


def _intensity(value):
    """5–100 in steps of 5. A missing value keeps the accepted entrance."""
    return max(5, _step(value, 100))


def animation_levels(edit):
    """How much of the timeline carries graphics, and how strong that entrance is.

    Coverage is a share of the video length. Intensity never changes card size.
    """
    manual = edit if isinstance(edit, dict) else edit.model_dump()
    return {
        'coverage': _step(manual.get('card_motion'), 100),
        'intensity': _intensity(manual.get('animation_intensity')),
        'depth': _step(manual.get('animation_depth'), 100),
        'motion': _step(manual.get('animation_motion'), 100),
        'density': _step(manual.get('animation_density'), 100),
        'inserts': _step(manual.get('animation_inserts'), 100),
    }


def animation_window(edit):
    """Seconds of full-size graphics. 10% of a minute is 6 seconds."""
    levels = animation_levels(edit)
    length = _footage_seconds(edit)
    return {
        'length': length,
        'seconds': length * levels['coverage'] / 100,
        'coverage': levels['coverage'],
        'intensity': levels['intensity'],
    }


# The picture Hypit generates. Lumen only fills this from the words that were said.
MAIN_VISUAL_PROMPT = (
    "Визуализируй слова ведущего синхронно с речью. "
    "Пока звучит фраза, на переднем плане графика этой мысли, ведущий в кружке, исходный кадр резкий. "
    "Графика — собранная моушн-сцена из нескольких карточек и связей, не одна плашка по центру. "
    "Прибыль, рост и «больше» — стрелка вверх. Риск, падение и «меньше» — стрелка вниз. "
    "Названное число — крупная цифра. Шаги появляются по одному. Сравнение — две колонки. "
    "Срок — отметка на шкале. Не выдумывай факты и не меняй размер картинок."
)

_UP = ('利润', '盈利', '增长', '上涨', '提高', '上升', '增加', 'profit', 'growth', 'increase', 'rising', 'прибыл', 'рост')
_DOWN = ('风险', '下降', '降低', '下跌', '减少', '亏损', 'risk', 'drop', 'fall', 'decline', 'риск', 'паден')
_STEPS = ('第一', '首先', '然后', '接着', '步骤', 'step', 'first', 'then', 'сначала', 'затем')
_COMPARE = ('相比', '对比', '不同于', 'compared', 'unlike', 'versus', 'сравн')
_DEADLINE = ('截止', '期限', '天内', '个月内', 'deadline', 'срок', 'дедлайн')
_KIND_RU = {
    'up': 'стрелка вверх',
    'down': 'стрелка вниз',
    'figure': 'крупная цифра',
    'steps': 'шаг',
    'compare': 'сравнение',
    'deadline': 'срок',
    'phrase': 'фраза',
}


def _caption_text(caption):
    if not isinstance(caption, dict):
        caption = caption.model_dump() if hasattr(caption, 'model_dump') else {}
    for key in ('zh', 'original', 'ru', 'en'):
        text = ' '.join(str(caption.get(key) or '').split())
        if text and text != '口播':
            return text
    return ''


_FOCUS = (
    '法人代表', '董事权限', '股东结构', '注册资本', '外资比例', '出资节奏',
    '三名股东', '实缴', '认缴', '第一步', '第一关',
)


def _spoken_line(caption):
    if not isinstance(caption, dict):
        caption = caption.model_dump() if hasattr(caption, 'model_dump') else {}
    for key in ('zh', 'original', 'ru', 'en'):
        text = ' '.join(str(caption.get(key) or '').split())
        if text and text != '口播' and not text.isdigit():
            return text
    return ''


def _focus(text):
    for token in _FOCUS:
        if token in text:
            return token
    line = text
    for sep in ('，', ',', '。', '？', '?', '！', '!', '；', ';', '：', ':'):
        if sep in line:
            line = line.split(sep)[0].strip()
    named = re.search(r'(?:看的是|强调|是)([\u4e00-\u9fff]{2,6})', text)
    if named:
        return named.group(1)
    chars = re.findall(r'[\u4e00-\u9fff]', line)
    if chars:
        return ''.join(chars[:8])
    return line[:24].strip()


# Spoken terms already on the cards. Another language is the same word, not a new fact.
_TERMS = (
    ('法人代表', 'Legal representative', 'Законный представитель'),
    ('董事权限', 'Director authority', 'Полномочия директора'),
    ('股东结构', 'Shareholder structure', 'Состав акционеров'),
    ('注册资本', 'Registered capital', 'Уставный капитал'),
    ('外资比例', 'Foreign share', 'Доля иностранного капитала'),
    ('出资节奏', 'Capital schedule', 'График взносов'),
    ('三名股东', 'Three shareholders', 'Три акционера'),
    ('实缴', 'Paid-in capital', 'Оплаченный капитал'),
    ('认缴', 'Subscribed capital', 'Заявленный капитал'),
    ('第一步', 'First step', 'Первый шаг'),
    ('第一关', 'First step', 'Первый порог'),
)


def _effects_language(manual):
    """Card language. An explicit effects choice wins. Otherwise the host language is used."""
    if not isinstance(manual, dict):
        return ''
    language = manual.get('effects_language')
    if language in ('zh', 'ru', 'en'):
        return language
    host = manual.get('host_language')
    return host if host in ('zh', 'ru', 'en') else ''


def _term(token, language):
    if language not in ('en', 'ru'):
        return token
    for zh, en, ru in _TERMS:
        if token == zh:
            return en if language == 'en' else ru
    return token


def _terms_in(text, language):
    if language not in ('en', 'ru'):
        return []
    hits = []
    for zh, en, ru in _TERMS:
        at = text.find(zh)
        if at >= 0:
            hits.append((at, en if language == 'en' else ru))
    hits.sort()
    found = []
    for _, label in hits:
        if label not in found:
            found.append(label)
    return found


def _visual_title(caption):
    return _focus(_spoken_line(caption))


def _ru_card_line(blob, title, figure, left, right, labels):
    """The spoken idea in full words. A card keeps the phrase, not a chopped token."""
    if left and right:
        return f'{left} · {right}'
    if figure and title and ('不超过' in blob or '不超' in blob):
        return f'{title} не выше {figure}'
    if figure and title:
        return f'{title}: {figure}'
    if labels:
        return ' · '.join(labels)
    return title


def _compare_sides(text):
    """Two labels already spoken. A missing side adds nothing."""
    if '中国' not in text or '泰国' not in text:
        return '', ''
    right = text.split('中国', 1)[1]
    if '泰国' not in right:
        return '', ''
    left, right = right.split('泰国', 1)
    left, right = _focus(left), _focus(right)
    if len(left) < 2 or len(right) < 2 or left == right:
        return '', ''
    return left, right


def visual_kind(text):
    """One picture for a spoken phrase. Nothing is added that the words do not say."""
    blob = ' '.join(str(text or '').split())
    if not blob or blob == '口播':
        return ''
    folded = blob.lower()
    if re.search(r'\d+(?:\.\d+)?\s*[%％]', blob) or re.search(r'\d+(?:\.\d+)?\s*[万千亿]', blob):
        return 'figure'
    if _compare_sides(blob)[0]:
        return 'compare'
    up = any(needle.lower() in folded for needle in _UP)
    down = any(needle.lower() in folded for needle in _DOWN)
    if up and down:
        return 'compare'
    if down:
        return 'down'
    if up:
        return 'up'
    if any(token in blob for token in _FOCUS if token not in ('第一步', '第一关')):
        return 'phrase'
    if any(needle.lower() in folded for needle in _STEPS):
        return 'steps'
    if any(needle.lower() in folded for needle in _COMPARE):
        return 'compare'
    if any(needle.lower() in folded for needle in _DEADLINE) or '节奏' in blob or '时间' in blob:
        return 'deadline'
    return 'phrase'


def speech_visuals(edit):
    """Timed pictures of what the host says. A missing phrase adds no picture."""
    manual = edit if isinstance(edit, dict) else edit.model_dump()
    language = _effects_language(manual)
    beats = []
    seen = set()
    for caption in manual.get('captions') or []:
        if not isinstance(caption, dict):
            caption = caption.model_dump() if hasattr(caption, 'model_dump') else {}
        blob = _caption_text(caption)
        kind = visual_kind(blob)
        title = _visual_title(caption)
        if not kind or not title:
            continue
        try:
            start, end = float(caption.get('start') or 0), float(caption.get('end') or 0)
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        key = (kind, title, int(start))
        if key in seen:
            continue
        seen.add(key)
        figure = ''
        left, right = '', ''
        if kind == 'figure':
            found = re.search(r'\d+(?:\.\d+)?\s*[%％]|\d+(?:\.\d+)?\s*[万千亿]', blob)
            figure = re.sub(r'\s+', '', found.group(0)) if found else title
            if '外资' in blob:
                title = '外资比例'
        elif kind == 'compare':
            left, right = _compare_sides(blob)
        elif kind == 'steps':
            title = '第一关' if '第一关' in blob else ('第一步' if '第一步' in blob else title)
        line = blob[:80]
        if language in ('en', 'ru'):
            title = _term(title, language)
            left, right = _term(left, language), _term(right, language)
            labels = _terms_in(blob, language)
            english = ' '.join(str(caption.get('en') or '').split())
            if language == 'en' and english:
                line = english[:140]
            elif language == 'ru':
                line = _ru_card_line(blob, title, figure, left, right, labels)
            elif labels:
                line = ' · '.join(labels)[:80]
            else:
                line = title
        beats.append({
            'kind': kind,
            'title': title,
            'figure': figure,
            'left': left,
            'right': right,
            'line': line,
            'start': round(start, 3),
            'end': round(end, 3),
        })
    return beats


def _insert_line(percent, edit=None):
    """The inserts slider, in the same prompt as the other percents."""
    from .thematic_broll import hold, quota, theme_phrase, windows

    count = quota(percent)
    if not count:
        return f"Вставки {percent}%: дополнительных роликов нет. "
    manual = edit if isinstance(edit, dict) else edit.model_dump() if hasattr(edit, 'model_dump') else {}
    theme = theme_phrase(manual)
    chosen = windows(manual, count, hold(percent)) if theme else []
    shown = len(chosen) if chosen else count
    where = f" по теме ролика: {theme}." if theme else " внутри графики."
    guard = " Чужую страну и чужую организацию не показывай." if theme else ""
    return (
        f"Вставки {percent}%: {shown} коротких роликов по {hold(percent):g} с{where}{guard} Речь не режется. "
    )


def animation_brief(edit):
    """The prompt saved with the edit and sent when Hypit generates the video.

    Presence is how much of each minute the host spends in the circle while the
    words become graphics. Depth is how sharply those graphics arrive.
    """
    levels = animation_levels(edit)
    presence = levels['coverage']
    seconds = presence * 60 // 100
    kept = speech_visuals(edit)
    density = levels['density']
    if 0 < density < 100 and len(kept) > 1:
        count = max(1, int(round(len(kept) * density / 100)))
        if count < len(kept):
            if count == 1:
                kept = [kept[len(kept) // 2]]
            else:
                kept = [kept[round(i * (len(kept) - 1) / (count - 1))] for i in range(count)]
    added = '; '.join(
        f"{int(beat['start'])}с {_KIND_RU.get(beat['kind'], 'фраза')}: {beat['figure'] or beat['title']}"
        for beat in kept[:12]
    )
    brief = (
        f"Будет добавлена анимация на {presence}% длины ролика — это {seconds} секунд на каждую минуту. "
        f"Ведущий в кружке, передний план — графика сказанного. "
        f"Интенсивность {levels['depth']}%. Движение {levels['motion']}%: карточки выезжают на эту долю. "
        f"{_insert_line(levels['inserts'], edit)}"
        f"Плотность {levels['density']}% слоёв. "
        f"{MAIN_VISUAL_PROMPT}"
    )
    if added:
        brief = f"{brief} Добавится: {added}."
    return brief[:1100]


def plan(edit, board=None):
    return edit.model_copy(update={
        'presentation': build(edit),
        'presentation_prompt': presentation_prompt(edit, board),
        'animation_prompt': animation_brief(edit),
    })
