#!/bin/bash
# Custom-format dump of the lumen database onto the media volume.
# Peer auth as the lumen OS user. No password in this file. Not a git path.
set -euo pipefail
DEST_ROOT=/mnt/volume_nyc1_1791446889637/lumen-db-backups
if [[ ! -d /mnt/volume_nyc1_1791446889637 ]]; then
  echo "media volume is not mounted" >&2
  exit 1
fi
install -d -o lumen -g postgres -m 750 "$DEST_ROOT"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$DEST_ROOT/lumen-$STAMP.dump"
runuser -u lumen -- pg_dump -Fc -d lumen -f "$OUT"
chown lumen:postgres "$OUT"
chmod 640 "$OUT"
find "$DEST_ROOT" -type f -name 'lumen-*.dump' -mtime +14 -delete
# Refuse to leave a dump inside the git checkout.
case "$OUT" in
  /opt/lumen-rebuild/*) echo "refusing a dump under the app tree" >&2; rm -f "$OUT"; exit 1 ;;
esac
echo "$OUT"
