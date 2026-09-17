# PostgreSQL storage

Production uses PostgreSQL through psycopg 3. SQLite is retained only for offline development and rollback of the pre-migration release.

`DATABASE_URL=dbname=lumen user=lumen host=/var/run/postgresql`

The systemd web and worker processes run as OS user `lumen`, which authenticates through the local PostgreSQL socket using peer authentication. No database password is required. The database role is not a superuser and cannot create roles/databases. PostgreSQL listens on localhost; do not open port 5432 publicly.

## Data and queue

All 14 application tables move together: accounts, sessions, OAuth state, Douyin caches, API usage, projects, sources, jobs, spending, events and studio plans/requests. Video files remain in the existing data directory. Timestamps and monetary values use double precision to preserve SQLite's existing representation.

The adapter preserves parameterized queries and short atomic read/check/write sections using transaction-scoped advisory locks. This deliberately conservative first migration serializes critical sections; it does not serialize the long-running AI or FFmpeg work. The worker holds a separate session advisory lock to enforce a single worker across processes/hosts. This release does not support a multi-worker fleet or shared cross-host media storage.

Redis is unnecessary for the current deployment: the queue and search cache are durable in PostgreSQL, while one web process and one worker run on the VM. Redis would not add durable job guarantees by itself. In-memory HTTP rate limiting is still per web process; review it before adding web replicas.

## Setup and migration

1. Install `postgresql` and `postgresql-client`; install pinned Python requirements.
2. Run `python3 deploy/setup-postgres.py` as root. The `lumen` OS user must already exist.
3. Drain queued/running jobs and stop the web and worker services.
4. Back up code, `.env`, and SQLite using SQLite's backup API; retain video files.
5. Run the migration as `lumen` with `DATABASE_URL` set, against that SQLite backup: `python -m backend.migrate_postgres /path/to/backup.db`.
6. The importer refuses a nonempty destination, validates SQLite integrity/FKs, imports in one transaction, compares every row by primary key, and resets identity sequences. It never modifies the SQLite file.
7. Set `DATABASE_URL` in the protected production `.env`, install the new backend and restart the two services.
8. Verify database identity, health, session/API protection, row counts and worker heartbeat.

Pre-cutover rollback restores the previous code and `.env`; the old SQLite file remains intact. After PostgreSQL accepts new writes, switching back to the old SQLite snapshot would lose those writes: reconcile/export them first. Do not silently switch storage when PostgreSQL is unavailable.

For backups use `pg_dump -Fc` as the lumen OS user, writing to a protected location. A local snapshot protects against deployment mistakes, not loss of the VM; off-host backups remain an operational follow-up.

## Tests

`LUMEN_TEST_POSTGRES_URL='dbname=lumen_qa user=lumen host=/var/run/postgresql' python -m pytest backend/tests -q`

The full suite creates and drops one random schema per test, and refuses any database name other than `lumen_qa`. Without this variable tests use isolated SQLite files. Tests cover concurrent budget reservation, rollback, worker exclusivity, ownership, OAuth, queue behavior and approval/locking rules.

References: [psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html), [PostgreSQL advisory locks](https://www.postgresql.org/docs/16/explicit-locking.html).

## Production cutover — 2026-09-15

- PostgreSQL 16.15 installed on the new VM `142.93.248.163`; the old VM was not touched.
- Full PostgreSQL backend suite: 48 passed; an additional importer regression test subsequently passed with the database tests (4/4). SQLite compatibility checks: 43 passed, 1 PostgreSQL-only skipped, 4 render-related deselected locally.
- Rehearsal against a live SQLite snapshot succeeded in a separate QA schema before cutover.
- All rows compared exactly during import: users 2, sessions 3, TikHub calls 3, Douyin results 17, search caches 2, Google identities 2, OAuth states 3, projects 2, source records 1, jobs 2, spend 7, events 7; studio tables were empty.
- Verified active connection `database=lumen`, `role=lumen`, PostgreSQL enabled, fresh worker heartbeat, and both services active. Port 5432 bound only to 127.0.0.1 and ::1. Public HTTPS health passed.
- Private backup directory: `/opt/lumen-rebuild/backups/postgres-20260915-051912`. Contains old backend, protected environment snapshot, SQLite backup, and a fresh PostgreSQL custom-format dump. Original media and SQLite file retained.
- Redis was not installed: this deployment keeps its durable queue and cache in PostgreSQL.
