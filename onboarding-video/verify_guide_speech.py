"""Transcribe original tutorial narration for pronunciation/completeness QA."""
import json,subprocess,urllib.request,base64,concurrent.futures
from pathlib import Path
from dotenv import dotenv_values
root=Path(__file__).resolve().parent;out=root/'public/guide-v2';timing=json.loads((root/'src/guide-v2/timing.json').read_text());key=dotenv_values(root.parent/'.env').get('OPENROUTER_API_KEY')
def check(lang,kind):
 target=out/f'{lang}-{kind}-mix.mp3'
 if kind=='quick':
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(out/f'{lang}-quick.wav'),'-af','adelay=200,apad','-t','10','-c:a','libmp3lame','-b:a','128k',str(target)],check=True)
 else:
  parts=[]
  for s in timing[lang]['scenes']:
   path=out/f"{lang}-{s['id']}-padded.wav";parts.append(path)
   subprocess.run(['ffmpeg','-v','error','-y','-i',str(root/'public'/s['audio']),'-af','adelay=200,apad','-t',str(s['frames']/30),str(path)],check=True)
  listing=out/f'{lang}-concat.txt';listing.write_text(''.join("file '"+p.name+"'\n" for p in parts))
  subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','1','-i',str(listing),'-c:a','libmp3lame','-b:a','128k',str(target)],check=True)
 dest=out/f'{lang}-{kind}-transcription.json'
 if dest.exists():return
 payload=dict(model='openai/whisper-large-v3',input_audio=dict(data=base64.b64encode(target.read_bytes()).decode(),format='mp3'),language=lang,response_format='verbose_json',timestamp_granularities=['segment','word'])
 req=urllib.request.Request('https://openrouter.ai/api/v1/audio/transcriptions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=120) as r:data=json.load(r)
 dest.write_text(json.dumps(data,ensure_ascii=False,indent=2));print(lang,kind,data.get('text',''),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda j:check(*j),[(l,k) for l in ['en','zh'] for k in ['quick','full']]))
