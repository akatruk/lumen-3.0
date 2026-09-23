"""Trend discovery sits in front of Studio. It never creates a second editor."""
import math
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field, model_validator
from .auth import current_user
from .db import connect
from .schemas import Strict

router = APIRouter(prefix='/api/trends')
SOURCES = ('manual', 'instagram', 'tiktok', 'youtube')
KINDS = ('original', 'safe', 'absurd', 'brand', 'creator')
SLOTS = ('expectation', 'interruption', 'escalation', 'reaction', 'punchline')

SAMPLES = (
    {'key': 'instagram', 'source': 'instagram', 'creator': 'Sample creator', 'caption': 'A quiet apartment tour is interrupted when the door opens onto a street market.', 'hashtags': 'travel', 'audio': 'Original voice', 'duration': 18, 'hours_old': 5, 'views': 12000, 'likes': 900, 'comments': 140, 'shares': 260},
    {'key': 'tiktok', 'source': 'tiktok', 'creator': 'Sample creator', 'caption': 'Someone expects a simple recipe and the last step changes the dish.', 'hashtags': 'food', 'audio': 'Original voice', 'duration': 14, 'hours_old': 3, 'views': 8000, 'likes': 1100, 'comments': 220, 'shares': 400},
    {'key': 'youtube', 'source': 'youtube', 'creator': 'Sample creator', 'caption': 'A city walk looks ordinary until the next corner reveals the real subject.', 'hashtags': 'city', 'audio': 'Original voice', 'duration': 22, 'hours_old': 8, 'views': 20000, 'likes': 700, 'comments': 90, 'shares': 180},
)


