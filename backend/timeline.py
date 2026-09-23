"""Executable timeline derived from validated, approved source decisions."""
def compile_timeline(edit):
    from .sound_effects import DURATIONS
    cursor=0.0;shots=[];titles=[];inserts=[];cutaways=[];effects=[]
    for clip in edit.clips:
        if not clip.approved:continue
        length=clip.end-clip.start
        row={'id':clip.id,'start':round(cursor,6),'end':round(cursor+length,6),'source_start':clip.start,'source_end':clip.end,
             'shot_type':clip.shot_type,'locked':clip.locked,'motion':{'from':[clip.zoom,clip.x,clip.y],'to':[clip.zoom_end if clip.zoom_end is not None else clip.zoom,clip.x_end if clip.x_end is not None else clip.x,clip.y_end if clip.y_end is not None else clip.y]},'transition':clip.transition,'audio_fade_ms':clip.audio_fade_ms}
        row['motion']['duration']=min(length,clip.motion_seconds or length)
        shots.append(row)
        if clip.text:titles.append({'decision_id':clip.id,'start':row['start'],'end':row['end'],'text':clip.text})
        if clip.card:inserts.append(clip.card.model_dump()|{'decision_id':clip.id,'start':round(cursor+clip.card.start,6),'end':round(cursor+clip.card.end,6)})
        if clip.cutaway:cutaways.append({'decision_id':clip.id,'start':round(cursor+clip.cutaway.start,6),'end':round(cursor+clip.cutaway.end,6),'source_start':clip.cutaway.source_start,'source_end':clip.cutaway.source_start+clip.cutaway.end-clip.cutaway.start,'audio':'base_source','locked':clip.locked})
        if clip.external_broll:
            c=clip.external_broll
            cutaways.append({'decision_id':clip.id,'start':round(cursor+c.start,6),'end':round(cursor+c.end,6),'source_start':c.source_start,'source_end':c.source_start+c.end-c.start,'asset_id':c.asset_id,'audio':'base_source','locked':clip.locked})
        effects.extend(e.model_dump()|{'decision_id':clip.id,'at':round(cursor+e.at,6),'end':round(cursor+e.at+DURATIONS[e.kind],6),'duration':DURATIONS[e.kind]} for e in clip.sound_effects)
        cursor+=length
    captions=[]
    if edit.subtitles:
        for shot in shots:
            for c in edit.captions:
                a=max(c.start,shot['source_start']);b=min(c.end,shot['source_end'])
                if b>a:captions.append({'start':round(shot['start']+a-shot['source_start'],6),'end':round(shot['start']+b-shot['source_start'],6),'en':c.en or c.original,'zh':c.zh or c.original,'emphasis_en':c.emphasis_en,'emphasis_zh':c.emphasis_zh})
    return {'version':2,'duration':round(cursor,6),'tracks':{'music':[edit.music.model_dump()|{'start':0,'end':round(cursor,6),'loop':True}] if edit.music else [],'sound_effects':effects,'video':shots,'titles':titles,'inserts':inserts,'cutaways':cutaways,'captions':sorted(captions,key=lambda c:c['start']),'audio':[{'start':0,'end':round(cursor,6),'source':'original','normalize':edit.normalize}] if shots else []}}

def _num(clip, key, default):
    try: return float(clip.get(key) if clip.get(key) is not None else default)
    except (TypeError, ValueError): return default

def motion_filter(clip,width,height,length):
    z0=clip['zoom'];z1=clip.get('zoom_end') if clip.get('zoom_end') is not None else z0
    x0=clip['x'];x1=clip.get('x_end') if clip.get('x_end') is not None else x0
    y0=clip['y'];y1=clip.get('y_end') if clip.get('y_end') is not None else y0
    pre='deshake=rx=16:ry=16:edge=0,' if clip.get('stabilize') else ''
    if (z0,x0,y0)==(z1,x1,y1):
        base=f"crop=trunc(iw/{z0}/2)*2:trunc(ih/{z0}/2)*2:(iw-ow)*{x0}:(ih-oh)*{y0},"
    else:
        n=max(1,round(min(length,clip.get('motion_seconds') or length)*30)-1);progress=f'min(on/{n},1)'
        base=f"fps=30,zoompan=z='{z0}+({z1}-{z0})*{progress}':x='(iw-iw/zoom)*({x0}+({x1}-{x0})*{progress})':y='(ih-ih/zoom)*({y0}+({y1}-{y0})*{progress})':d=1:s={width}x{height}:fps=30,"
    speed=_num(clip,'speed',1)
    if abs(speed-1)>0.04: base+=f'setpts=PTS/{max(0.5,min(2,speed)):.4f},'
    grade=clip.get('grade') or None
    if grade:
        base+=f"eq=contrast={_num(grade,'contrast',1):.4f}:brightness={_num(grade,'brightness',0):.4f}:saturation={_num(grade,'saturation',1):.4f}:gamma={_num(grade,'gamma',1):.4f},"
        base+=f"colorbalance=rs={_num(grade,'rs',0):.4f}:gs={_num(grade,'gs',0):.4f}:bs={_num(grade,'bs',0):.4f},"
    elif clip.get('enhance'):
        # A small lift only. It does not copy a reference grade.
        base+='eq=contrast=1.04:brightness=0.02:saturation=1.06:gamma=1.02,'
    if _num(clip,'blur',0)>=0.4: base+=f"gblur=sigma={min(12,_num(clip,'blur',0)):.2f},"
    if clip.get('glow'): base+='unsharp=7:7:0.8:7:7:0,'
    if clip.get('shadow'): base+='vignette=angle=PI/5,'
    if abs(_num(clip,'exposure',0))>0.02: base+=f"exposure={_num(clip,'exposure',0):.3f},"
    return pre+base
