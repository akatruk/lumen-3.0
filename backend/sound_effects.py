"""Deterministic, original sound accents. No external audio/licensing dependency."""
import math,random,struct,wave
from typing import Literal
from pydantic import Field
from .schemas import Strict
class SoundEffect(Strict):
    kind:Literal['chime','click','whoosh']='chime'
    at:float=Field(ge=0)
    gain_db:float=Field(default=-24,ge=-36,le=-12)
DURATIONS={'chime':.6,'click':.08,'whoosh':.4}

def synthesize(path,kind,gain_db):
    rate=48000;length=DURATIONS[kind];n=round(rate*length);gain=10**(gain_db/20);rng=random.Random(42);data=bytearray()
    for i in range(n):
        t=i/rate;u=i/n
        if kind=='chime':v=(math.sin(2*math.pi*880*t)+.35*math.sin(2*math.pi*1320*t))/1.35*math.exp(-7*u)*min(1,t/.008)
        elif kind=='click':v=rng.uniform(-1,1)*math.exp(-12*u)*min(1,t/.002)
        else:v=rng.uniform(-1,1)*math.sin(math.pi*u)**2*.6
        data.extend(struct.pack('<h',round(v*gain*32767)))
    with wave.open(str(path),'wb') as out:out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes(data)

def mix(source,folder,effects,duration,has_audio):
    from .media import ffmpeg
    args=['-i',source];graph=[];labels=[]
    if has_audio:graph.append('[0:a]aresample=48000,apad,atrim=duration='+str(duration)+'[base]')
    else:graph.append('anullsrc=r=48000:cl=stereo,atrim=duration='+str(duration)+'[base]')
    labels.append('[base]')
    for i,e in enumerate(effects):
        path=folder/f'sfx-{i}.wav';synthesize(path,e['kind'],e['gain_db']);args+=['-i',path]
        graph.append(f"[{i+1}:a]adelay={round(e['at']*1000)}:all=1[s{i}]");labels.append(f'[s{i}]')
    graph.append(''.join(labels)+f'amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.95:level=false:latency=true[a]')
    out=folder/'sound-mix.mp4'
    ffmpeg(*args,'-filter_complex',';'.join(graph),'-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-t',duration,out,timeout=600)
    return out
