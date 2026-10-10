#!/usr/bin/env bash
# Append hypit-gen → DO library sync status every INTERVAL seconds.
# Durable loop: SSH BatchMode + optional RunPod status (env key only; never written to disk).
set -uo pipefail

INTERVAL="${INTERVAL:-600}"
LOG="${LOG:-/Users/akatruk_macbook/Documents/github/lumen-3.0/output/runpod-hypit-sync-status.log}"
HOST="${LUMEN_TEST_HOST:-root@142.93.248.163}"
HYPIT_POD_ID="${HYPIT_POD_ID:-6zleobjm8h7zu9}"
HYPIT_POD_NAME="${HYPIT_POD_NAME:-lumen-hypit-4090}"
AGENT_TRANSCRIPT="${AGENT_TRANSCRIPT:-/Users/akatruk_macbook/.cursor/projects/Users-akatruk-macbook-Documents-github-lumen-3-0/agent-transcripts/1492dcf3-d1d7-40d0-883d-5c640bd08663/subagents/f3c3ca5f-ec41-44ad-8a0c-a3cf84289a5c.jsonl}"
STATE_DIR="${STATE_DIR:-/Users/akatruk_macbook/Documents/github/lumen-3.0/output/.runpod-hypit-sync-monitor}"
mkdir -p "$(dirname "$LOG")" "$STATE_DIR"

prev_bytes_file="$STATE_DIR/transcript_bytes"
pidfile="$STATE_DIR/monitor.pid"
echo "$$" >"$pidfile"

local_markers() {
  local n
  n="$(pgrep -f 'rsync|rclone|scp |build_vector|library_v2|lumen_media|diffusers|i2v|monitor_runpod_hypit' 2>/dev/null | wc -l | tr -d ' ')"
  printf 'local_syncish=%s' "${n:-0}"
  if [[ -f /tmp/lumen_hypit_ssh.json ]]; then
    printf ' hypit_ssh_json=yes'
  else
    printf ' hypit_ssh_json=no'
  fi
  if pgrep -f 'check_runpod_gen_status|MONITOR_START every 20m' >/dev/null 2>&1; then
    printf ' gen_monitor=yes'
  else
    printf ' gen_monitor=no'
  fi
}

