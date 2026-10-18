#!/bin/bash
# Restore the newest dump into a throwaway database, then drop it.
# Never restores over the live `lumen` database.
set -euo pipefail
DEST_ROOT=/mnt/volume_nyc1_1791446889637/lumen-db-backups
DUMP=$(ls -1t "$DEST_ROOT"/lumen-*.dump | head -1)
TARGET=lumen_restore_drill
cleanup() {
  runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${TARGET}' AND pid <> pg_backend_pid();" >/dev/null || true
  runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${TARGET};" >/dev/null || true
}
trap cleanup EXIT
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${TARGET}' AND pid <> pg_backend_pid();" || true
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${TARGET};"
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${TARGET} OWNER lumen;"
# Extension creation is superuser-only. Create it before the restore so vector columns load.
# Directory must be traversable by postgres (750 lumen:postgres). The dump is 640.
chgrp postgres "$(dirname "$DUMP")" "$DUMP"
chmod 750 "$(dirname "$DUMP")"
chmod 640 "$DUMP"
runuser -u postgres -- psql -d "$TARGET" -v ON_ERROR_STOP=1 -c 'CREATE EXTENSION IF NOT EXISTS vector;'
set +e
runuser -u postgres -- pg_restore --no-owner --dbname "$TARGET" "$DUMP"
status=$?
set -e
if [[ "$status" -gt 1 ]]; then
  echo "pg_restore failed with status $status" >&2
  runuser -u postgres -- psql -c "DROP DATABASE IF EXISTS ${TARGET};" || true
  exit "$status"
fi
EXT=$(runuser -u postgres -- psql -d "$TARGET" -At -c "SELECT extname || ' ' || extversion FROM pg_extension WHERE extname='vector';")
COUNT=$(runuser -u postgres -- psql -d "$TARGET" -At -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='engineering_memory';")
ROWS=$(runuser -u postgres -- psql -d "$TARGET" -At -c "SELECT COUNT(*) FROM asset_embeddings;")
echo "restored=$DUMP extension=${EXT:-missing} engineering_memory_table=$COUNT asset_rows=$ROWS"
test "$COUNT" = "1"
test "$ROWS" -ge 1
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "DROP DATABASE ${TARGET};"
echo "dropped $TARGET"
