"""Bounded, labeled samples for reviewable matching of private library footage."""
import math
from .assets import path
from .media import ffmpeg,write_subtitles
from .schemas import Caption

def sample_ranges(duration):
    length=min(2.0,duration)
    return [{'start':round(s,3),'end':round(min(duration,s+length),3)} for s in sorted({0.0,max(0.0,(duration-length)/2),max(0.0,duration-length)})]

def video_ranges(duration,target_duration):
    """At most five coherent windows; cover short assets, spread across longer ones."""
    if not math.isfinite(duration) or not math.isfinite(target_duration) or min(duration,target_duration)<=0:
        raise ValueError('invalid_duration')
    length=min(4.0,duration,target_duration)
    if duration<=5*length:
        count=max(1,math.ceil(duration/length))
        return [{'start':round(i*duration/count,3),'end':round((i+1)*duration/count,3)} for i in range(count)]
    return [{'start':round(i*(duration-length)/4,3),'end':round(i*(duration-length)/4+length,3)} for i in range(5)]

def build_reel(pid,candidates,folder):
    folder.mkdir(parents=True,exist_ok=True);parts=[]
    for candidate in candidates:
        for span in candidate['samples']:
            index=len(parts);target=folder/f'sample-{index}.mp4';label=folder/f'sample-{index}.ass'
            length=span['end']-span['start']
            text=f"{candidate['label']} | source {span['start']:.2f}-{span['end']:.2f}s"
            write_subtitles(label,[Caption(start=0,end=length,original=text,en=text,zh=text)],[(0,length)],'en',360,640,{'position':'top'})
            escaped=str(label.resolve()).replace('\\','/').replace(':','\\:').replace("'","'\\''")
            ffmpeg('-ss',span['start'],'-i',path(pid,candidate['id']),'-t',length,'-vf',f"scale=360:640:force_original_aspect_ratio=decrease,pad=360:640:(ow-iw)/2:(oh-ih)/2,setsar=1,ass='{escaped}'",'-r','12','-an','-c:v','libx264','-preset','veryfast','-crf','28',target,timeout=120)
            parts.append(target)
    listing=folder/'samples.txt';listing.write_text(''.join(f"file '{p.name}'\n" for p in parts))
    output=folder/'candidates.mp4'
    ffmpeg('-f','concat','-safe','1','-i',listing,'-c','copy',output,timeout=120)
    if output.stat().st_size>8*1024*1024:raise ValueError('analysis_proxy_too_large')
    return output
