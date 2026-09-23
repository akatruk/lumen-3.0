"""One owned-word illustration. Reference pixels and reference text never enter the prompt."""
import base64
import json
import os
import re
import httpx
from .config import settings
from .db import connect, reserve, settle

def allow():
    return bool(settings.openrouter_api_key) and 'PYTEST_CURRENT_TEST' not in os.environ

def subject(text):
    cleaned = re.sub(r'[^0-9A-Za-z\u0400-\u04FF ]+', ' ', text or '')
    return ' '.join(cleaned.split())[:80] or 'abstract shapes'

def image_bytes(payload):
    message = ((payload.get('choices') or [{}])[0].get('message') or {})
    found = []
    for image in message.get('images') or []:
        found.append((image.get('image_url') or {}).get('url') or '')
    content = message.get('content')
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                found.append((part.get('image_url') or {}).get('url') or '')
    for url in found:
        if url.startswith('data:image') and ',' in url:
            raw = base64.b64decode(url.split(',', 1)[1])
            if raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff'):
                return raw
    return None

def fetch(prompt):
    body = {'model': settings.image_model, 'modalities': ['image', 'text'], 'messages': [{'role': 'user', 'content': prompt}]}
    headers = {'Authorization': 'Bearer ' + settings.openrouter_api_key, 'Content-Type': 'application/json', 'X-Title': 'Lumen Studio'}
    with httpx.Client(timeout=60) as client:
        response = client.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=body)
    if response.status_code != 200:
        raise ValueError('style_image_failed')
    raw = image_bytes(response.json())
    if not raw or len(raw) > 8 * 1024 * 1024:
        raise ValueError('style_image_failed')
    return raw

def attach_art(pid, manual, enabled):
    if not enabled or not manual:
        return manual
    target = next((clip for clip in manual.get('clips') or [] if clip.get('diagram') and not clip.get('art')), None)
    if target is None:
        return manual
    dest = settings.data_dir / pid / 'style-art-0.png'
    if not (dest.is_file() and dest.stat().st_size > 32):
        try:
            token = reserve(pid, 0.08, 'style_illustration')
        except ValueError:
            return manual
        try:
            prompt = 'Abstract editorial illustration, flat shapes, no text, no letters, no logos, no watermark, no people. Subject: ' + subject(target.get('text'))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(fetch(prompt))
            settle(token, 0.08)
        except Exception:
            settle(token, 0)
            return manual
    target['art'] = 'style-art-0.png'
    _remember(pid, target.get('id'))
    return manual

def _remember(pid, clip_id):
    with connect() as db:
        row = db.execute('SELECT config FROM studio_manual WHERE project_id=?', (pid,)).fetchone()
        if row and clip_id:
            config = json.loads(row['config'])
            for clip in config.get('clips') or []:
                if clip.get('id') == clip_id:
                    clip['art'] = 'style-art-0.png'
            db.execute('UPDATE studio_manual SET config=? WHERE project_id=?', (json.dumps(config), pid))
        project = db.execute('SELECT context FROM studio_projects WHERE project_id=?', (pid,)).fetchone()
        if not project:
            return
        context = json.loads(project['context'])
        report = context.get('style_report') or {}
        applied = list(report.get('applied') or [])
        if 'art' not in applied:
            applied.append('art')
        report['applied'] = applied
        context['style_report'] = report
        db.execute('UPDATE studio_projects SET context=? WHERE project_id=?', (json.dumps(context, ensure_ascii=False), pid))
