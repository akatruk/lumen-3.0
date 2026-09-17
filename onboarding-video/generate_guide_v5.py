"""Generate cached narration from the authored bilingual script; never print keys."""
import json,os,hashlib,urllib.request,concurrent.futures
from pathlib import Path
from dotenv import dotenv_values
root=Path(__file__).resolve().parent
config=dotenv_values(os.environ.get('LUMEN_VOICE_CONFIG',str(root.parent/'.env')))
key=os.environ.get('OPENROUTER_API_KEY') or config.get('OPENROUTER_API_KEY') or config.get('openrouter_api_key')
if not key:raise RuntimeError('Voice provider not configured')
rows=json.loads((root/'guide-v5-script.json').read_text());out=root/'public/guide-v5';out.mkdir(parents=True,exist_ok=True)
voices={'en':'English_Graceful_Lady','zh':'Chinese (Mandarin)_Warm_Bestie'}
def generate(job):
 row,lang=job;text=row['text'][lang];dest=out/f"{lang}-{row['id']}.mp3";meta=dest.with_suffix('.json');digest=hashlib.sha256(text.encode()).hexdigest()
 if dest.exists() and meta.exists() and json.loads(meta.read_text()).get('script_hash')==digest:return
 payload={'model':'minimax/speech-2.8-hd','voice':voices[lang],'input':text,'response_format':'mp3'}
 req=urllib.request.Request('https://openrouter.ai/api/v1/audio/speech',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=180) as r:
  if 'audio' not in r.headers.get('Content-Type',''):raise RuntimeError('No audio returned')
  data=r.read()
 if len(data)<1000:raise RuntimeError('Empty audio')
 dest.write_bytes(data);meta.write_text(json.dumps({'script_hash':digest,'voice':voices[lang],'model':payload['model']}))
 print(lang,row['id'],'ready',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(generate,[(r,l) for r in rows for l in voices]))
