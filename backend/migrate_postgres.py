"""Offline SQLite -> empty PostgreSQL migration. Run with web/worker stopped.

Usage: DATABASE_URL='dbname=lumen user=lumen' python -m backend.migrate_postgres /path/to/sqlite-backup.db
The original SQLite file and media are never modified.
"""
import argparse
import sqlite3
from pathlib import Path
from .config import settings
from .db import init_db, connect

TABLES = ('users','sessions','tikhub_calls','douyin_results','douyin_searches',
          'google_identities','oauth_states','projects','project_sources','jobs',
          'spend','events','studio_projects','studio_requests','platform_packages','platform_history','director_proposals')

def migrate(path):
    if not settings.database_url: raise RuntimeError('DATABASE_URL must select PostgreSQL')
    source = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        if source.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('SQLite integrity check failed')
        if source.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('SQLite foreign key check failed')
        if source.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]:
            raise RuntimeError('Drain pending jobs before migration')
        init_db()
        with connect() as db:
            db.lock()
            for table in TABLES:
                if db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]:
                    raise RuntimeError('Destination must be empty; nothing imported')
            counts = {}
            existing={r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in TABLES:
                if table not in existing:
                    if table not in ('platform_packages','platform_history','director_proposals'):raise RuntimeError('Missing source table: '+table)
                    counts[table]=0;continue
                cursor=source.execute(f'SELECT * FROM {table}')
                columns=[c[0] for c in cursor.description]
                rows=cursor.fetchall()
                query=f'INSERT INTO {table} ({",".join(columns)}) VALUES ({",".join("?" for _ in columns)})'
                for row in rows: db.execute(query,row)
                keys=[r[1] for r in sorted(source.execute(f'PRAGMA table_info({table})'),key=lambda r:r[5]) if r[5]]
                actual=[tuple(r.values()) for r in db.execute(f'SELECT {",".join(columns)} FROM {table} ORDER BY {",".join(keys)}')]
                expected=sorted(rows,key=lambda r:tuple(r[columns.index(k)] for k in keys))
                if actual != expected: raise RuntimeError('Exact row validation failed: '+table)
                counts[table]=len(rows)
            for table in ('events','tikhub_calls'):
                db.execute(f"SELECT setval(pg_get_serial_sequence('{table}','id'),COALESCE(MAX(id),1),COUNT(*)>0) FROM {table}")
        return counts
    finally: source.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sqlite_backup')
    args=parser.parse_args()
    print('Validated and migrated row counts:',migrate(args.sqlite_backup))
