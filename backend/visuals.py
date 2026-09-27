"""Bilingual, editor-supplied data cards with bounded text and clip-local timing."""
import re
from typing import Literal
from pydantic import Field,model_validator
from .schemas import Strict,Span
class CardText(Strict):
    en:str=Field(min_length=1,max_length=48)
    zh:str=Field(min_length=1,max_length=48)
class DataItem(Strict):
    label:CardText
    value:float=Field(ge=0,le=1e12,allow_inf_nan=False)

class Milestone(Strict):
    when:CardText
    label:CardText

class MapPoint(Strict):
    label:CardText
    latitude:float=Field(ge=-90,le=90,allow_inf_nan=False)
    longitude:float=Field(ge=-180,le=180,allow_inf_nan=False)

class VisualCard(Span):
    kind:Literal['number','comparison','bar_chart','ranking','timeline','map']='number'
    locations:list[MapPoint]=Field(default_factory=list,max_length=5)
    animation:Literal['none','grow']='none'
    animation_seconds:float=Field(default=.6,ge=.2,le=2,allow_inf_nan=False)
    milestones:list[Milestone]=Field(default_factory=list,max_length=5)
    items:list[DataItem]=Field(default_factory=list,max_length=5)
    title:CardText
    primary:CardText
    secondary:CardText|None=None
    source:CardText

    @model_validator(mode='after')
    def validate_items(self):
        if self.kind=='map' and (not self.locations or self.items or self.milestones):raise ValueError('map_requires_locations')
        if self.kind!='map' and self.locations:raise ValueError('locations_require_map')
        if self.animation=='grow' and (self.kind not in ('bar_chart','ranking') or self.animation_seconds>self.end-self.start-.15):raise ValueError('invalid_chart_animation')
        if self.kind in ('bar_chart','ranking') and len(self.items)<2:raise ValueError('at_least_two_data_items')
        if self.kind=='timeline' and (len(self.milestones)<2 or self.items):raise ValueError('timeline_requires_milestones')
        if self.kind!='timeline' and self.milestones:raise ValueError('milestones_require_timeline')
        if self.kind in ('number','comparison') and self.items:raise ValueError('items_require_chart')
        if self.kind=='comparison' and self.secondary is None:raise ValueError('comparison_requires_two_values')
        return self

def _pair(value):
    if not isinstance(value,(tuple,list)) or len(value)<2 or value[0] is None or value[1] is None:
        return None
    try:
        a,b=float(value[0]),float(value[1])
    except (TypeError,ValueError):
        return None
    if a!=a or b!=b or a<0 or b<0:
        return None
    return a,b

def _card_shift(place, size=None):
    """Move and size the owned card from measured fractions. A missing measurement keeps the fixed panel."""
    sized=_pair(size)
    if sized and (sized[0] <= 0 or sized[1] <= 0):
        sized=None
    point=_pair(place)
    if sized:
        panel_w=min(0.96,max(0.08,sized[0]))
        panel_h=min(0.96,max(0.08,sized[1]))
    elif point is None:
        return None
    else:
        panel_w=0.58 if abs(point[0]-0.5)>=0.12 else 0.90
        panel_h=0.41
    if point is None:
        point=(0.5,0.485)
    cx,cy=point
    cx=min(max(cx,panel_w/2+0.02),1-(panel_w/2+0.02))
    cy=min(max(cy,panel_h/2+0.02),1-(panel_h/2+0.02))
    return {'cx':cx,'cy':cy,'left':cx-panel_w/2,'right':cx+panel_w/2,'top':cy-panel_h/2,'bottom':cy+panel_h/2,'dx':cx-0.5,'dy':cy-0.485,'panel_h':panel_h,'sized':sized is not None}

