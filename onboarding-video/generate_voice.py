"""Generate original Mandarin tutorial narration through OpenRouter; never print credentials."""
import json,urllib.request,urllib.error,concurrent.futures
from pathlib import Path
root=Path(__file__).resolve().parent
key=next(l.split('=',1)[1].strip().strip('\"\'') for l in (root.parent/'.env').read_text().splitlines() if l.startswith('OPENROUTER_API_KEY='))
script='上传视频，填写目标。智能分析，定位亮点。展开建议，勾选优化。生成新片，预览下载。'
def generate(voice,name):
 body={'model':'minimax/speech-2.8-hd','voice':voice,'input':script,'response_format':'mp3'}
 req=urllib.request.Request('https://openrouter.ai/api/v1/audio/speech',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=90) as r:
   data=r.read();ct=r.headers.get('Content-Type','');gid=r.headers.get('X-Generation-Id')
   if 'audio' not in ct: raise RuntimeError('Non-audio provider response')
  (root/'voice-candidates'/f'{name}.mp3').write_bytes(data)
  (root/'voice-candidates'/f'{name}.json').write_text(json.dumps({'model':body['model'],'voice':voice,'script':script,'generation_id':gid},ensure_ascii=False,indent=2))
  print(name,'generated',len(data),'bytes')
 except urllib.error.HTTPError as e:
  print(name,'HTTP',e.code,e.read().decode()[:800])
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 list(pool.map(lambda p:generate(*p),[('Chinese (Mandarin)_Warm_Bestie','warm'),('Chinese (Mandarin)_IntellectualGirl','intellectual')]))
