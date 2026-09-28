"""Centered moving-shot transitions; preserve each clip's duration and audio.

The default blend is 400 ms on each side of the join. A measured blend may run
longer, and a designed style-match blend may run shorter. Neither side is
longer than a quarter of its clip. No frames outside approved source ranges
are introduced. Audio stays sample-identical; only the picture blends.
"""
# ffmpeg wipeleft reveals the incoming picture from the right. wiperight reveals it
# from the left, so a right-arrival uses wipe rather than a second filter name.
# wipeup shows the new picture on the bottom first. wipedown shows it on the top first.
# diagtl travels toward the top left: the new picture arrives at the opposite corner.
# smooth* is the same direction with a soft edge. diagbl is not remapped: some
# ffmpeg builds draw it like wipedown, so the measured name stays the filter name.
KINDS={'crossfade':'fade','zoom':'zoomin','wipe':'wipeleft','wipe-up':'wipeup','wipe-down':'wipedown','circle':'circleopen','diagtl':'diagtl','diagtr':'diagtr','diagbl':'diagbl','diagbr':'diagbr'}
_SMOOTH={'wipeleft':'smoothleft','wipeup':'smoothup','wipedown':'smoothdown'}

def _mix(kind, window, eased):
    """A long or default join keeps its filter name. A short designed join eases."""
    name=KINDS[kind]
    if eased:
        name=_SMOOTH.get(name, name)
    if eased and name=='fade':
        # Smoothstep of the xfade progress. Not a light sweep.
        expr='A*(1-P*P*(3-2*P))+B*(P*P*(3-2*P))'
        return f"[a][b]xfade=transition=custom:duration={window}:offset=0:expr='{expr}',split[x][y];"
    return f'[a][b]xfade=transition={name}:duration={window}:offset=0,split[x][y];'

def apply(previous,current,kind,duration,blend=None):
    from .media import ffmpeg,probe
    previous_duration=probe(previous)['duration']
    # 12 frames is the default 400 ms on each side. A measured blend is the full
    # window, so each side is half of that. A quarter of either clip still wins.
    side=12
    eased=False
    try:
        measured=float(blend) if blend is not None else 0.0
    except (TypeError, ValueError):
        measured=0.0
    if measured>0.8:
        side=max(12,int(round(measured*30/2)))
    elif measured>=0.12:
        side=max(2,int(round(measured*30/2)))
        eased=True
    frames=min(side,int(previous_duration*30/4),int(duration*30/4))
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
        f'{_mix(kind, window, eased)}'
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
