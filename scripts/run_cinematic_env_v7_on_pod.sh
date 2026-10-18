#!/usr/bin/env bash
# Capital cinematic V7 on the pinned pod. Does not touch V6 files or hufsgfs9f7gpga.
# Usage: bash scripts/run_cinematic_env_v7_on_pod.sh <pod_ip> <pod_ssh_port>
set -euo pipefail
IP="${1:?pod ip}"
PORT="${2:?pod ssh port}"
KEY="${RUNPOD_SSH_KEY:-/opt/lumen-rebuild/data/gpu/id_ed25519}"
ROOT="${LUMEN_ROOT:-/opt/lumen-rebuild}"
REMOTE_ROOT="/workspace/lumen-media-v1"
PY="$REMOTE_ROOT/py"
CKPT="$REMOTE_ROOT/models/sd_xl_base_1.0.safetensors"
SVD="$REMOTE_ROOT/models/svd-xt"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p "$PORT" "root@$IP")
SCP=(scp -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P "$PORT")

echo "=== balance check ==="
cd "$ROOT"
set -a; . ./.env; set +a
venv/bin/python scripts/runpod_pod_control.py status | tee /tmp/v7_status_pre.json
BAL=$(python3 -c "import json; print(json.load(open('/tmp/v7_status_pre.json'))['balance'])")
python3 - <<PY
bal=float("$BAL")
if bal < 3.0:
    raise SystemExit(f"HARD_STOP balance {bal} < 3")
print("balance_ok", bal)
PY

echo "=== sync plans + scripts (v7 only) ==="
"${SSH[@]}" "mkdir -p $REMOTE_ROOT/plans $REMOTE_ROOT/out/v7/stills $REMOTE_ROOT/out/v7/clips"
"${SCP[@]}" "$ROOT/scripts/lumen_media_image.py" "root@$IP:$REMOTE_ROOT/lumen_media_image.py"
"${SCP[@]}" "$ROOT/scripts/lumen_media_i2v.py" "root@$IP:$REMOTE_ROOT/lumen_media_i2v.py"
"${SCP[@]}" "$ROOT/media/library/plans/cinematic-env-v7-batch1.jsonl" "root@$IP:$REMOTE_ROOT/plans/cinematic-env-v7-batch1.jsonl"
"${SCP[@]}" "$ROOT/media/library/plans/cinematic-env-v7-i2v-batch1.jsonl" "root@$IP:$REMOTE_ROOT/plans/cinematic-env-v7-i2v-batch1.jsonl"

echo "=== model audit ==="
"${SSH[@]}" "bash -lc '
set -e
nvidia-smi
test -f $CKPT && echo SDXL_OK || echo SDXL_MISSING
test -f $SVD/model_index.json && echo SVD_OK || echo SVD_MISSING
'"

echo "=== stills ==="
"${SSH[@]}" "bash -lc '
set -e
export PYTHONPATH=$PY:\${PYTHONPATH:-}
cd $REMOTE_ROOT
python3 lumen_media_image.py --checkpoint $CKPT --batch plans/cinematic-env-v7-batch1.jsonl --outdir out/v7/stills
'"

echo "=== I2V (no SVD download; existing weights only) ==="
"${SSH[@]}" "bash -lc '
set -e
export PYTHONPATH=$PY:\${PYTHONPATH:-}
cd $REMOTE_ROOT
test -f $SVD/model_index.json
python3 lumen_media_i2v.py --model $SVD --batch plans/cinematic-env-v7-i2v-batch1.jsonl --stills-dir out/v7/stills --outdir out/v7/clips
'"

echo "=== pull to DO volume (v7 tree only) ==="
LIB="/mnt/volume_nyc1_1791446889637/app-library"
mkdir -p "$LIB/motion/cinematic-env-v7/stills" "$LIB/motion/cinematic-env-v7/clips"
"${SCP[@]}" -r "root@$IP:$REMOTE_ROOT/out/v7/stills/." "$LIB/motion/cinematic-env-v7/stills/"
"${SCP[@]}" -r "root@$IP:$REMOTE_ROOT/out/v7/clips/." "$LIB/motion/cinematic-env-v7/clips/"
if [[ -d "$ROOT/media/library/out" ]]; then
  mkdir -p "$ROOT/media/library/out/motion/cinematic-env-v7/stills" "$ROOT/media/library/out/motion/cinematic-env-v7/clips"
  rsync -a "$LIB/motion/cinematic-env-v7/" "$ROOT/media/library/out/motion/cinematic-env-v7/"
fi

echo "=== probe durations (no setpts) ==="
python3 - <<'PY'
import json, subprocess
from pathlib import Path
clips = Path("/mnt/volume_nyc1_1791446889637/app-library/motion/cinematic-env-v7/clips")
rows = []
for mp4 in sorted(clips.glob("*.mp4")):
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,nb_frames,r_frame_rate,duration",
         "-show_entries", "format=duration", "-of", "json", str(mp4)],
        capture_output=True, text=True,
    )
    data = json.loads(proc.stdout or "{}")
    fmt = (data.get("format") or {}).get("duration")
    stream = (data.get("streams") or [{}])[0]
    rows.append({
        "id": mp4.stem,
        "path": str(mp4),
        "duration": float(fmt or stream.get("duration") or 0),
        "width": stream.get("width"),
        "height": stream.get("height"),
        "nb_frames": stream.get("nb_frames"),
        "r_frame_rate": stream.get("r_frame_rate"),
        "durationClaim": "ffprobe_not_setpts",
    })
    print(mp4.name, rows[-1]["duration"], rows[-1]["width"], rows[-1]["height"], rows[-1]["r_frame_rate"])
out = clips / "probe.json"
out.write_text(json.dumps(rows, indent=2) + "\n")
print("PROBED", len(rows))
PY

echo "FACTORY_V7_POD_PHASE_DONE"
venv/bin/python scripts/runpod_pod_control.py status
