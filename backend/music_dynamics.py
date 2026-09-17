"""Measured soundtrack dynamics; loudness is not an emotion classifier."""
import array,math,subprocess,sys

def describe(samples,rate=4000):
    hop=rate*2
    sections=[]
    for i in range(0,len(samples),hop):
        block=samples[i:i+hop]
        if not block:continue
        rms=math.sqrt(sum(v*v for v in block)/len(block))
        sections.append({'start':round(i/rate,3),'end':round((i+len(block))/rate,3),'db':round(20*math.log10(max(rms,1e-6)),1)})
    changes=[]
    for a,b in zip(sections,sections[1:]):
        delta=b['db']-a['db']
        if abs(delta)>=6:changes.append({'at':b['start'],'kind':'rise' if delta>0 else 'drop','delta_db':round(delta,1)})
    return {'sections':sections,'changes':sorted(changes,key=lambda x:abs(x['delta_db']),reverse=True)[:12],
            'quiet_ranges':[{'start':s['start'],'end':s['end']} for s in sections if s['db']<-45]}

def analyze(path):
    p=subprocess.run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file,pipe','-i',str(path),'-t','420','-vn','-ac','1','-ar','4000','-f','f32le','pipe:1'],capture_output=True,timeout=60)
    if p.returncode:raise ValueError('media_processing_failed')
    values=array.array('f');values.frombytes(p.stdout)
    if sys.byteorder!='little':values.byteswap()
    return describe(values)

def sample_ranges(duration,dynamics):
    length=min(4.,duration)
    starts=[0.,max(0.,(duration-length)/2),max(0.,duration-length)]
    sections=dynamics.get('sections',[])
    if sections:
        starts.append(max(sections,key=lambda s:s['db'])['start'])
        starts.append(min(sections,key=lambda s:s['db'])['start'])
    if dynamics.get('changes'):starts.append(max(0.,dynamics['changes'][0]['at']-1))
    selected=[]
    for start in starts:
        start=max(0.,min(start,duration-length))
        if any(abs(start-s)<length/2 for s in selected):continue
        selected.append(start)
    return [{'start':round(s,3),'end':round(min(duration,s+length),3)} for s in sorted(selected)]

def enrich(pid,candidates):
    from .assets import path
    for candidate in candidates:
        dynamics=analyze(path(pid,candidate['id']))
        candidate['dynamics']=dynamics
        candidate['samples']=sample_ranges(candidate['duration'],dynamics)
