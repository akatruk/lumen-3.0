#!/bin/bash
# Install the distro pgvector build that matches PostgreSQL 16 on lumen-fix.
# Does not create a second server and does not open port 5432.
set -euo pipefail
PIN="0.6.0-1"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y "postgresql-16-pgvector=${PIN}"
for db in lumen lumen_qa; do
  runuser -u postgres -- psql -d "$db" -v ON_ERROR_STOP=1 -c 'CREATE EXTENSION IF NOT EXISTS vector;'
  runuser -u postgres -- psql -d "$db" -At -c "SELECT current_database() || ' ' || extname || ' ' || extversion FROM pg_extension WHERE extname='vector';"
done
ss -lnt | awk 'NR==1 || /:5432/'
echo "pgvector ${PIN} installed on the existing PostgreSQL 16 instance"
