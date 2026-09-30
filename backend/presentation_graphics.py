"""Presentation graphics sized as a share of the finished video.

The scan reads speech and scene text already on the cut. It does not invent
facts. Each beat is stored in Russian, English and Chinese. The picture uses
the selected voiceover language when there is one, otherwise the project language.
"""
import re
from pathlib import Path
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
    """The card-animation percent is the SVML Hypit builds. Words stay on the edit."""
    from .hypit_prompt import author_source, treatment_line

    manual = edit if isinstance(edit, dict) else edit.model_dump()
    share = manual.get('card_motion', 100)
    try:
        share = int(0 if share is None else share)
    except (TypeError, ValueError):
        share = 100
    return author_source(share, _footage_seconds(edit), 720, 1280, treatment_line(manual), board)

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
    return ' '.join(str(caption.get(key) or '') for key in ('zh', 'original', 'en', 'ru'))


def _visual_title(caption):
    if not isinstance(caption, dict):
        caption = caption.model_dump() if hasattr(caption, 'model_dump') else {}
    for key in ('zh', 'original', 'ru', 'en'):
        text = ' '.join(str(caption.get(key) or '').split())
        if text and text != '口播' and not text.isdigit():
            for sep in ('，', ',', '。', '？', '?', '！', '!', '；', ';'):
                if sep in text:
                    text = text.split(sep)[0].strip()
            text = text.strip(' ，,。.')
            if len(text) > 18:
                text = text[:18].rsplit(' ', 1)[0].strip() or text[:18]
            return text
    return ''


def visual_kind(text):
    """One picture for a spoken phrase. Nothing is added that the words do not say."""
    blob = ' '.join(str(text or '').split())
    if not blob or blob == '口播':
        return ''
    folded = blob.lower()
    if re.search(r'\d+(?:\.\d+)?\s*[%％]', blob) or re.search(r'\d+(?:\.\d+)?\s*[万千亿]', blob):
        return 'figure'
    up = any(needle.lower() in folded for needle in _UP)
    down = any(needle.lower() in folded for needle in _DOWN)
    if up and down:
        return 'compare'
    if down:
        return 'down'
    if up:
        return 'up'
    if any(needle.lower() in folded for needle in _STEPS):
        return 'steps'
    if any(needle.lower() in folded for needle in _COMPARE):
        return 'compare'
    if any(needle.lower() in folded for needle in _DEADLINE):
        return 'deadline'
    return 'phrase'


def speech_visuals(edit):
    """Timed pictures of what the host says. A missing phrase adds no picture."""
    manual = edit if isinstance(edit, dict) else edit.model_dump()
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
        if kind == 'figure':
            found = re.search(r'\d+(?:\.\d+)?\s*[%％]|\d+(?:\.\d+)?\s*[万千亿]', blob)
            figure = re.sub(r'\s+', '', found.group(0)) if found else title
        beats.append({
            'kind': kind,
            'title': title,
            'figure': figure,
            'start': round(start, 3),
            'end': round(end, 3),
        })
    return beats


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
        f"Интенсивность {levels['depth']}%. Движение {levels['motion']}%. Плотность {levels['density']}% слоёв. "
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

def _fit(text, size, width):
    per = 0.95 if re.search(r'[\u4e00-\u9fff]', text) else 0.55
    return min(size, max(11, width * 0.86 / max(1, len(text)) / per))

def _words(node, language):
    if not isinstance(node, dict):
        return ''
    order = {'zh': ('zh', 'en', 'ru'), 'ru': ('ru', 'en', 'zh')}.get(language, ('en', 'zh', 'ru'))
    for key in order:
        text = _clean(node.get(key) or '', 48)
        if text:
            return text
    return ''

def _motion(cx, cy, enter, mid, leave, span, yaw):
    return (
        rf'\org({cx:.1f},{cy:.1f})\frx6\fry{yaw}\fscx38\fscy38'
        rf'\t(0,{enter},\frx0\fry0\fscx100\fscy100)'
        rf'\t({enter},{mid},\fry-8\frx4)'
        rf'\t({mid},{leave},\fry6\frx-3)'
        rf'\t({leave},{span},\fry{yaw // 2}\fscx72\fscy72)'
        r'\fad(70,160)'
    )

