import json
import math
import re
import subprocess
from pathlib import Path

def run(args, timeout=600):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        # Keep raw decoder stderr out of user responses.
        raise RuntimeError('media_processing_failed')
    return p.stdout, p.stderr

def ffmpeg(*args, timeout=600):
    return run(['ffmpeg','-hide_banner','-nostdin','-y','-threads','2',*map(str,args)],timeout)

def probe(path):
    out,_ = run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_format','-show_streams','-of','json',str(path)],30)
    data=json.loads(out)
    if not set(data.get('format',{}).get('format_name','').split(',')) & {'mov','mp4','matroska','webm'}:
        raise ValueError('not_a_video')
    video=next((s for s in data['streams'] if s['codec_type']=='video'),None)
    if not video: raise ValueError('not_a_video')
    duration=float(data['format'].get('duration') or video.get('duration') or 0)
    if not math.isfinite(duration) or duration<=0: raise ValueError('invalid_duration')
    if min(video['width'],video['height'])<16 or video['width']*video['height'] > 4096*4096: raise ValueError('resolution_too_large')
    return {'duration':duration,'width':video['width'],'height':video['height'],
            'has_audio':any(s['codec_type']=='audio' for s in data['streams']),
            'size':int(data['format']['size']),'codec':video['codec_name']}

def prepare(path, folder):
    duration=probe(path)['duration']
    maxrate_kbps=max(64,min(600,int(12*1024*8/max(1,duration))-64))
    # Analysis proxy keeps the entire timeline and audio; original used for export.
    ffmpeg('-protocol_whitelist','file,pipe','-i',path,'-map','0:v:0','-map','0:a:0?',
           '-vf',"scale=960:960:force_original_aspect_ratio=decrease:force_divisible_by=2",'-r','12',
           '-c:v','libx264','-preset','veryfast','-crf','29','-maxrate',f'{maxrate_kbps}k','-bufsize',f'{maxrate_kbps*2}k',
           '-c:a','aac','-b:a','64k','-ac','1','-movflags','+faststart',folder/'analysis.mp4')
    if (folder/'analysis.mp4').stat().st_size>16*1024*1024: raise ValueError('analysis_proxy_too_large')
    ffmpeg('-i',path,'-frames:v','1','-vf','scale=640:-2',folder/'poster.jpg')

def silence_ranges(path, duration):
    _,err=ffmpeg('-i',path,'-af','silencedetect=noise=-38dB:d=0.7','-vn','-f','null','-',timeout=180)
    ranges=[]; start=None
    for line in err.splitlines():
        a=re.search(r'silence_start: ([\d.]+)',line)
        b=re.search(r'silence_end: ([\d.]+)',line)
        if a: start=float(a.group(1))
        if b and start is not None:
            ranges.append({'start':start,'end':min(float(b.group(1)),duration)}); start=None
    if start is not None: ranges.append({'start':start,'end':duration})
    return ranges

def validate_analysis(analysis, duration):
    for item in [*analysis.scenes,*analysis.transcript,*analysis.recommendations]:
        if item.end>duration+0.25 or item.start>=duration: raise ValueError('analysis_timestamps_invalid')
        item.end=min(item.end,duration)
    ids=[r.id for r in analysis.recommendations]
    if len(ids)!=len(set(ids)): raise ValueError('analysis_duplicate_ids')
    if sum(r.action=='move_to_front' for r in analysis.recommendations)>1: raise ValueError('analysis_multiple_hooks')
    return analysis

def build_timeline(duration, recommendations):
    removals=sorted((r.start,r.end) for r in recommendations if r.action=='remove')
    merged=[]
    for a,b in removals:
        a=max(0,a); b=min(duration,b)
        if b<=a: continue
        if merged and a<=merged[-1][1]: merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else: merged.append((a,b))
    kept=[]; cursor=0
    for a,b in merged:
        if a>cursor: kept.append((cursor,a))
        cursor=max(cursor,b)
    if cursor<duration: kept.append((cursor,duration))
    hooks=[r for r in recommendations if r.action=='move_to_front']
    if len(hooks)>1: raise ValueError('multiple_hooks')
    if hooks:
        h=hooks[0]
        if not any(a<=h.start and b>=h.end for a,b in kept): raise ValueError('hook_overlaps_cut')
        remaining=[]
        for a,b in kept:
            if a<h.start: remaining.append((a,min(b,h.start)))
            if b>h.end: remaining.append((max(a,h.end),b))
        kept=[(h.start,h.end),*remaining]
    kept=[(a,b) for a,b in kept if b-a>=0.08]
    if sum(b-a for a,b in kept)<min(2,duration*0.5): raise ValueError('too_much_removed')
    return kept

