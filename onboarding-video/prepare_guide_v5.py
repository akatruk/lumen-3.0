import json,math,re,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
rows=json.loads((root/'guide-v5-script.json').read_text());manifest={};site={}
out=root.parent/'frontend/public/tutorial';out.mkdir(exist_ok=True)
def stamp(ms):
 ms=round(ms);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'
for lang in ['en','zh']:
 manifest[lang]={};site[lang]={}
 for kind in ['guide','walkthrough']:
  offset=0;scenes=[];captions=[];chapters=[]
  for row in [r for r in rows if r['kind']==kind]:
   name=f"{lang}-{row['id']}";src=root/'public/guide-v5'/f'{name}.mp3';wav=src.with_suffix('.wav')
   subprocess.run(['ffmpeg','-v','error','-y','-i',str(src),'-af','loudnorm=I=-16:TP=-1.5:LRA=9','-ar','48000','-ac','1',str(wav)],check=True)
   seconds=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(wav)]))
   frames=math.ceil((seconds+.8)*30);start=offset/30
   chunks=[]
   for sentence in re.split(r'(?<=[。！？.!?])\s*',row['text'][lang]):
    if not sentence:continue
    tokens=sentence.split() if lang=='en' else list(sentence);n=max(1,math.ceil(len(tokens)/(13 if lang=='en' else 27)))
    chunks += [(' ' if lang=='en' else '').join(tokens[round(len(tokens)*i/n):round(len(tokens)*(i+1)/n)]) for i in range(n)]
   total=sum(len(c) for c in chunks);cursor=start+.2
   for c in chunks:
    end=cursor+seconds*len(c)/total;captions.append({'text':c,'startMs':round(cursor*1000),'endMs':round(end*1000)});cursor=end
   scenes.append({'id':row['id'],'fromFrame':offset,'frames':frames,'audio':f'guide-v5/{name}.wav','title':row['title'][lang],'lines':row['lines'][lang]})
   chapters.append({'id':row['id'],'title':row['title'][lang],'text':row['text'][lang],'start':start});offset+=frames
  manifest[lang][kind]={'frames':offset,'scenes':scenes,'captions':captions}
  site[lang][kind]={'seconds':offset/30,'chapters':chapters}
  (out/f'lumen-{kind}-{lang}-v5.vtt').write_text('WEBVTT\n\n'+''.join(f"{stamp(c['startMs'])} --> {stamp(c['endMs'])}\n{c['text']}\n\n" for c in captions))
(root/'src/guide-v5/timing.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(root.parent/'frontend/src/tutorial-content.json').write_text(json.dumps(site,ensure_ascii=False,indent=2))
print({l:{k:round(v['frames']/30,1) for k,v in m.items()} for l,m in manifest.items()})