runpod_status() {
  if [[ -z "${RUNPOD_API_KEY:-}" ]]; then
    echo "runpod=KEY_ABSENT"
    return 0
  fi
  python3 - <<'PY' 2>/dev/null || echo "runpod=QUERY_FAIL"
import json, os, urllib.request

token = os.environ["RUNPOD_API_KEY"]
pod_id = os.environ.get("HYPIT_POD_ID", "6zleobjm8h7zu9")
pod_name = os.environ.get("HYPIT_POD_NAME", "lumen-hypit-4090")
query = "{ myself { currentSpendPerHr pods { id name desiredStatus } } }"
body = json.dumps({"query": query}).encode()
req = urllib.request.Request(
    "https://api.runpod.io/graphql?api_key=" + token,
    data=body,
    headers={"Content-Type": "application/json", "User-Agent": "lumen-monitor/1.0"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
except Exception as exc:
    print(f"runpod=HTTP_FAIL({type(exc).__name__})")
    raise SystemExit(0)
if data.get("errors"):
    print("runpod=GQL_ERR")
    raise SystemExit(0)
me = (data.get("data") or {}).get("myself") or {}
pods = me.get("pods") or []
target = next((p for p in pods if p.get("id") == pod_id or (p.get("name") or "") == pod_name), None)
others = ",".join(f"{p.get('name') or p.get('id')}:{(p.get('desiredStatus') or '?')}" for p in pods[:6]) or "none"
if target:
    print(
        f"runpod={target.get('desiredStatus')} id={target.get('id')} name={target.get('name')} "
        f"spend={me.get('currentSpendPerHr')} pods={len(pods)} all={others}"
    )
else:
    print(f"runpod=NOT_FOUND spend={me.get('currentSpendPerHr')} pods={len(pods)} all={others}")
PY
}

one_check() {
  local ts t_bytes t_lines t_mtime grew remote assets runpod man_mtime sync_procs recent30 recent120 gen_hint rp localm
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  t_bytes=0
  t_lines=0
  t_mtime="missing"
  grew="n/a"
  if [[ -f "$AGENT_TRANSCRIPT" ]]; then
    t_bytes="$(wc -c <"$AGENT_TRANSCRIPT" | tr -d ' ')"
    t_lines="$(wc -l <"$AGENT_TRANSCRIPT" | tr -d ' ')"
    t_mtime="$(date -u -r "$AGENT_TRANSCRIPT" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
    if [[ -f "$prev_bytes_file" ]]; then
      local prev
      prev="$(cat "$prev_bytes_file" 2>/dev/null || echo 0)"
      if [[ "$t_bytes" -gt "$prev" ]]; then
        grew="yes(+$((t_bytes - prev))B)"
      elif [[ "$t_bytes" -eq "$prev" ]]; then
        grew="no"
      else
        grew="shrunk"
      fi
    else
      grew="baseline"
    fi
    echo "$t_bytes" >"$prev_bytes_file"
  fi

  remote="$(ssh -o BatchMode=yes -o ConnectTimeout=20 "$HOST" \
    'python3 -c "
import json, os, datetime, subprocess
p=\"/mnt/volume_nyc1_1791446889637/app-library/manifest.json\"
if not os.path.isfile(p):
    print(\"assets=NA runpod=NA mtime=NA\")
else:
    st=os.stat(p)
    mtime=datetime.datetime.fromtimestamp(st.st_mtime, datetime.timezone.utc).strftime(\"%Y-%m-%dT%H:%M:%SZ\")
    with open(p) as f: data=json.load(f)
    assets=data.get(\"assets\") if isinstance(data, dict) else data
    if not isinstance(assets, list): assets=[]
    runpod=sum(1 for a in assets if isinstance(a, dict) and str(a.get(\"source\") or \"\").lower()==\"runpod\")
    print(f\"assets={len(assets)} runpod={runpod} mtime={mtime}\")
import re
out=subprocess.check_output([\"ps\",\"-eo\",\"args\"], text=True, errors=\"replace\")
pat=re.compile(r\"rsync|scp |sftp|rclone|build_vector|library_v2|lumen_media|diffusers|i2v\", re.I)
sync=sum(1 for line in out.splitlines() if pat.search(line) and \"egrep\" not in line and \"monitor_runpod\" not in line)
print(f\"sync_procs={sync}\")
r30=subprocess.check_output(\"find /mnt/volume_nyc1_1791446889637/app-library -type f -mmin -30 2>/dev/null | wc -l\", shell=True, text=True).strip()
r120=subprocess.check_output(\"find /mnt/volume_nyc1_1791446889637/app-library -type f -mmin -120 2>/dev/null | wc -l\", shell=True, text=True).strip()
print(f\"recent30={r30}\")
print(f\"recent120={r120}\")
" 2>/dev/null; \
    if [ -f /tmp/lumen-gen-status.py ] && [ -x /opt/lumen-rebuild/venv/bin/python ]; then
      sudo -u lumen bash -lc "set -a; [ -f /opt/lumen-rebuild/.env ] && . /opt/lumen-rebuild/.env; set +a; PYTHONPATH=/opt/lumen-rebuild /opt/lumen-rebuild/venv/bin/python /tmp/lumen-gen-status.py" 2>/dev/null | head -5 | tr "\n" " " | sed "s/[[:space:]]\+/ /g"; echo
    else
      echo "pod_hint=no_status_script"
    fi' 2>/dev/null || echo "SSH_FAIL")"

  assets="$(echo "$remote" | sed -n 's/.*assets=\([0-9NA]*\).*/\1/p' | head -1)"
  runpod="$(echo "$remote" | sed -n 's/.*runpod=\([0-9NA]*\).*/\1/p' | head -1)"
  man_mtime="$(echo "$remote" | sed -n 's/.*mtime=\([0-9T:Z-]*\).*/\1/p' | head -1)"
  sync_procs="$(echo "$remote" | sed -n 's/.*sync_procs=\([0-9]*\).*/\1/p' | head -1)"
  recent30="$(echo "$remote" | sed -n 's/.*recent30=\([0-9]*\).*/\1/p' | head -1)"
  recent120="$(echo "$remote" | sed -n 's/.*recent120=\([0-9]*\).*/\1/p' | head -1)"
  gen_hint="$(echo "$remote" | egrep -i 'JOBS|POD |GPU_|pod_hint|SSH_FAIL|EXITED|RUNNING' | head -3 | tr '\n' ';' | sed 's/;$//')"

  : "${assets:=?}" "${runpod:=?}" "${man_mtime:=?}" "${sync_procs:=?}" "${recent30:=?}" "${recent120:=?}"
  : "${gen_hint:=none}"

  rp="$(runpod_status | tr '\n' ' ' | sed 's/[[:space:]]\+$//')"
  localm="$(local_markers)"

  printf '%s assets=%s runpod_tag=%s manifest_mtime=%s sync_procs=%s recent30=%s recent120=%s agent_bytes=%s agent_lines=%s agent_mtime=%s agent_grew=%s gen=%s %s %s\n' \
    "$ts" "$assets" "$runpod" "$man_mtime" "$sync_procs" "$recent30" "$recent120" \
    "$t_bytes" "$t_lines" "$t_mtime" "$grew" "$gen_hint" "$rp" "$localm" >>"$LOG"
}

cleanup() {
  echo "==== $(date -u +%Y-%m-%dT%H:%M:%SZ) MONITOR_STOP pid=$$ ====" >>"$LOG"
  rm -f "$pidfile"
}
trap cleanup EXIT
trap 'exit 0' TERM INT HUP

if [[ -n "${RUNPOD_API_KEY:-}" ]]; then
  _key_note="present"
else
  _key_note="absent"
fi
echo "==== $(date -u +%Y-%m-%dT%H:%M:%SZ) MONITOR_START interval=${INTERVAL}s host=${HOST} pid=$$ hypit=${HYPIT_POD_ID}/${HYPIT_POD_NAME} RUNPOD_API_KEY=${_key_note} ====" >>"$LOG"
unset _key_note

one_check || echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) CHECK_FAILED" >>"$LOG"
while true; do
  sleep "$INTERVAL" || true
  one_check || echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) CHECK_FAILED" >>"$LOG"
done
