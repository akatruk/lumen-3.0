"""Owned/licensed music beds with bounded gain and source-audio ducking."""
import json,math
from pydantic import Field,model_validator
from .schemas import Strict

class MusicLevel(Strict):
    at:float=Field(ge=0,le=840)
    gain_db:float=Field(ge=-40,le=-6)

class Music(Strict):
    asset_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    source_start:float=Field(default=0,ge=0)
    gain_db:float=Field(default=-24,ge=-40,le=-6)
    fade_in:float=Field(default=1,ge=0,le=10)
    fade_out:float=Field(default=2,ge=0,le=10)
    duck:bool=True
    loop_fade_ms:int=Field(default=0,ge=0,le=250)
    levels:list[MusicLevel]=Field(default_factory=list,max_length=8)
    locked:bool=False
    @model_validator(mode='after')
    def ordered_levels(self):
        if self.levels and (self.levels[0].at!=0 or any(b.at<=a.at for a,b in zip(self.levels,self.levels[1:]))):raise ValueError('music_levels_not_ordered')
        return self

def gain_filter(config):
    points=config.get('levels',[])
    if not points:return f"volume={config['gain_db']}dB"
    expression=str(10**(points[-1]['gain_db']/20))
    for a,b in reversed(list(zip(points,points[1:]))):
        start=10**(a['gain_db']/20);end=10**(b['gain_db']/20)
        expression=f"if(lt(t,{b['at']}),{start}+({end-start})*(t-{a['at']})/{b['at']-a['at']},{expression})"
    return f"volume='{expression}':eval=frame"

def probe_audio(path):
    from .media import run
    out,_=run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_format','-show_streams','-of','json',str(path)],30)
    data=json.loads(out);fmt=data.get('format',{})
    if not set(fmt.get('format_name','').split(',')) & {'mp3','wav','flac','ogg','mov','mp4'}:raise ValueError('not_audio')
    if not any(s['codec_type']=='audio' for s in data.get('streams',[])):raise ValueError('not_audio')
    duration=float(fmt.get('duration',0))
    if not math.isfinite(duration) or duration<=0:raise ValueError('not_audio')
    mime=next((mime for fmt_name,mime in [('mp3','audio/mpeg'),('wav','audio/wav'),('flac','audio/flac'),('ogg','audio/ogg')] if fmt_name in fmt.get('format_name','').split(',')),'audio/mp4')
    return {'duration':duration,'has_audio':True,'kind':'music','mime':mime,'size':int(fmt['size'])}

def smooth_loop(bed,output_duration,milliseconds):
    """Soften repeating excerpt edges without shifting beats or video timestamps."""
    from .media import ffmpeg
    if not milliseconds:return False
    length=probe_audio(bed)['duration']
    if length>=output_duration:return False
    fade=min(milliseconds/1000,length/4)
    target=bed.with_name('music-bed-smoothed.wav')
    ffmpeg('-i',bed,'-af',f'afade=t=in:d={fade},afade=t=out:st={length-fade}:d={fade}','-c:a','pcm_s16le',target)
    target.replace(bed)
    return True

def mix(source,track,folder,config,duration,has_audio):
    from .media import ffmpeg
    fade_in=min(config['fade_in'],duration/2);fade_out=min(config['fade_out'],duration/2)
    # Repeat the selected excerpt; trim after looping to exactly the output duration.
    bed=folder/'music-bed.wav'
    ffmpeg('-ss',config['source_start'],'-i',track,'-vn','-map','0:a:0','-ar',48000,'-ac',2,bed)
    smooth_loop(bed,duration,config.get('loop_fade_ms',0))
    graph=[f"[1:a]atrim=duration={duration},asetpts=PTS-STARTPTS,{gain_filter(config)},afade=t=in:d={fade_in},afade=t=out:st={duration-fade_out}:d={fade_out}[music]"]
    if has_audio:
        graph.append(f'[0:a]aresample=48000,apad,atrim=duration={duration}[original]')
        if config['duck']:
            graph.extend(['[original]asplit=2[voice][key]','[music][key]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=350[bed]','[voice][bed]amix=inputs=2:duration=first:normalize=0[mixed]'])
        else:graph.append('[original][music]amix=inputs=2:duration=first:normalize=0[mixed]')
    else:graph.append('[music]anull[mixed]')
    graph.append('[mixed]alimiter=limit=0.95:level=false:latency=true[a]')
    out=folder/'music-mix.mp4'
    ffmpeg('-i',source,'-stream_loop','-1','-i',bed,'-filter_complex',';'.join(graph),'-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-t',duration,out)
    bed.unlink(missing_ok=True)
    return out