def init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS trend_items(
      id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      source TEXT NOT NULL, url TEXT NOT NULL, creator TEXT NOT NULL, published_at DOUBLE PRECISION NOT NULL,
      duration DOUBLE PRECISION NOT NULL, caption TEXT NOT NULL, hashtags TEXT NOT NULL, audio TEXT NOT NULL,
      category TEXT NOT NULL, sample INTEGER NOT NULL, created DOUBLE PRECISION NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS trend_signals(
      id TEXT PRIMARY KEY, trend_id TEXT NOT NULL REFERENCES trend_items(id) ON DELETE CASCADE,
      observed_at DOUBLE PRECISION NOT NULL, views BIGINT NOT NULL, likes BIGINT NOT NULL,
      comments BIGINT NOT NULL, shares BIGINT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS trend_dna(
      trend_id TEXT PRIMARY KEY REFERENCES trend_items(id) ON DELETE CASCADE,
      data TEXT NOT NULL, created DOUBLE PRECISION NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS trend_concepts(
      id TEXT PRIMARY KEY, trend_id TEXT NOT NULL REFERENCES trend_items(id) ON DELETE CASCADE,
      kind TEXT NOT NULL, data TEXT NOT NULL, chosen INTEGER NOT NULL, created DOUBLE PRECISION NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS project_trend_links(
      project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
      trend_id TEXT NOT NULL, concept_id TEXT NOT NULL, created DOUBLE PRECISION NOT NULL)''')


def trend_score(published_at, signals, now):
    """Prefer a fresh, accelerating video over a large but settled view count."""
    if not signals or published_at <= 0 or now <= published_at:
        return 0.0
    ordered = sorted(signals, key=lambda row: row['observed_at'])
    latest = ordered[-1]
    age_hours = max(0.25, (now - published_at) / 3600)
    views = max(0, int(latest['views']))
    views_per_hour = views / age_hours
    engagement_per_hour = (int(latest['likes']) + int(latest['comments']) + int(latest['shares'])) / age_hours
    share_ratio = int(latest['shares']) / views if views else 0
    comment_velocity = int(latest['comments']) / age_hours
    if len(ordered) >= 2:
        previous, current = ordered[-2], ordered[-1]
        gap = max(0.25, (current['observed_at'] - previous['observed_at']) / 3600)
        recent = max(0, int(current['views']) - int(previous['views'])) / gap
        earlier = int(previous['views']) / max(0.25, (previous['observed_at'] - published_at) / 3600)
        change = (recent - earlier) / max(1, earlier)
        acceleration = (max(-0.2, min(1.0, change)) + 0.2) / 1.2
    else:
        acceleration = 0.5
    recency = math.exp(-age_hours / 36)

    def unit(value, scale):
        return min(1.0, max(0.0, value / scale))

    raw = (0.28 * unit(views_per_hour, 40000) + 0.18 * unit(engagement_per_hour, 3000)
           + 0.16 * unit(share_ratio, 0.05) + 0.14 * unit(comment_velocity, 400)
           + 0.14 * acceleration + 0.10 * recency)
    return round(100 * raw, 1)


class Manual(Strict):
    url: str = Field(min_length=8, max_length=500)
    creator: str = Field(min_length=1, max_length=120)
    published_at: float
    duration: float = Field(gt=0, le=180)
    caption: str = Field(default='', max_length=2000)
    hashtags: str = Field(default='', max_length=300)
    audio: str = Field(default='', max_length=200)
    category: str = Field(default='general', max_length=40)
    views: int = Field(ge=0, le=10**12)
    likes: int = Field(ge=0, le=10**12)
    comments: int = Field(ge=0, le=10**12)
    shares: int = Field(ge=0, le=10**12)

    @model_validator(mode='after')
    def public_url(self):
        if not self.url.startswith(('https://', 'http://')) or ' ' in self.url:
            raise ValueError('invalid_url')
        if self.published_at > time.time() + 120:
            raise ValueError('invalid_date')
        return self


class Signal(Strict):
    views: int = Field(ge=0, le=10**12)
    likes: int = Field(ge=0, le=10**12)
    comments: int = Field(ge=0, le=10**12)
    shares: int = Field(ge=0, le=10**12)


def _loads(raw):
    import json
    return json.loads(raw) if raw else None


def _item(db, ident, user_id):
    row = db.execute('SELECT * FROM trend_items WHERE id=? AND user_id=?', (ident, user_id)).fetchone()
    if not row:
        raise HTTPException(404, 'not_found')
    return row


def _pack(db, row, now, full=False):
    import json
    signals = [dict(s) for s in db.execute('SELECT observed_at,views,likes,comments,shares FROM trend_signals WHERE trend_id=? ORDER BY observed_at', (row['id'],))]
    body = {key: row[key] for key in ('id', 'source', 'url', 'creator', 'published_at', 'duration', 'caption', 'hashtags', 'audio', 'category')}
    body['sample'] = bool(row['sample'])
    body['score'] = trend_score(row['published_at'], signals, now)
    body['signals'] = signals
    if full:
        dna = db.execute('SELECT data FROM trend_dna WHERE trend_id=?', (row['id'],)).fetchone()
        concepts = db.execute('SELECT id,kind,data,chosen FROM trend_concepts WHERE trend_id=? ORDER BY created', (row['id'],)).fetchall()
        body['dna'] = _loads(dna['data']) if dna else None
        body['concepts'] = [{'id': c['id'], 'kind': c['kind'], 'chosen': bool(c['chosen']), 'script': script_for(json.loads(c['data']))} | json.loads(c['data']) for c in concepts]
    return body


def _insert(db, user_id, source, url, creator, published_at, duration, caption, hashtags, audio, category, sample, views, likes, comments, shares):
    if source not in SOURCES:
        raise HTTPException(422, 'invalid_settings')
    now = time.time()
    ident = uuid.uuid4().hex
    db.execute('INSERT INTO trend_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', (
        ident, user_id, source, url, creator, published_at, duration, caption, hashtags, audio, category[:40] or 'general', int(sample), now))
    db.execute('INSERT INTO trend_signals VALUES(?,?,?,?,?,?,?)', (uuid.uuid4().hex, ident, now, views, likes, comments, shares))
    return ident


def build_dna(item):
    return {
        'method': 'metadata',
        'why': 'This structure is inferred from the caption and metrics you saved. The reference file was not downloaded or watched.',
        'slots': list(SLOTS),
        'hook': 'Open on a clear expectation, before anything turns.',
        'setup': 'Show an ordinary situation in your own place, with your own subject.',
        'conflict': 'Interrupt that expectation with a different event.',
        'surprise': 'Raise the stakes once, using footage you record.',
        'punchline': 'Land a reaction that pays off the interruption.',
        'pacing': f"About {max(1, round(item['duration']))} seconds. Put the turn in the first third.",
        'shot_structure': 'Wide setup, cut in on the interruption, hold the reaction.',
        'camera': 'Use your own phone framing. Do not match the reference shot for shot.',
        'editing_rhythm': 'Short setup, hard cut on the interruption, brief hold for the reaction.',
        'text_overlay': 'One original line at the turn. Do not copy the reference caption.',
        'audio_role': item['audio'] or 'Use original or licensed sound. Do not reuse the reference track.',
        'emotional_trigger': 'Surprise after a clearly stated expectation.',
        'meme_mechanism': 'The mechanism is a broken expectation, not a person, phrase, or joke to copy.',
        'duration': item['duration'],
        'narrative': 'Expectation → interruption → escalation → reaction → punchline',
        'observed_caption': (item['caption'] or '')[:280],
        'risks': [
            'Do not download the reference and replace faces or voices.',
            'Do not reuse the reference music, caption, or likeness.',
            'Platforms can reject a video that is only a repost of someone else.',
        ],
    }


def build_concepts(item, dna):
    frames = {
        'original': ('New version of this structure', 'Keep the five beats. Invent the people, place, and lines.'),
        'safe': ('Everyday parody', 'Use a familiar setting and original lines. Stay clear of a real person’s identity.'),
        'absurd': ('Absurd version', 'Make the interruption impossible, and still film it yourself.'),
        'brand': ('Brand version', 'The interruption can reveal a real offer. Do not invent prices, legal status, or results.'),
        'creator': ('Creator version', 'Film it in your own space, with your own voice.'),
    }
    rows = []
    for kind, (title, relation) in frames.items():
        rows.append((kind, {
            'title': title,
            'hook': dna['hook'],
            'story': f"{dna['narrative']}. {relation}",
            'characters': 'Original characters. Do not portray the reference creator.',
            'scenes': [dna['setup'], dna['conflict'], dna['surprise'], dna['punchline']],
            'dialogue': 'Write new lines for each beat. Do not reuse the reference caption.',
            'shots': dna['shot_structure'],
            'duration': max(8, min(60, round(item['duration']))),
            'editing_style': dna['editing_rhythm'],
            'relation': relation,
            'risks': dna['risks'],
        }))
    return rows


def script_for(concept):
    parts = [concept['story'], 'Scenes: ' + ' / '.join(concept['scenes']), concept['dialogue'], concept['shots']]
    parts.extend(concept['risks'])
    return '\n'.join(parts)[:6000]


def attach_concept(db, user_id, project_id, concept_id):
    row = db.execute('''SELECT c.trend_id, c.chosen FROM trend_concepts c
        JOIN trend_items t ON t.id=c.trend_id WHERE c.id=? AND t.user_id=?''', (concept_id, user_id)).fetchone()
    if not row:
        raise HTTPException(404, 'not_found')
    if not row['chosen']:
        raise HTTPException(422, 'concept_not_chosen')
    db.execute('INSERT INTO project_trend_links VALUES(?,?,?,?)', (project_id, row['trend_id'], concept_id, time.time()))


def _sample_card(sample, now):
    published = now - sample['hours_old'] * 3600
    signals = [{'observed_at': now, 'views': sample['views'], 'likes': sample['likes'], 'comments': sample['comments'], 'shares': sample['shares']}]
    return {
        'key': sample['key'], 'source': sample['source'], 'creator': sample['creator'], 'caption': sample['caption'],
        'hashtags': sample['hashtags'], 'audio': sample['audio'], 'duration': sample['duration'], 'category': sample['hashtags'],
        'sample': True, 'url': 'https://example.invalid/sample/' + sample['key'], 'published_at': published,
        'score': trend_score(published, signals, now),
        'note': 'Sample card. Nothing is fetched from the platform.',
    }


@router.get('')
def listing(user=Depends(current_user)):
    now = time.time()
    with connect() as db:
        rows = db.execute('SELECT * FROM trend_items WHERE user_id=? ORDER BY created DESC', (user['id'],)).fetchall()
        items = [_pack(db, row, now) for row in rows]
    items.sort(key=lambda item: item['score'], reverse=True)
    return {'items': items, 'samples': [_sample_card(sample, now) for sample in SAMPLES]}


@router.post('/manual', status_code=201)
def manual(body: Manual, request: Request, user=Depends(current_user)):
    from .app import rate_limit
    rate_limit(request, 'trend_manual', 30, 3600)
    with connect() as db:
        db.lock()
        ident = _insert(db, user['id'], 'manual', body.url, body.creator.strip(), body.published_at, body.duration,
                        body.caption.strip(), body.hashtags.strip(), body.audio.strip(), body.category.strip() or 'general',
                        False, body.views, body.likes, body.comments, body.shares)
        row = _item(db, ident, user['id'])
        return _pack(db, row, time.time(), full=True)


@router.post('/samples/{key}', status_code=201)
def save_sample(key: str, user=Depends(current_user)):
    sample = next((row for row in SAMPLES if row['key'] == key), None)
    if not sample:
        raise HTTPException(404, 'not_found')
    now = time.time()
    with connect() as db:
        db.lock()
        ident = _insert(db, user['id'], sample['source'], 'https://example.invalid/sample/' + key, sample['creator'],
                        now - sample['hours_old'] * 3600, sample['duration'], sample['caption'], sample['hashtags'],
                        sample['audio'], sample['hashtags'], True, sample['views'], sample['likes'], sample['comments'], sample['shares'])
        return _pack(db, _item(db, ident, user['id']), now, full=True)


@router.get('/{ident}')
def detail(ident: str, user=Depends(current_user)):
    with connect() as db:
        return _pack(db, _item(db, ident, user['id']), time.time(), full=True)


@router.post('/{ident}/signals', status_code=201)
def add_signal(ident: str, body: Signal, user=Depends(current_user)):
    now = time.time()
    with connect() as db:
        db.lock()
        _item(db, ident, user['id'])
        db.execute('INSERT INTO trend_signals VALUES(?,?,?,?,?,?,?)', (uuid.uuid4().hex, ident, now, body.views, body.likes, body.comments, body.shares))
        return _pack(db, _item(db, ident, user['id']), now, full=True)


@router.post('/{ident}/analyze')
def analyze(ident: str, user=Depends(current_user)):
    import json
    with connect() as db:
        db.lock()
        row = _item(db, ident, user['id'])
        dna = build_dna(row)
        now = time.time()
        db.execute('INSERT INTO trend_dna VALUES(?,?,?) ON CONFLICT(trend_id) DO UPDATE SET data=excluded.data, created=excluded.created', (ident, json.dumps(dna), now))
        return _pack(db, row, now, full=True)


@router.post('/{ident}/concepts')
def concepts(ident: str, user=Depends(current_user)):
    import json
    with connect() as db:
        db.lock()
        row = _item(db, ident, user['id'])
        dna_row = db.execute('SELECT data FROM trend_dna WHERE trend_id=?', (ident,)).fetchone()
        if not dna_row:
            raise HTTPException(409, 'analyze_first')
        linked = db.execute('SELECT 1 FROM project_trend_links l JOIN trend_concepts c ON c.id=l.concept_id WHERE c.trend_id=?', (ident,)).fetchone()
        if linked:
            raise HTTPException(409, 'concept_in_use')
        db.execute('DELETE FROM trend_concepts WHERE trend_id=?', (ident,))
        now = time.time()
        for kind, data in build_concepts(row, json.loads(dna_row['data'])):
            db.execute('INSERT INTO trend_concepts VALUES(?,?,?,?,?,?)', (uuid.uuid4().hex, ident, kind, json.dumps(data), 0, now))
        return _pack(db, row, now, full=True)


@router.post('/{ident}/concepts/{concept_id}/choose')
def choose(ident: str, concept_id: str, user=Depends(current_user)):
    with connect() as db:
        db.lock()
        _item(db, ident, user['id'])
        row = db.execute('SELECT id FROM trend_concepts WHERE id=? AND trend_id=?', (concept_id, ident)).fetchone()
        if not row:
            raise HTTPException(404, 'not_found')
        db.execute('UPDATE trend_concepts SET chosen=0 WHERE trend_id=?', (ident,))
        db.execute('UPDATE trend_concepts SET chosen=1 WHERE id=?', (concept_id,))
        return _pack(db, _item(db, ident, user['id']), time.time(), full=True)
