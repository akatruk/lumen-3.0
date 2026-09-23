import json
import math
import time
import uuid
from .database import connect
from .config import settings

def init_db():
    with connect() as db:
        db.schema_lock()
        if not db.postgres: db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS tikhub_calls(id INTEGER PRIMARY KEY AUTOINCREMENT, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS douyin_results(id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), data TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS douyin_searches(id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), cache_key TEXT NOT NULL, data TEXT NOT NULL, created REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS douyin_cache ON douyin_searches(user_id,cache_key,created);
        CREATE TABLE IF NOT EXISTS google_identities(subject TEXT PRIMARY KEY, user_id TEXT UNIQUE NOT NULL REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS oauth_states(state TEXT PRIMARY KEY, binding TEXT NOT NULL, verifier TEXT NOT NULL, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), title TEXT NOT NULL, brief TEXT NOT NULL,
          language TEXT NOT NULL, aspect TEXT NOT NULL, auto_render INTEGER NOT NULL, generative INTEGER NOT NULL, budget REAL NOT NULL,
          status TEXT NOT NULL, stage TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0, metadata TEXT, analysis TEXT, result TEXT,
          error TEXT, created REAL NOT NULL, updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS project_sources(project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE, result_id TEXT NOT NULL, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id) ON DELETE CASCADE, kind TEXT NOT NULL,
          payload TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS jobs_queue ON jobs(status,created);
        CREATE TABLE IF NOT EXISTS spend(id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id) ON DELETE CASCADE, amount REAL NOT NULL,
          actual REAL, purpose TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
          kind TEXT NOT NULL, detail TEXT NOT NULL, created REAL NOT NULL);
        ''')
        from .soundtracks import init as init_soundtracks
        init_soundtracks(db)
        from .studio import init as init_studio
        init_studio(db)
        from .dubbing import init as init_dubbing
        init_dubbing(db)
        from .director_revisions import init as init_director_revisions
        init_director_revisions(db)
        from .variants import init as init_variants
        init_variants(db)
        from .trends import init as init_trends
        init_trends(db)
        if 'auth_method' not in db.columns('sessions'):
            db.execute("ALTER TABLE sessions ADD COLUMN auth_method TEXT NOT NULL DEFAULT 'password'")

def project(project_id, user_id=None):
    with connect() as db:
        r = db.execute('SELECT * FROM projects WHERE id=?' + (' AND user_id=?' if user_id else ''),
                       (project_id, user_id) if user_id else (project_id,)).fetchone()
        if not r: return None
        p = dict(r)
        p['studio'] = bool(db.execute('SELECT 1 FROM studio_projects WHERE project_id=?',(project_id,)).fetchone())
        for key in ['metadata','analysis','result']:
            p[key] = json.loads(p[key]) if p[key] else None
        source = db.execute('SELECT data FROM project_sources WHERE project_id=?',(project_id,)).fetchone()
        p['source'] = json.loads(source['data']) if source else None
        p['cost'] = db.execute('SELECT COALESCE(SUM(COALESCE(actual,amount)),0) FROM spend WHERE project_id=?',(project_id,)).fetchone()[0]
        p['events'] = [dict(e) for e in db.execute('SELECT kind,detail,created FROM events WHERE project_id=? ORDER BY id DESC LIMIT 25',(project_id,))]
        return p

def update(project_id, **fields):
    fields['updated'] = time.time()
    for k,v in fields.items():
        if k not in {'status','stage','progress','metadata','analysis','result','error','updated'}: raise ValueError(k)
        if isinstance(v,(dict,list)): fields[k] = json.dumps(v,ensure_ascii=False)
    with connect() as db:
        db.execute('UPDATE projects SET '+','.join(k+'=?' for k in fields)+' WHERE id=?', (*fields.values(),project_id))

def event(project_id, kind, detail):
    with connect() as db:
        db.execute('INSERT INTO events(project_id,kind,detail,created) VALUES(?,?,?,?)',(project_id,kind,detail,time.time()))

def enqueue(db, project_id, kind, payload=None):
    now=time.time()
    db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?)',(uuid.uuid4().hex,project_id,kind,json.dumps(payload or {}),'queued',now,now))

def reserve(project_id, amount, purpose):
    with connect() as db:
        db.lock()
        budget = db.execute('SELECT budget FROM projects WHERE id=?',(project_id,)).fetchone()[0]
        used = db.execute('SELECT COALESCE(SUM(COALESCE(actual,amount)),0) FROM spend WHERE project_id=?',(project_id,)).fetchone()[0]
        daily = db.execute('SELECT COALESCE(SUM(COALESCE(actual,amount)),0) FROM spend WHERE created>?',(time.time()-86400,)).fetchone()[0]
        if used+amount > budget or daily+amount > settings.daily_budget_usd:
            raise ValueError('budget_limit')
        token = uuid.uuid4().hex
        db.execute('INSERT INTO spend VALUES(?,?,?,?,?,?)',(token,project_id,amount,None,purpose,time.time()))
        return token

def settle(token, actual):
    if actual is not None and math.isfinite(float(actual)):
        with connect() as db:
            db.execute('UPDATE spend SET actual=? WHERE id=?',(max(0,float(actual)),token))
