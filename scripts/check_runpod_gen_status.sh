#!/bin/bash
set -euo pipefail
ssh -o BatchMode=yes -o ConnectTimeout=20 root@142.93.248.163 'cd /opt/lumen-rebuild && sudo -u lumen bash -lc "
set -a; [ -f .env ] && . ./.env; set +a
PYTHONPATH=/opt/lumen-rebuild ./venv/bin/python /tmp/lumen-gen-status.py
"'
