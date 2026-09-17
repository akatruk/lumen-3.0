"""Centered moving-shot transitions; preserve each clip's duration and audio.

A short tail/head (at most 150 ms each) is stretched across the 300 ms
transition window. No frames outside approved source ranges are introduced.
Audio remains sample-identical; visual timing displacement is bounded by 150 ms.
"""
KINDS={'crossfade':'fade','zoom':'zoomin','wipe':'wipeleft','circle':'circleopen'}

def apply(previous,current,kind,duration):
    from .media import ffmpeg,probe
    previous_duration=probe(previous)['duration']
    # Whole frames make the split and concatenation stable at the render rate.
    frames=min(4,int(previous_duration*30/4),int(duration*30/4))
    if frames<1:return
    half=frames/30
    window=2*half
    start=previous_duration-half
    outgoing=previous.with_suffix('.transition-next.mp4')
    incoming=current.with_suffix('.transition.mp4')
    graph=(
        f'[0:v]fps=30,settb=AVTB,setpts=PTS-STARTPTS,format=yuv420p,split[p][pt];'
        f'[1:v]fps=30,settb=AVTB,setpts=PTS-STARTPTS,format=yuv420p,split[c][ct];'
        f'[pt]trim=start={start}:end={previous_duration},setpts=2*(PTS-STARTPTS),fps=30,tpad=stop_mode=clone:stop_duration={half},trim=duration={window}[a];'
        f'[ct]trim=start=0:end={half},setpts=2*(PTS-STARTPTS),fps=30,tpad=stop_mode=clone:stop_duration={half},trim=duration={window}[b];'
        f'[a][b]xfade=transition={KINDS[kind]}:duration={window}:offset=0,split[x][y];'
        f'[p]trim=end={start},setpts=PTS-STARTPTS[prefix];'
        f'[x]trim=end={half},setpts=PTS-STARTPTS[left];'
        f'[y]trim=start={half}:end={window},setpts=PTS-STARTPTS[right];'
        f'[c]trim=start={half},setpts=PTS-STARTPTS[suffix];'
        '[prefix][left]concat=n=2:v=1:a=0[prev];'
        '[right][suffix]concat=n=2:v=1:a=0[next]'
    )
    try:
        ffmpeg('-i',previous,'-i',current,'-filter_complex_threads',1,'-filter_complex',graph,
            '-map','[prev]','-map','0:a:0?','-t',previous_duration,
            '-c:v','libx264','-preset','fast','-crf',18,'-pix_fmt','yuv420p','-c:a','copy',outgoing,
            '-map','[next]','-map','1:a:0?','-t',duration,
            '-c:v','libx264','-preset','fast','-crf',18,'-pix_fmt','yuv420p','-c:a','copy',incoming,timeout=900)
        outgoing.replace(previous)
        incoming.replace(current)
    finally:
        outgoing.unlink(missing_ok=True);incoming.unlink(missing_ok=True)
