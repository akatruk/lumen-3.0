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

def plan(edit):
    return edit.model_copy(update={'presentation': build(edit)})

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
