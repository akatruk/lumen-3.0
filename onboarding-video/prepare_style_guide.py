"""Build the style-match guide audio, captions, and chapter timings."""
import json, math, re, subprocess
from pathlib import Path
root = Path(__file__).resolve().parent
rows = json.loads((root / 'style-guide-script.json').read_text())
audio = root / 'public' / 'style-guide'
audio.mkdir(parents=True, exist_ok=True)
out = root.parent / 'frontend' / 'public' / 'tutorial'
out.mkdir(exist_ok=True)
voices = {'en': 'Samantha (English (US))', 'zh': 'Tingting (Chinese (China mainland))'}

def stamp(ms):
    ms = round(ms)
    return f'{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02}.{ms % 1000:03}'

manifest = {}
for lang, voice in voices.items():
    offset = 0
    scenes, captions, chapters = [], [], []
    for row in rows:
        aiff = audio / f'{lang}-{row["id"]}.aiff'
        wav = audio / f'{lang}-{row["id"]}.wav'
        subprocess.run(['say', '-v', voice, '-r', '168', '-o', str(aiff), row['text'][lang]], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(aiff), '-ar', '48000', '-ac', '1', str(wav)], check=True)
        seconds = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', str(wav)]))
        frames = math.ceil((seconds + 0.8) * 30)
        start = offset / 30
        chunks = []
        for sentence in re.split(r'(?<=[。！？.!?])\s*', row['text'][lang]):
            if not sentence:
                continue
            tokens = sentence.split() if lang == 'en' else list(sentence)
            n = max(1, math.ceil(len(tokens) / (12 if lang == 'en' else 24)))
            chunks += [(' ' if lang == 'en' else '').join(tokens[round(len(tokens) * i / n):round(len(tokens) * (i + 1) / n)]) for i in range(n)]
        total = sum(len(c) for c in chunks) or 1
        cursor = start + 0.2
        for chunk in chunks:
            end = cursor + seconds * len(chunk) / total
            captions.append({'text': chunk, 'startMs': round(cursor * 1000), 'endMs': round(end * 1000)})
            cursor = end
        scenes.append({'id': row['id'], 'fromFrame': offset, 'frames': frames, 'audio': f'style-guide/{lang}-{row["id"]}.wav', 'title': row['title'][lang], 'lines': row['lines'][lang]})
        chapters.append({'id': row['id'], 'title': row['title'][lang], 'text': row['text'][lang], 'start': round(start, 3)})
        offset += frames
    manifest[lang] = {'frames': offset, 'scenes': scenes, 'captions': captions, 'seconds': offset / 30, 'chapters': chapters}
    (out / f'lumen-style-{lang}-v5.vtt').write_text('WEBVTT\n\n' + ''.join(f"{stamp(c['startMs'])} --> {stamp(c['endMs'])}\n{c['text']}\n\n" for c in captions))
(root / 'src' / 'style-guide').mkdir(parents=True, exist_ok=True)
(root / 'src' / 'style-guide' / 'timing.json').write_text(json.dumps({lang: {'frames': manifest[lang]['frames'], 'scenes': manifest[lang]['scenes'], 'captions': manifest[lang]['captions']} for lang in voices}, ensure_ascii=False, indent=2))
site = json.loads((root.parent / 'frontend' / 'src' / 'tutorial-content.json').read_text())
for lang in ('en', 'zh'):
    site[lang]['style'] = {'seconds': manifest[lang]['seconds'], 'chapters': manifest[lang]['chapters']}
site.setdefault('ru', {})
en_chapters = {row['id']: row for row in rows}
site['ru']['style'] = {
    'seconds': manifest['en']['seconds'],
    'chapters': [{'id': chapter['id'], 'title': en_chapters[chapter['id']]['title']['ru'], 'text': en_chapters[chapter['id']]['text']['ru'], 'start': chapter['start']} for chapter in manifest['en']['chapters']],
}
(root.parent / 'frontend' / 'src' / 'tutorial-content.json').write_text(json.dumps(site, ensure_ascii=False, indent=2) + '\n')
print({lang: round(manifest[lang]['seconds'], 1) for lang in voices})
