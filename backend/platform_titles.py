"""Reviewed platform hook and CTA overlays, independent from burned-in captions."""
from typing import Literal
from pydantic import Field
from .schemas import Strict

class Presentation(Strict):
    caption_mode:Literal['inherit','custom','off']='inherit'
    caption_size:Literal['small','medium','large']='medium'
    caption_position:Literal['top','bottom']='bottom'
    caption_color:Literal['white','yellow']='white'
    hook_seconds:float=Field(default=3,ge=0,le=8)
    cta_seconds:float=Field(default=0,ge=0,le=8)
    title_style:Literal['clean','bold','panel']='clean'
    title_position:Literal['top','center']='top'

def write(path,variant,language,w,h,duration):
    from .media import subtitle_text,ass_time
    size=round(min(w*.055,h*.055))
    size=max(28,min(72,size))
    bold=-1 if variant.title_style!='clean' else 0
    border=3 if variant.title_style=='panel' else 1
    align=8 if variant.title_position=='top' else 5
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Noto Sans CJK SC,{size},&H00FFFFFF,&H00121212,&H50121212,{bold},{border},3,1,{align},{round(w*.09)},{round(w*.12)},{round(h*.125)}
[Events]
Format: Layer, Start, End, Style, Text
'''
    hook=min(variant.hook_seconds,duration)
    # On short edits give the hook priority; never stack CTA on top of it.
    cta_start=max(hook,duration-variant.cta_seconds)
    rows=[]
    if hook>0:rows.append(f'Dialogue: 0,0:00:00.00,{ass_time(hook)},Default,{subtitle_text(variant.title,language)}\n')
    if variant.cta_seconds>0 and duration-cta_start>=.5:
        rows.append(f'Dialogue: 0,{ass_time(cta_start)},{ass_time(duration)},Default,{subtitle_text(variant.cta,language)}\n')
    path.write_text(header+''.join(rows),encoding='utf-8')
