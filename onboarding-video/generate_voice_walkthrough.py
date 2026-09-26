"""Generate the voice-walkthrough narration with the language's own stock voice.

Same speech call as generate_guide_v5.py. English uses en-female. Chinese uses zh-female.
Never print credentials.
"""
import json, os, hashlib, urllib.request, concurrent.futures
from pathlib import Path
from dotenv import dotenv_values

root = Path(__file__).resolve().parent
config = dotenv_values(os.environ.get('LUMEN_VOICE_CONFIG', str(root.parent / '.env')))
key = os.environ.get('OPENROUTER_API_KEY') or config.get('OPENROUTER_API_KEY') or config.get('openrouter_api_key')
if not key:
    raise RuntimeError('Voice provider not configured')
rows = json.loads((root / 'voice-walkthrough-script.json').read_text())
out = root / 'public' / 'voice-walkthrough'
out.mkdir(parents=True, exist_ok=True)
# Product ids from backend/dubbing_audio.py. Do not swap languages.
voices = {
    'en': {'id': 'en-female', 'provider': 'English_Graceful_Lady'},
    'zh': {'id': 'zh-female', 'provider': 'Chinese (Mandarin)_Warm_Bestie'},
}

def generate(job):
    row, lang = job
    text = row['text'][lang]
    dest = out / f'{lang}-{row["id"]}.mp3'
    meta = dest.with_suffix('.json')
    digest = hashlib.sha256(text.encode()).hexdigest()
    voice = voices[lang]
    if dest.exists() and meta.exists() and json.loads(meta.read_text()).get('script_hash') == digest and json.loads(meta.read_text()).get('voice_id') == voice['id']:
        print(lang, row['id'], 'cached', flush=True)
        return
    payload = {'model': 'minimax/speech-2.8-hd', 'voice': voice['provider'], 'input': text, 'response_format': 'mp3'}
    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/audio/speech',
        data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        if 'audio' not in response.headers.get('Content-Type', ''):
            raise RuntimeError('No audio returned')
        data = response.read()
    if len(data) < 1000:
        raise RuntimeError('Empty audio')
    dest.write_bytes(data)
    meta.write_text(json.dumps({
        'script_hash': digest,
        'voice_id': voice['id'],
        'voice': voice['provider'],
        'model': payload['model'],
    }))
    print(lang, row['id'], 'ready', voice['id'], flush=True)

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(generate, [(row, lang) for row in rows for lang in voices]))
