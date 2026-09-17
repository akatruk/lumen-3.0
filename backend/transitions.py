"""Incoming visual transitions preserve clip length and original audio timing."""
KINDS={'crossfade':'fade','zoom':'zoomin','wipe':'wipeleft','circle':'circleopen'}

def apply(previous,current,kind,duration):
    from .media import ffmpeg
    frame=current.with_suffix('.previous.png')
    output=current.with_suffix('.transition.mp4')
    try:
        ffmpeg('-sseof',-.04,'-i',previous,'-frames:v',1,frame)
        # Hold the outgoing frame into the incoming shot: no speech or timeline overlap is removed.
        graph=f'[0:v]fps=30,settb=AVTB,setpts=PTS-STARTPTS,format=yuv420p[a];[1:v]fps=30,settb=AVTB,setpts=PTS-STARTPTS,format=yuv420p[b];[a][b]xfade=transition={KINDS[kind]}:duration={min(.3,duration/2)}:offset=0[v]'
        ffmpeg('-loop',1,'-framerate',30,'-i',frame,'-i',current,'-filter_complex_threads',1,'-filter_complex',graph,'-map','[v]','-map','1:a:0?','-t',duration,'-c:v','libx264','-preset','fast','-crf',18,'-pix_fmt','yuv420p','-c:a','copy',output,timeout=900)
        output.replace(current)
    finally:
        frame.unlink(missing_ok=True);output.unlink(missing_ok=True)