def write_presentation(path, beats, language, w, h):
    from .media import ass_time
    header = f'''[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,36,&H00FFFFFF,&H00FFFFFF,&H00101614,&H00101614,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Ru,Noto Sans,36,&H00FFFFFF,&H00FFFFFF,&H00101614,&H00101614,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    style = 'Ru' if language == 'ru' else 'Default'
    rows = []
    for index, beat in enumerate(beats):
        title = _words(beat.get('title') if isinstance(beat, dict) else beat.title.model_dump(), language)
        body_node = beat.get('body') if isinstance(beat, dict) else (beat.body.model_dump() if beat.body else None)
        body = _words(body_node, language) if body_node else ''
        if not title:
            continue
        kind = beat['kind'] if isinstance(beat, dict) else beat.kind
        start = beat['start'] if isinstance(beat, dict) else beat.start
        end = beat['end'] if isinstance(beat, dict) else beat.end
        x = beat['x'] if isinstance(beat, dict) else beat.x
        y = beat['y'] if isinstance(beat, dict) else beat.y
        span_ms = max(120, int(round((end - start) * 1000)))
        enter = min(380, max(80, span_ms // 3))
        leave = max(enter + 40, span_ms - min(220, max(40, span_ms // 5)))
        mid = min(leave - 20, enter + max(40, (leave - enter) // 2))
        if mid <= enter:
            mid = enter + 1
        if leave <= mid:
            leave = mid + 1
        if span_ms <= leave:
            span_ms = leave + 1
        cx, cy = w * x, h * y
        wide = kind == 'mini'
        panel_w = w * (0.46 if wide else 0.34)
        panel_h = h * (0.30 if wide else 0.18)
        left, top = cx - panel_w / 2, cy - panel_h / 2
        right, bottom = left + panel_w, top + panel_h
        yaw = 34 if index % 2 == 0 else -30
        motion = _motion(cx, cy, enter, mid, leave, span_ms, yaw)
        when = f'{ass_time(start)},{ass_time(end)}'
        plate = (
            r'{\an7\pos(0,0)\p1\c&H00181C16\alpha&H28' + motion + '}'
            + f'm {left:.1f} {top:.1f} l {right:.1f} {top:.1f} {right:.1f} {bottom:.1f} {left:.1f} {bottom:.1f}'
        )
        shade_left, shade_top = left + w * 0.012, top + h * 0.012
        shadow = (
            r'{\an7\pos(0,0)\p1\c&H00000000\alpha&H70' + motion + '}'
            + f'm {shade_left:.1f} {shade_top:.1f} l {shade_left + panel_w:.1f} {shade_top:.1f} {shade_left + panel_w:.1f} {shade_top + panel_h:.1f} {shade_left:.1f} {shade_top + panel_h:.1f}'
        )
        accent = max(4.0, panel_w * 0.02)
        edge = (
            r'{\an7\pos(0,0)\p1\c&H00D1EF9E' + motion + '}'
            + f'm {left:.1f} {top:.1f} l {left + accent:.1f} {top:.1f} {left + accent:.1f} {bottom:.1f} {left:.1f} {bottom:.1f}'
        )
        rows.append(f'Dialogue: 0,{when},{style},,0,0,0,,{shadow}\n')
        rows.append(f'Dialogue: 1,{when},{style},,0,0,0,,{plate}\n')
        rows.append(f'Dialogue: 2,{when},{style},,0,0,0,,{edge}\n')
        title_size = _fit(title, h * (0.034 if wide else 0.04), panel_w * 0.82)
        title_y = cy - (panel_h * 0.18 if body else 0)
        title_tags = r'{\an5\pos(' + f'{cx:.1f},{title_y:.1f}' + r')\fs' + f'{title_size:.1f}' + r'\c&H00FFFFFF' + motion + '}'
        rows.append(f'Dialogue: 3,{when},{style},,0,0,0,,{title_tags}{title}\n')
        if kind == 'mini' and body:
            body_size = _fit(body, h * 0.026, panel_w * 0.82)
            body_y = cy + panel_h * 0.16
            body_tags = r'{\an5\pos(' + f'{cx:.1f},{body_y:.1f}' + r')\fs' + f'{body_size:.1f}' + r'\c&H00D1EF9E' + motion + '}'
            rows.append(f'Dialogue: 4,{when},{style},,0,0,0,,{body_tags}{body}\n')
    path.write_text(header + ''.join(rows), encoding='utf-8')

def burn(video, folder, beats, language, w, h):
    if not beats:
        return video
    folder = Path(folder)
    script = folder / 'presentation.ass'
    write_presentation(script, beats, language, w, h)
    out = folder / 'presentation.mp4'
    escaped = str(script.resolve()).replace('\\', '/').replace(':', '\\:').replace("'", r"'\''")
    from .media import ffmpeg
    ffmpeg('-i', video, '-vf', f"ass='{escaped}'", '-map', '0:v:0', '-map', '0:a:0?',
           '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'copy', out, timeout=900)
    return out
