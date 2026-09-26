"""Normalize walkthrough speech, write v6 caption sidecars, and build Remotion timing.

Does not overwrite v5 tutorial files or tutorial-content.json.
"""
import json, math, re, subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
rows = json.loads((root / 'voice-walkthrough-script.json').read_text())
audio = root / 'public' / 'voice-walkthrough'
out = root.parent / 'frontend' / 'public' / 'tutorial'
out.mkdir(exist_ok=True)
voices = ('en', 'zh')

def stamp(ms):
    ms = round(ms)
    return f'{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02}.{ms % 1000:03}'

manifest = {}
for lang in voices:
    offset = 0
    scenes, captions = [], []
    for row in rows:
        name = f'{lang}-{row["id"]}'
        src = audio / f'{name}.mp3'
        wav = src.with_suffix('.wav')
        meta = json.loads(src.with_suffix('.json').read_text())
        expected = 'en-female' if lang == 'en' else 'zh-female'
        if meta.get('voice_id') != expected:
            raise SystemExit(f'{name} voice {meta.get("voice_id")} is not {expected}')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-af', 'loudnorm=I=-16:TP=-1.5:LRA=9', '-ar', '48000', '-ac', '1', str(wav)], check=True)
        seconds = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', str(wav)]))
        frames = math.ceil((seconds + 0.8) * 30)
        start = offset / 30
        chunks = []
        for sentence in re.split(r'(?<=[。！？.!?])\s*', row['text'][lang]):
            if not sentence:
                continue
            tokens = sentence.split() if lang == 'en' else list(sentence)
            n = max(1, math.ceil(len(tokens) / (13 if lang == 'en' else 27)))
            chunks += [(' ' if lang == 'en' else '').join(tokens[round(len(tokens) * i / n):round(len(tokens) * (i + 1) / n)]) for i in range(n)]
        total = sum(len(chunk) for chunk in chunks) or 1
        cursor = start + 0.2
        for chunk in chunks:
            end = cursor + seconds * len(chunk) / total
            captions.append({'text': chunk, 'startMs': round(cursor * 1000), 'endMs': round(end * 1000)})
            cursor = end
        scenes.append({'id': row['id'], 'fromFrame': offset, 'frames': frames, 'audio': f'voice-walkthrough/{name}.wav', 'title': row['title'][lang], 'lines': row['lines'][lang]})
        offset += frames
    manifest[lang] = {'frames': offset, 'scenes': scenes, 'captions': captions, 'seconds': offset / 30, 'voice_id': 'en-female' if lang == 'en' else 'zh-female'}
    note = 'en-female English_Graceful_Lady' if lang == 'en' else 'zh-female Chinese (Mandarin)_Warm_Bestie'
    (out / f'lumen-voice-{lang}-v6.vtt').write_text('WEBVTT\n\nNOTE voice ' + note + '\n\n' + ''.join(f"{stamp(c['startMs'])} --> {stamp(c['endMs'])}\n{c['text']}\n\n" for c in captions))

timing = {lang: {'frames': manifest[lang]['frames'], 'scenes': manifest[lang]['scenes'], 'captions': manifest[lang]['captions'], 'voice_id': manifest[lang]['voice_id']} for lang in voices}
(root / 'src' / 'voice-walkthrough').mkdir(parents=True, exist_ok=True)
(root / 'src' / 'voice-walkthrough' / 'timing.json').write_text(json.dumps(timing, ensure_ascii=False, indent=2))
print({lang: {'seconds': round(manifest[lang]['seconds'], 1), 'voice_id': manifest[lang]['voice_id']} for lang in voices})