def remap_span(start,end,timeline):
    cursor=0; result=[]
    for a,b in timeline:
        left=max(start,a); right=min(end,b)
        if right-left>0.05: result.append((cursor+left-a,cursor+right-a))
        cursor+=b-a
    return result

def ass_time(t):
    cs=round(t*100)
    return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'

def subtitle_text(text, language):
    # Prevent ASS override commands and wrap comfortably inside a portrait frame.
    text=re.sub(r'[{}\\\r\n]',' ',text).strip()
    size=16 if language=='zh' else 34
    if language=='zh':
        from .caption_layout import chinese_lines
        lines=chinese_lines(text,size)
    else:
        lines=[]; current=''
        for word in text.split():
            if current and len(current)+len(word)+1>size: lines.append(current); current=''
            current=(current+' '+word).strip()
        if current: lines.append(current)
        if len(lines)==2:
            words=text.split()
            choices=[(' '.join(words[:i]),' '.join(words[i:])) for i in range(1,len(words))]
            choices=[(a,b) for a,b in choices if len(a)<=size and len(b)<=size]
            if choices: lines=list(min(choices,key=lambda pair:abs(len(pair[0])-len(pair[1]))))
    return '\\N'.join(lines)

def caption_chunks(raw, language):
    cleaned=re.sub(r'[{}\\\r\n]',' ',raw).strip()
    rendered=subtitle_text(cleaned,language)
    lines=rendered.split('\\N')
    if len(lines)<=2: return [rendered]
    if language=='zh':
        # Reuse word-safe line boundaries rather than splitting characters again.
        return ['\\N'.join(lines[i:i+2]) for i in range(0,len(lines),2)]
    tokens=list(cleaned) if language=='zh' else cleaned.split()
    # Balance cards instead of stranding the last word on its own screen.
    groups=math.ceil(len(lines)/2)
    while groups<=len(tokens):
        chunks=[]
        for i in range(groups):
            left=round(len(tokens)*i/groups); right=round(len(tokens)*(i+1)/groups)
            part=('' if language=='zh' else ' ').join(tokens[left:right])
            chunks.append(subtitle_text(part,language))
        if all(len(c.split('\\N'))<=2 for c in chunks): return chunks
        groups+=1
    return [rendered]

def emphasize_caption(chunk,terms,language,base_color):
    # Input caption was already sanitized; only constant ASS tags are introduced.
    clean_terms=sorted({re.sub(r'[{}\\\r\n]',' ',s).strip() for s in terms},key=len,reverse=True)
    patterns=[]
    for term in clean_terms:
        if not term:continue
        pattern=re.escape(term).replace(r'\ ',r'(?: |\\N)+')
        if language=='en':pattern=r'(?<!\w)'+pattern+r'(?!\w)'
        patterns.append(pattern)
    if not patterns:return chunk
    accent='&H00FFFF00' if base_color=='&H0000FFFF' else '&H0000FFFF'
    return re.sub('|'.join(patterns),lambda m:r'{\c'+accent+'}'+m.group(0)+r'{\c'+base_color+'}',chunk,flags=re.IGNORECASE if language=='en' else 0)

def write_subtitles(path, captions, timeline, language, w,h,style=None):
    style=style or {}
    font=max(22,round(h*{'small':.026,'medium':.035,'large':.045}.get(style.get('font_size'),.035)))
    color='&H0000FFFF' if style.get('color')=='yellow' else '&H00FFFFFF'
    alignment=8 if style.get('position')=='top' else 2
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,{font},{color},&H00FFFFFF,&H00121212,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,{alignment},{int(w*.08)},{int(w*.08)},{int(h*.15)},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    rows=[]
    for c in captions:
        raw=getattr(c,language) or c.original
        # Split long model phrases, distribute within their original timestamps.
        chunks=caption_chunks(raw,language)
        weights=[len(chunk.replace('\\N',' ')) for chunk in chunks]
        total=max(1,sum(weights)); cursor=0
        for i,chunk in enumerate(chunks):
            s=c.start+(c.end-c.start)*cursor/total
            cursor+=weights[i]
            e=c.start+(c.end-c.start)*cursor/total
            chunk=emphasize_caption(chunk,getattr(c,'emphasis_'+language,[]),language,color)
            for a,b in remap_span(s,e,timeline):
                rows.append((a,f'Dialogue: 0,{ass_time(a)},{ass_time(b)},Default,,0,0,0,,{chunk}\n'))
    path.write_text(header+''.join(row for _,row in sorted(rows)),encoding='utf-8')

