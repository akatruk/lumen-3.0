#!/usr/bin/env bash
# Resumable V7 factory. Retries pinned-pod resume only. Never creates a pod.
# On success: generate, pull, leave probe.json. Stops the pod when the GPU phase ends.
set -uo pipefail
ROOT="${LUMEN_ROOT:-/opt/lumen-rebuild}"
cd "$ROOT"
set -a; . ./.env; set +a
ATTEMPTS="${V7_RESUME_ATTEMPTS:-36}"
SLEEP="${V7_RESUME_SLEEP:-75}"

for i in $(seq 1 "$ATTEMPTS"); do
  echo "ATTEMPT $i $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if ./venv/bin/python scripts/runpod_pod_control.py resume | tee /tmp/v7_resume_status.json; then
    python3 - <<'PY'
import json
text = open("/tmp/v7_resume_status.json").read()
start = text.find("{")
if start < 0:
    raise SystemExit("resume output had no json")
blob, _ = json.JSONDecoder().raw_decode(text[start:])
bal = float(blob["balance"])
if bal < 3.0:
    raise SystemExit(f"HARD_STOP balance {bal}")
ip = (blob.get("ssh") or {}).get("ip")
port = (blob.get("ssh") or {}).get("port")
if not ip or not port:
    raise SystemExit("resume json missing ssh")
open("/tmp/v7_ssh.env","w").write(f"IP={ip}\nPORT={port}\n")
print("SSH", ip, port, "BAL", bal)
PY
    # shellcheck disable=SC1091
    . /tmp/v7_ssh.env
    set +e
    bash scripts/run_cinematic_env_v7_on_pod.sh "$IP" "$PORT"
    code=$?
    set -e
    echo "FACTORY_EXIT $code"
    ./venv/bin/python scripts/runpod_pod_control.py stop || true
    exit "$code"
  fi
  echo "FAIL_SLEEP $SLEEP"
  sleep "$SLEEP"
done
echo "RESUME_BLOCKED no free GPU on pinned pod after $ATTEMPTS attempts"
./venv/bin/python scripts/runpod_pod_control.py status || true
exit 2
