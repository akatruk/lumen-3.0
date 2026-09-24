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
        if clip.text:
            title_start,title_end=row['start'],row['end']
            if clip.effect_end<0.999:
                title_start=row['start']+max(0,min(clip.effect_at,0.98))*length
                title_end=row['start']+max(clip.effect_at,clip.effect_end)*length
                if title_end<=title_start: title_start,title_end=row['start'],row['end']
            titles.append({'decision_id':clip.id,'start':round(title_start,6),'end':round(title_end,6),'text':clip.text})
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

def playback(clip, length, room=None):
    speed=max(0.5,min(2,_num(clip,'speed',1)))
    end=clip.get('speed_end')
    end=speed if end is None else max(0.5,min(2,_num(clip,'speed_end',speed)))
    if abs(end-speed)<=0.04: end=speed
    average=(speed+end)/2
    if average>1 and room is not None and average>room:
        speed=min(speed,max(1,room)); end=speed; average=speed
    return speed, end, average

def _ramp(speed, end, length):
    slope=(end-speed)/(2*max(0.08,length))
    return f"setpts=(-{speed:.4f}+sqrt({speed:.4f}*{speed:.4f}+4*{slope:.6f}*PTS*TB))/(2*{slope:.6f})/TB,"

def motion_filter(clip,width,height,length):
    z0=clip['zoom'];z1=clip.get('zoom_end') if clip.get('zoom_end') is not None else z0
    x0=clip['x'];x1=clip.get('x_end') if clip.get('x_end') is not None else x0
    y0=clip['y'];y1=clip.get('y_end') if clip.get('y_end') is not None else y0
    rx=max(4, min(64, int(clip.get('shake_rx') or 16))) if clip.get('stabilize') else 0
    pre=f'deshake=rx={rx}:ry={rx}:edge=0,' if rx else ''
    if (z0,x0,y0)==(z1,x1,y1):
        base=f"crop=trunc(iw/{z0}/2)*2:trunc(ih/{z0}/2)*2:(iw-ow)*{x0}:(ih-oh)*{y0},"
    else:
        n=max(1,round(min(length,clip.get('motion_seconds') or length)*30)-1);progress=f'min(on/{n},1)'
        # zoompan resamples with bilinear. A 2x lanczos source keeps a punch-in from softening a small frame.
        base=f"scale=iw*2:ih*2:flags=lanczos,fps=30,zoompan=z='{z0}+({z1}-{z0})*{progress}':x='(iw-iw/zoom)*({x0}+({x1}-{x0})*{progress})':y='(ih-ih/zoom)*({y0}+({y1}-{y0})*{progress})':d=1:s={width}x{height}:fps=30,"
    speed,end,_average=playback(clip,length)
    if abs(end-speed)>0.04: base+=_ramp(speed,end,length)
    elif abs(speed-1)>0.04: base+=f'setpts=PTS/{speed:.4f},'
    grade=clip.get('grade') or None
    short=min(width,height)<720
    if grade:
        contrast=_num(grade,'contrast',1)
        saturation=_num(grade,'saturation',1)
        if short:
            # Match color on a small frame. A full contrast or saturation lift looks softer than the source.
            contrast=1+(contrast-1)*0.25
            saturation=1+(saturation-1)*0.25
        base+=f"eq=contrast={contrast:.4f}:brightness={_num(grade,'brightness',0):.4f}:saturation={saturation:.4f}:gamma={_num(grade,'gamma',1):.4f},"
        base+=f"colorbalance=rs={_num(grade,'rs',0):.4f}:gs={_num(grade,'gs',0):.4f}:bs={_num(grade,'bs',0):.4f},"
    elif clip.get('enhance') and not short:
        base+='eq=contrast=1.04:brightness=0.02:saturation=1.06:gamma=1.02,'
    at=float(clip.get('effect_at') or 0)
    opened=max(0.0, min(at, 0.98)) * float(length) if at >= 0.2 else 0.0
    gate=f":enable='gte(t\\,{opened:.3f})'" if opened >= 0.2 else ''
    if _num(clip,'blur',0)>=0.4: base+=f"gblur=sigma={min(12,_num(clip,'blur',0)):.2f}{gate},"
    if clip.get('glow'):
        amount=_num(clip,'glow_amount',0)
        if amount<0.2: amount=0.8
        base+=f"unsharp=7:7:{min(1.5,amount):.2f}:7:7:0{gate},"
    if clip.get('shadow'):
        angle=_num(clip,'shade',0)
        if angle<0.2: angle=3.1416/5
        base+=f"vignette=angle={min(1.35,angle):.3f}{gate},"
    if abs(_num(clip,'exposure',0))>0.02: base+=f"exposure={_num(clip,'exposure',0):.3f},"
    return pre+base
