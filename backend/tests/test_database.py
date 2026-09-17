import concurrent.futures
import time
import pytest
from backend.db import connect,init_db,reserve
from backend.config import settings
from backend.database import worker_guard

def test_concurrent_budget_reservations(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'data_dir',tmp_path)
    init_db()
    with connect() as db:
        db.execute('INSERT INTO users VALUES(?,?,?,?)',('u','qa@invalid.test','disabled',time.time()))
        db.execute('INSERT INTO projects(id,user_id,title,brief,language,aspect,auto_render,generative,budget,status,stage,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',('p','u','Test','Test','en','original',0,0,1,'ready','ready',time.time(),time.time()))
    def attempt(_):
        try: reserve('p',.75,'concurrency-test');return True
        except ValueError as exc:
            assert str(exc)=='budget_limit';return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt,range(8)))==1
    with connect() as db:
        assert db.execute('SELECT SUM(amount) FROM spend').fetchone()[0]==.75

def test_transaction_rollback(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'data_dir',tmp_path);init_db()
    with pytest.raises(RuntimeError):
        with connect() as db:
            db.execute('INSERT INTO users VALUES(?,?,?,?)',('u','qa@invalid.test','disabled',time.time()))
            raise RuntimeError('rollback')
    with connect() as db: assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0

def test_postgres_worker_singleton():
    if not settings.database_url:pytest.skip('PostgreSQL only')
    with worker_guard():
        with pytest.raises(RuntimeError,match='already running'):
            with worker_guard(): pass
    with worker_guard(): pass

def test_sqlite_migration_preserves_values_and_sequences(tmp_path,monkeypatch):
    if not settings.database_url:pytest.skip('PostgreSQL only')
    from backend.migrate_postgres import migrate
    url=settings.database_url
    monkeypatch.setattr(settings,'data_dir',tmp_path)
    monkeypatch.setattr(settings,'database_url','')
    init_db()
    timestamp=1789441234.123456
    with connect() as db:
        db.execute('INSERT INTO users VALUES(?,?,?,?)',('u','qa@invalid.test','disabled',timestamp))
        db.execute('INSERT INTO sessions VALUES(?,?,?,?)',('hash-only','u',timestamp+3600,'google'))
        db.execute('INSERT INTO tikhub_calls(id,created) VALUES(?,?)',(9,timestamp))
    monkeypatch.setattr(settings,'database_url',url)
    counts=migrate(tmp_path/'lumen.db')
    assert counts['users']==1 and counts['sessions']==1
    with connect() as db:
        assert db.execute('SELECT created FROM users').fetchone()[0]==timestamp
        assert db.execute('SELECT auth_method FROM sessions').fetchone()[0]=='google'
        db.execute('INSERT INTO tikhub_calls(created) VALUES(?)',(timestamp,))
        assert db.execute('SELECT MAX(id) FROM tikhub_calls').fetchone()[0]==10
    with pytest.raises(RuntimeError,match='Destination must be empty'):migrate(tmp_path/'lumen.db')
