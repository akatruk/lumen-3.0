"""Optional full-suite PostgreSQL run, always against a dedicated QA database."""
import os
import uuid
import pytest
from backend.config import settings

@pytest.fixture(autouse=True)
def database_isolation(monkeypatch):
    url=os.environ.get('LUMEN_TEST_POSTGRES_URL','')
    if not url:
        monkeypatch.setattr(settings,'database_url','')
        yield
        return
    import psycopg
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    if conninfo_to_dict(url).get('dbname') != 'lumen_qa':
        raise RuntimeError('PostgreSQL tests require the dedicated lumen_qa database')
    schema='test_'+uuid.uuid4().hex
    with psycopg.connect(url,autocommit=True) as db:
        db.execute(f'CREATE SCHEMA {schema}')
        monkeypatch.setattr(settings,'database_url',make_conninfo(url,options=f'-c search_path={schema}'))
        try: yield
        finally: db.execute(f'DROP SCHEMA {schema} CASCADE')
