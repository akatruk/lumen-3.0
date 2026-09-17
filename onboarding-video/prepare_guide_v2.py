import json,subprocess,math,re
from pathlib import Path
root=Path(__file__).resolve().parent;audio=root/'public/guide-v2';script=json.loads((root/'guide-script.json').read_text())
def duration(path):return float(subprocess.check_output(['ffprobe','-v','quiet','-show_entries','format=duration','-of','csv=p=0',str(path)],text=True))
def stamp(t):
 ms=round(t);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'
def captions(text,lang,start,end):
 # Phrase-level captions, spread across measured audio. Not word-level karaoke.
 sentences=[s.strip() for s in re.split(r'(?<=[。！？.!?])\s*',text) if s.strip()]
 chunks=[]
 for sentence in sentences:
  tokens=sentence.split() if lang=='en' else list(sentence)
  n=max(1,math.ceil(len(tokens)/(11 if lang=='en' else 24)))
  for i in range(n):chunks.append((' ' if lang=='en' else '').join(tokens[round(len(tokens)*i/n):round(len(tokens)*(i+1)/n)]))
 weights=[len(x) for x in chunks];total=sum(weights);cursor=start;result=[]
 for text,w in zip(chunks,weights):
  finish=cursor+(end-start)*w/total;result.append(dict(text=text,startMs=round(cursor),endMs=round(finish),timestampMs=None,confidence=None));cursor=finish
 return result
manifest={}
for lang in ['en','zh']:
 scenes=[];allcaptions=[];offset=0
 for item in script['scenes']:
  name=f"{lang}-{item['id']}";src=audio/(name+'.mp3');dst=audio/(name+'.wav')
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(src),'-af','loudnorm=I=-16:TP=-1.5:LRA=9','-ar','48000','-ac','1',str(dst)],check=True)
  seconds=duration(dst);frames=math.ceil((seconds+.65)*30)
  caps=captions(item[lang],lang,offset/30*1000+200,offset/30*1000+200+seconds*1000)
  allcaptions.extend(caps);scenes.append(dict(id=item['id'],fromFrame=offset,frames=frames,audio='guide-v2/'+name+'.wav'));offset+=frames
 manifest[lang]=dict(frames=offset,scenes=scenes,captions=allcaptions)
 for kind in ['quick']:
  src=audio/f'{lang}-{kind}.mp3';seconds=duration(src)
  if seconds>9.78:raise RuntimeError(f'Quick voice exceeds 10 seconds: {lang} {seconds}')
  dst=audio/f'{lang}-{kind}.wav';subprocess.run(['ffmpeg','-v','error','-y','-i',str(src),'-af','loudnorm=I=-16:TP=-1.5:LRA=9','-ar','48000','-ac','1',str(dst)],check=True)
  manifest[lang]['quickCaptions']=captions(script['quick'][lang],lang,200,200+seconds*1000)
 for kind,caps in [('walkthrough',allcaptions),('guide',manifest[lang]['quickCaptions'])]:
  (root.parent/f'frontend/public/tutorial/lumen-{kind}-{lang}-v4.vtt').write_text('WEBVTT\n\n'+''.join(f"{stamp(c['startMs'])} --> {stamp(c['endMs'])}\n{c['text']}\n\n" for c in caps))
(root/'src/guide-v2/timing.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print({l:round(v['frames']/30,2) for l,v in manifest.items()})
