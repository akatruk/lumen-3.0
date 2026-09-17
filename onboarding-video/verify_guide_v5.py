"""Optional speech-completeness check of the generated narration via transcription."""
import os,json,subprocess,urllib.request,base64,concurrent.futures
from pathlib import Path
from dotenv import dotenv_values
root=Path(__file__).resolve().parent
config=dotenv_values(os.environ.get('LUMEN_VOICE_CONFIG',str(root.parent/'.env')))
key=os.environ.get('OPENROUTER_API_KEY') or config.get('OPENROUTER_API_KEY')
timing=json.loads(Path(os.environ.get('LUMEN_TIMING',str(root/'src/guide-v5/timing.json'))).read_text())
out=root/'public/guide-v5'
def check(job):
 lang,kind=job;target=out/f'{lang}-{kind}-check.mp3';parts=[]
 for s in timing[lang][kind]['scenes']:
  src=out/f"{lang}-{s['id']}.mp3";dst=out/f"{lang}-{s['id']}-padded.wav";parts.append(dst)
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(src),'-af','adelay=200,apad','-t',str(s['frames']/30),'-ar','48000','-ac','1',str(dst)],check=True)
 listing=out/f'{lang}-{kind}-concat.txt';listing.write_text(''.join(f"file '{p.name}'\n" for p in parts))
 subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','1','-i',str(listing),'-c:a','libmp3lame','-b:a','96k',str(target)],check=True)
 payload=dict(model='openai/whisper-large-v3',input_audio=dict(data=base64.b64encode(target.read_bytes()).decode(),format='mp3'),language=lang,response_format='verbose_json',timestamp_granularities=['segment'])
 req=urllib.request.Request('https://openrouter.ai/api/v1/audio/transcriptions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=180) as r:data=json.load(r)
 (out/f'{lang}-{kind}-transcription.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 print(lang,kind,'transcribed',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(check,[(l,k) for l in ['en','zh'] for k in ['guide','walkthrough']]))
