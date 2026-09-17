"""Original tutorial speech. Reuses existing private OpenRouter configuration; no secret output."""
import json,urllib.request,urllib.error,concurrent.futures,hashlib,os
from pathlib import Path
root=Path(__file__).resolve().parent
script=json.loads((root/'guide-script.json').read_text())
out=root/'public/guide-v2';out.mkdir(parents=True,exist_ok=True)
key=os.environ.get('OPENROUTER_API_KEY')
if not key:
 from dotenv import dotenv_values
 key=dotenv_values(root.parent/'.env').get('OPENROUTER_API_KEY')
if not key:raise SystemExit('OpenRouter key not configured')
voices={'en':'English_Graceful_Lady','zh':'Chinese (Mandarin)_Warm_Bestie'}
jobs=[(lang,'quick',script['quick'][lang]) for lang in voices]+[(lang,s['id'],s[lang]) for lang in voices for s in script['scenes']]
def generate(job):
 lang,name,text=job;path=out/f'{lang}-{name}.mp3';meta=path.with_suffix('.json');digest=hashlib.sha256(text.encode()).hexdigest()
 if path.exists() and meta.exists() and json.loads(meta.read_text()).get('script_hash')==digest:return
 req=urllib.request.Request('https://openrouter.ai/api/v1/audio/speech',data=json.dumps(dict(model='minimax/speech-2.8-hd',voice=voices[lang],input=text,response_format='mp3')).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=120) as r:
   if 'audio' not in r.headers.get('Content-Type',''):raise RuntimeError('Non-audio response')
   data=r.read();gid=r.headers.get('X-Generation-Id')
  if len(data)<1000:raise RuntimeError('Empty audio')
  path.write_bytes(data);meta.write_text(json.dumps(dict(script_hash=digest,voice=voices[lang],model='minimax/speech-2.8-hd',generation_id=gid),indent=2))
  print(lang,name,'generated',flush=True)
 except urllib.error.HTTPError as e:raise RuntimeError(f'TTS HTTP {e.code} for {lang}/{name}') from None
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(generate,jobs))