def render(source,folder,metadata,analysis,recommendations,language,aspect,brolls=None,timeline_override=None,manual=None,asset_paths=None):
    if manual:
        from .manual import Edit,check
        from .schemas import Caption
        manual=Edit.model_validate(manual).model_dump()
        check(Edit.model_validate(manual),metadata['duration'])
        manual['clips']=[c for c in manual['clips'] if c['approved']]
        if not manual['clips']:raise ValueError('no_approved_changes')
        timeline_override=[(c['start'],c['end']) for c in manual['clips']]
    timeline=timeline_override if timeline_override is not None else build_timeline(metadata['duration'],recommendations)
    if not timeline or any(not 0<=a<b<=metadata['duration'] for a,b in timeline): raise ValueError('analysis_timestamps_invalid')
    if aspect=='original':
        scale=min(1,1920/max(metadata['width'],metadata['height']),1080/min(metadata['width'],metadata['height']))
        w=int(metadata['width']*scale)//2*2; h=int(metadata['height']*scale)//2*2
    else: w,h={'9:16':(1080,1920),'16:9':(1920,1080),'1:1':(1080,1080),'4:5':(1080,1350)}[aspect]
    captions=any(r.action=='captions' for r in recommendations)
    normalize=any(r.action=='normalize_audio' for r in recommendations)
    if manual:
        captions=manual['subtitles'];normalize=manual['normalize']
    parts=[]
    # Sequential clips keep memory bounded on the 4GB droplet.
    for i,(a,b) in enumerate(timeline):
        part=folder/f'part-{i:03}.mp4'; parts.append(part)
        vf=f'scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x101614,setsar=1,fps=30'
        cutaway=None;post=''
        if manual:
            clip=manual['clips'][i]
            cutaway=clip.get('external_broll') or clip.get('cutaway')
            from .timeline import motion_filter
            vf=motion_filter(clip,w,h,b-a)+vf
            base_vf=vf
            vf=''
            if clip['transition']=='fade':
                fade=min(.25,(b-a)/4)
                vf+=f',fade=t=in:st=0:d={fade},fade=t=out:st={b-a-fade}:d={fade}'
            if clip['text'].strip():
                title=folder/f'title-{i}.ass'
                write_subtitles(title,[Caption(start=0,end=b-a,original=clip['text'],en=clip['text'],zh=clip['text'])],[(0,b-a)],language,w,h,{'position':'top'})
                title_path=str(title.resolve()).replace('\\','/').replace(':','\\:').replace("'","'\\''")
                vf+=f",ass='{title_path}'"
            if clip.get('card'):
                from .visuals import write_card
                card_path=folder/f'card-{i}.ass'
                write_card(card_path,clip['card'],language,w,h)
                escaped=str(card_path.resolve()).replace('\\','/').replace(':','\\:').replace("'","'\\''")
                vf+=f",ass='{escaped}'"
            post=vf;vf=base_vf+post
        if cutaway:
            footage=(asset_paths or {}).get(cutaway['asset_id']) if 'asset_id' in cutaway else source
            if footage is None:raise ValueError('asset_not_found')
            length=cutaway['end']-cutaway['start']
            graph=f"[0:v]{base_vf}[base];[1:v]trim=duration={length},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=30,setpts=PTS-STARTPTS+{cutaway['start']}/TB[br];[base][br]overlay=enable='gte(t,{cutaway['start']})*lt(t,{cutaway['end']})':eof_action=pass:repeatlast=0{post}[v]"
            inputs=['-ss',a,'-i',source,'-ss',cutaway['source_start'],'-i',footage]
            filters=['-filter_complex_threads','1','-filter_complex',graph,'-map','[v]']
        else:
            inputs=['-ss',a,'-i',source];filters=['-vf',vf,'-map','0:v:0']
        if manual and metadata['has_audio'] and clip.get('audio_fade_ms',0):
            edge=min(clip['audio_fade_ms']/1000,(b-a)/4)
            filters+=['-af',f'afade=t=in:st=0:d={edge},afade=t=out:st={b-a-edge}:d={edge}']
        args=[*inputs,'-t',b-a,*filters,'-map','0:a:0?',
              '-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000',part]
        ffmpeg(*args,timeout=900)
        if manual and i>0:
            from .transitions import KINDS,apply
            if clip['transition'] in KINDS:apply(parts[i-1],part,clip['transition'],b-a)
    listing=folder/'concat.txt'
    listing.write_text(''.join(f"file '{p.name}'\n" for p in parts))
    base=folder/'assembled.mp4'
    ffmpeg('-f','concat','-safe','1','-i',listing,'-c','copy',base)
    input_path=base
    # Overlay generated footage while retaining the source voice / audio track.
    for i,item in enumerate(brolls or []):
        mapped=remap_span(item['start'],item['end'],timeline)
        if not mapped: continue
        a,b=mapped[0]; overlay=folder/f'overlay-{i}.mp4'
        vf=f'[1:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,setpts=PTS-STARTPTS+{a}/TB[br];[0:v][br]overlay=enable=\'between(t,{a},{b})\':eof_action=pass[v]'
        ffmpeg('-i',input_path,'-i',item['path'],'-filter_complex_threads','1','-filter_complex',vf,'-map','[v]','-map','0:a:0?',
               '-c:v','libx264','-preset','fast','-crf','18','-c:a','copy',overlay,timeout=900)
        input_path=overlay
    if manual:
        effects=[];cursor=0
        for clip in manual['clips']:
            effects.extend(e|{'at':cursor+e['at']} for e in clip['sound_effects'])
            cursor+=clip['end']-clip['start']
        if effects:
            from .sound_effects import mix
            input_path=mix(input_path,folder,effects,cursor,metadata['has_audio'])
    if manual and manual.get('music'):
        from .music import mix as mix_music
        track=(asset_paths or {}).get(manual['music']['asset_id'])
        if track is None:raise ValueError('asset_not_found')
        input_path=mix_music(input_path,track,folder,manual['music'],sum(b-a for a,b in timeline),probe(input_path)['has_audio'])
    filters=[]
    if captions:
        subs=folder/'captions.ass'; write_subtitles(subs,[Caption.model_validate(c) for c in manual['captions']] if manual else analysis.transcript,timeline,language,w,h,manual)
        # All paths generated internally; quote for libavfilter independently of shell.
        escaped=str(subs.resolve()).replace('\\','/').replace(':','\\:').replace("'","'\\''")
        filters.append(f"ass='{escaped}'")
    args=['-i',input_path]
    if filters: args+=['-vf',','.join(filters)]
    if normalize and metadata['has_audio']:
        _,stats=ffmpeg('-i',input_path,'-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-vn','-f','null','-')
        match=re.search(r'\{\s*"input_i"[\s\S]*?\}',stats)
        values=json.loads(match.group(0)) if match else {}
        measured=[values.get(k) for k in ['input_i','input_tp','input_lra','input_thresh','target_offset']]
        if all(v is not None and math.isfinite(float(v)) for v in measured):
            filters_a=f'loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={measured[0]}:measured_TP={measured[1]}:measured_LRA={measured[2]}:measured_thresh={measured[3]}:offset={measured[4]}:linear=true'
            args+=['-af',filters_a]
    args+=['-map','0:v:0','-map','0:a:0?','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',folder/'result.mp4']
    ffmpeg(*args,timeout=1200)
    output=probe(folder/'result.mp4')
    expected=sum(b-a for a,b in timeline)
    if abs(output['duration']-expected)>0.6: raise ValueError('output_duration_mismatch')
    ffmpeg('-i',folder/'result.mp4','-v','error','-f','null','-',timeout=600)
    if metadata['has_audio'] and not output['has_audio']: raise ValueError('output_audio_missing')
    for p in [*parts,base,*folder.glob('overlay-*.mp4')]: p.unlink(missing_ok=True)
    from .timeline import compile_timeline
    director_timeline=compile_timeline(Edit.model_validate(manual)) if manual else None
    return {'director_timeline':director_timeline,'metadata':output,'timeline':timeline,'applied':[r.id for r in recommendations], 'generated_clips':len(brolls or [])}