def write_card(path,card,language,w,h,place=None,size=None,face=None,heavy=None):
    from .media import ass_face, ass_time
    font_name, bold = ass_face(face, heavy)
    shift=_card_shift(place,size)
    scale=(shift['panel_h']/0.41) if shift and shift.get('sized') else 1.0
    def clean(text):return re.sub(r'[{}\\\r\n]',' ',text).strip()
    def value(key):return clean(card[key][language])
    # Font shrinks to keep even 48 CJK characters inside the safe horizontal area.
    def event(text,y,size,color='&H00FFFFFF',layer=1):
        size=min(size*scale,w*.82/max(1,len(text)))
        if shift is None:
            x,y_frac=w/2,y
        elif shift.get('sized'):
            x,y_frac=w*shift['cx'],shift['cy']+(y-0.485)*scale
        else:
            x,y_frac=w*shift['cx'],y+shift['dy']
        tags=r'{\an5\pos('+f'{x:.1f},{h*y_frac:.1f}'+r')\fs'+f'{size:.1f}'+r'\c'+color+r'\fad(150,150)}'
        return f'Dialogue: {layer},{ass_time(card["start"])},{ass_time(card["end"])},Default,,0,0,0,,{tags}{text}\n'
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},36,&H00FFFFFF,&H00FFFFFF,&H00101614,&H00101614,{bold},0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    # A vector panel avoids shell filters containing user-supplied text.
    if shift is None:
        panel=r'{\an7\pos(0,0)\p1\c&H00161410\alpha&H18\fad(150,150)}'+f'm {w*.05:.0f} {h*.28:.0f} l {w*.95:.0f} {h*.28:.0f} {w*.95:.0f} {h*.69:.0f} {w*.05:.0f} {h*.69:.0f}'
    else:
        left,right,top,bottom=w*shift['left'],w*shift['right'],h*shift['top'],h*shift['bottom']
        panel=r'{\an7\pos(0,0)\p1\c&H00161410\alpha&H18\fad(150,150)}'+f'm {left:.0f} {top:.0f} l {right:.0f} {top:.0f} {right:.0f} {bottom:.0f} {left:.0f} {bottom:.0f}'
    rows=f'Dialogue: 0,{ass_time(card["start"])},{ass_time(card["end"])},Default,,0,0,0,,{panel}\n'
    rows+=event(value('title'),.34,h*.035)
    dx=0 if shift is None else shift['dx']
    dy=0 if shift is None else shift['dy']
    if card['kind']=='map':
        from .map_cards import map_rows
        rows+=map_rows(card,language,w,h,ass_time,clean,dx,dy)
    elif card['kind']=='timeline':
        rows+=milestone_rows(card,language,w,h,event,ass_time,clean,dx,dy)
    elif card['kind'] in ('bar_chart','ranking'):
        rows+=data_rows(card,language,w,h,event,ass_time,clean,dx,dy)
    else:rows+=event(value('primary'),.44 if card['kind']=='comparison' else .48,h*.08,'&H009EEF D1'.replace(' ',''))
    if card['kind']=='comparison':rows+=event(value('secondary'),.54,h*.065)
    rows+=event(value('source'),.64,h*.023)
    path.write_text(header+rows,encoding='utf-8')


def data_rows(card,language,w,h,event,ass_time,clean,dx=0.0,dy=0.0):
    items=card['items']
    if card['kind']=='ranking':items=sorted(items,key=lambda item:item['value'],reverse=True)
    maximum=max(item['value'] for item in items) or 1
    rows=event(clean(card['primary'][language]),.385,h*.021)
    step=.205/len(items)
    for index,item in enumerate(items):
        y=.42+index*step
        prefix=f'{index+1}. ' if card['kind']=='ranking' else ''
        text=prefix+clean(item['label'][language])+f"  {item['value']:g}"
        rows+=event(text,y,h*min(.024,step*.5))
        left=w*.13+(w*dx if dx else 0);right=left+w*.74*item['value']/maximum;top=h*(y+step*.22)+(h*dy if dy else 0);bottom=top+h*.008
        # Shared zero baseline and maximum, with proportional bar length.
        tags=r'{\an7\pos(0,0)\p1\c&H009EEFD1\fad(150,150)}'
        if card.get('animation')=='grow':
            # Rectangular ASS clips interpolate in output coordinates. Values and labels stay fixed.
            import math
            x0=math.floor(left);x1=math.ceil(right);y0=math.floor(top)-1;y1=math.ceil(bottom)+1
            ms=round(card['animation_seconds']*1000)
            tags=tags[:-1]+rf'\clip({x0},{y0},{x0},{y1})\t(0,{ms},\clip({x0},{y0},{x1},{y1}))'+'}'
        drawing=f'm {left:.2f} {top:.2f} l {right:.2f} {top:.2f} {right:.2f} {bottom:.2f} {left:.2f} {bottom:.2f}'
        if item['value']>0:rows+=f'Dialogue: 1,{ass_time(card["start"])},{ass_time(card["end"])},Default,,0,0,0,,{tags}{drawing}\n'
    return rows


def milestone_rows(card,language,w,h,event,ass_time,clean,dx=0.0,dy=0.0):
    # Equal spacing preserves editorial order; it does not imply elapsed duration.
    milestones=card['milestones'];step=.205/len(milestones)
    rows=event(clean(card['primary'][language]),.385,h*.021)
    x=w*.11+(w*dx if dx else 0);top=h*.42+(h*dy if dy else 0);bottom=h*(.42+(len(milestones)-1)*step)+(h*dy if dy else 0)
    tags=r'{\an7\pos(0,0)\p1\c&H009EEFD1\fad(150,150)}'
    line=f'm {x:.2f} {top:.2f} l {x+max(4,w*.0125):.2f} {top:.2f} {x+max(4,w*.0125):.2f} {bottom:.2f} {x:.2f} {bottom:.2f}'
    rows+=f'Dialogue: 1,{ass_time(card["start"])},{ass_time(card["end"])},Default,,0,0,0,,{tags}{line}\n'
    for i,m in enumerate(milestones):
        y=.42+i*step
        text=clean(m['when'][language])+' — '+clean(m['label'][language])
        rows+=event(text,y,h*min(.022,step*.48))
    return rows
