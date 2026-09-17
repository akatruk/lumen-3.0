"""Bounded onset analysis; tempo is reported only for a regular pulse."""
import array,math,statistics,subprocess,sys

def detect(samples,rate=2000):
    hop=max(1,round(rate*.02))
    energy=[math.sqrt(sum(x*x for x in samples[i:i+hop])/hop) for i in range(0,len(samples)-hop+1,hop)]
    if not energy or max(energy)<1e-5:return {'version':1,'accents':[],'bpm':None,'regularity':0}
    novelty=[0]+[max(0,energy[i]-energy[i-1]) for i in range(1,len(energy))]
    threshold=max(novelty)*.15
    peaks=[]
    for i in range(1,len(novelty)-1):
        local=novelty[max(0,i-25):min(len(novelty),i+26)]
        if novelty[i]>max(threshold,statistics.median(local)*3) and novelty[i]>=novelty[i-1] and novelty[i]>novelty[i+1]:
            if peaks and i-peaks[-1]<8:
                if novelty[i]>novelty[peaks[-1]]:peaks[-1]=i
            else:peaks.append(i)
    times=[round(i*hop/rate,3) for i in peaks]
    intervals=[b-a for a,b in zip(times,times[1:])]
    median=statistics.median(intervals) if intervals else 0
    regularity=sum(abs(v-median)<.08 for v in intervals)/len(intervals) if intervals else 0
    bpm=round(60/median,1) if len(times)>=8 and regularity>=.65 and .25<=median<=1.5 else None
    return {'version':1,'accents':times,'bpm':bpm,'regularity':round(regularity,3)}

def analyze(path):
    result=subprocess.run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file,pipe','-i',str(path),'-t','420','-vn','-ac','1','-ar','2000','-f','f32le','pipe:1'],capture_output=True,timeout=60)
    if result.returncode:raise ValueError('media_processing_failed')
    samples=array.array('f');samples.frombytes(result.stdout)
    if sys.byteorder!='little':samples.byteswap()
    return detect(samples)
